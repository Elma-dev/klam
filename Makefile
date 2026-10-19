# Klam — development commands.
#
# macOS native (default) uses the MLX provider via mlx-audio. Anywhere else uses
# the Voxtral provider against a served model — see deploy/modal/ for the
# serverless GPU endpoint.

PY            := $(CURDIR)/backend/.venv/bin/python
MLX_MODEL     ?= $(HOME)/models/voxtral-ar-8bit
# The public checkpoint the MLX model is converted from. It cannot be loaded
# directly: it ships both Mistral-native and HF-format weights, and mlx-audio
# would merge the two schemas. It is a conversion source, not a model.
VOXTRAL_HF    ?= mistralai/Voxtral-Mini-4B-Realtime-Arabic
# Set to publish the conversion to the Hub, e.g. MLX_HF_REPO=you/voxtral-ar-8bit-mlx
MLX_HF_REPO   ?=
MLX_HOST      ?= 127.0.0.1
MLX_PORT      ?= 8000
BACKEND_PORT  ?= 8001
FRONTEND_PORT ?= 5173
MODAL_APP     ?= deploy/modal/app.py

.PHONY: help setup setup-mlx setup-frontend fonts model doctor test lint fmt dev frontend frontend-build mlx-server dev-mac dev-all modal-weights modal-serve modal-deploy hf-space clean

help:
	@echo "make setup           - create venv + install core & dev deps"
	@echo "make setup-mlx       - also install the MLX provider deps (macOS)"
	@echo "make setup-frontend  - install frontend deps (pnpm)"
	@echo "make fonts           - (re)fetch bundled OFL fonts"
	@echo "make model           - build the 8-bit MLX speech model (~8.3 GB download)"
	@echo "make doctor          - check ffmpeg/libass/fonts"
	@echo "make test            - run pytest"
	@echo "make lint            - run ruff (backend)"
	@echo "make fmt             - format with ruff"
	@echo "make dev             - run backend (in-process MLX) on :$(BACKEND_PORT)"
	@echo "make frontend        - run Vite dev server on :$(FRONTEND_PORT)"
	@echo "make frontend-build  - build the frontend to frontend/dist"
	@echo "make mlx-server      - run mlx-audio HTTP server on :$(MLX_PORT)"
	@echo "make dev-mac         - mlx server + backend (HTTP mode) together"
	@echo "make dev-all         - mlx server + backend + frontend (mock ASR)"
	@echo "make modal-weights   - prefetch ASR weights into the Modal Volume"
	@echo "make modal-serve     - run the Modal ASR endpoint with hot reload"
	@echo "make modal-deploy    - deploy the Modal ASR endpoint"
	@echo "make hf-space        - assemble the HF ZeroGPU Space directory"

setup:
	cd backend && uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"

setup-mlx: setup
	cd backend && uv pip install --python .venv/bin/python -e ".[dev,mlx]"

setup-frontend:
	cd frontend && pnpm install

fonts:
	python3 scripts/fetch_fonts.py

# Build the default 8-bit MLX speech model. Run `make setup-mlx` first: this
# needs mlx-audio (which brings mlx-lm and the `hf` CLI) and internet; see the
# README for disk and memory. The source repo ships its weights twice, and the
# converter only reads the Mistral-native consolidated.safetensors, so the
# HF-format model*.safetensors copy (~8 GB) is excluded from the download.
model:
	src=$$($(dir $(PY))hf download $(VOXTRAL_HF) --quiet \
		--exclude 'model*.safetensors' --exclude 'model.safetensors.index.json') && \
	$(PY) -m mlx_audio.convert \
		--hf-path "$$src" \
		--mlx-path $(MLX_MODEL) \
		--model-domain stt \
		--quantize --q-bits 8 --q-group-size 64 \
		$(if $(MLX_HF_REPO),--upload-repo $(MLX_HF_REPO))
	# mlx-audio 0.4.5 copies the source's Mistral-native consolidated weights
	# into the output. Left there they add ~9 GB and, worse, mlx-audio would
	# re-download and merge them with the quantized weights on the next load.
	rm -f $(MLX_MODEL)/consolidated.safetensors
	@echo "Model ready at $(MLX_MODEL)"

doctor:
	@$(PY) -c "from klam.config import get_settings; from klam.ffmpeg import resolve_ffmpeg, resolve_ffprobe, has_libass; from klam.paths import resolve_fonts_dir; s=get_settings(); ff=resolve_ffmpeg(s); print('ffmpeg     ', ff); print('libass     ', has_libass(ff)); print('ffprobe    ', resolve_ffprobe(s)); print('fonts_dir  ', resolve_fonts_dir(s))"

test:
	cd backend && $(PY) -m pytest -q
	$(PY) -m pytest deploy/modal -q
	cd frontend && pnpm test

lint:
	cd backend && $(PY) -m ruff check src tests ../deploy
	cd frontend && pnpm lint

fmt:
	cd backend && $(PY) -m ruff format src tests

dev:
	cd backend && $(PY) -m uvicorn klam.main:app --port $(BACKEND_PORT) --reload

frontend:
	cd frontend && pnpm dev

frontend-build:
	cd frontend && pnpm build

mlx-server:
	$(PY) -m mlx_audio.server --host $(MLX_HOST) --port $(MLX_PORT) --realtime --realtime-model $(MLX_MODEL)

# Start the mlx-audio server in the background, then the backend in HTTP mode.
dev-mac:
	@trap 'kill 0' EXIT INT TERM; \
	$(PY) -m mlx_audio.server --host $(MLX_HOST) --port $(MLX_PORT) --realtime --realtime-model $(MLX_MODEL) & \
	sleep 3; \
	cd backend && KLAM_MLX_MODE=http KLAM_MLX_BASE_URL=http://$(MLX_HOST):$(MLX_PORT) \
		$(PY) -m uvicorn klam.main:app --port $(BACKEND_PORT) --reload

# Everything together with a mock ASR (no model needed), for UI development.
dev-all:
	@trap 'kill 0' EXIT INT TERM; \
	cd backend && KLAM_ASR_PROVIDER=mock $(PY) -m uvicorn klam.main:app --port $(BACKEND_PORT) & \
	cd frontend && pnpm dev

# Serverless GPU ASR endpoint (see deploy/modal/README.md). Needs the `modal`
# client locally and a `klam-asr` secret holding KLAM_ASR_TOKEN.
modal-weights:
	modal run $(MODAL_APP)::download_models

modal-serve:
	modal serve $(MODAL_APP)

modal-deploy:
	modal deploy $(MODAL_APP)

# Assemble the HF ZeroGPU Space (see deploy/hf/README.md), then upload it and set
# the Space hardware to ZeroGPU in its settings.
hf-space:
	$(PY) deploy/hf/build_space.py

clean:
	rm -rf backend/.venv backend/data data frontend/node_modules frontend/dist
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
