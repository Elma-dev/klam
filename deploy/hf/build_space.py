"""Assemble — and optionally upload — the HF ZeroGPU Space.

The Space is its own git repository, so it cannot import the Klam package
from this repo. Rather than keep a hand-maintained copy that drifts, copy the
package and the bundled fonts in at build time.

    python deploy/hf/build_space.py
    python deploy/hf/build_space.py --upload <user>/<space>

Then set the Space's hardware to ZeroGPU in its settings.

Why this script uploads rather than telling you to use `hf upload` or git — both
of those fail on this repo, for two unrelated reasons:

* ``hf upload`` calls ``create_repo`` first, which returns **402** for a Gradio
  Space on a non-PRO account even when the Space already exists.
* a plain ``git push`` is rejected by the pre-receive hook: **binary files must
  go through Xet storage**, and the fonts are binaries.

``HfApi.upload_folder`` does neither — it uploads through Xet and does not touch
the create endpoint — so it is what this uses.

If ``HF_TOKEN`` is set in your environment but is stale, it takes precedence
over the stored token and every call fails; ``env -u HF_TOKEN`` avoids that.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = REPO / "build" / "hf-space"

SPACE_FILES = ["app.py", "README.md", "requirements.txt", "packages.txt"]

TREES = {
    REPO / "backend" / "src" / "klam": OUT / "klam",
    # The same OFL fonts the browser and the local export use, so the burnt-in
    # captions look like the ones you designed.
    REPO / "frontend" / "public" / "fonts": OUT / "fonts",
}

SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info", ".pytest_cache")


def build() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for name in SPACE_FILES:
        shutil.copy2(HERE / name, OUT / name)
    for src, dst in TREES.items():
        if not src.is_dir():
            raise SystemExit(f"missing source directory: {src}")
        shutil.copytree(src, dst, ignore=SKIP)

    files = sum(1 for path in OUT.rglob("*") if path.is_file())
    print(f"built {OUT.relative_to(REPO)} ({files} files)")


def _merge_frontmatter(repo_id: str) -> None:
    """Keep the Space's own frontmatter (title, emoji, colours, sdk_version).

    The Space was created in the browser with its own settings; our README only
    owns the body, so pull the live frontmatter across rather than clobber it.
    """
    readme = OUT / "README.md"
    body = readme.read_text().split("---", 2)[2].lstrip()
    try:
        from huggingface_hub import hf_hub_download

        live = Path(
            hf_hub_download(repo_id, "README.md", repo_type="space")
        ).read_text()
        front = live.split("---")[1]
        readme.write_text(f"---{front}---\n{body}")
        print("merged the Space's existing frontmatter")
    except Exception as exc:  # noqa: BLE001 — a new Space has nothing to merge
        print(f"(no live frontmatter to merge: {type(exc).__name__})")


def upload(repo_id: str) -> None:
    from huggingface_hub import HfApi

    _merge_frontmatter(repo_id)
    try:
        HfApi().upload_folder(
            repo_id=repo_id,
            repo_type="space",
            folder_path=str(OUT),
            ignore_patterns=[".git*"],
            commit_message="Klam: ZeroGPU Gradio Space",
        )
    except Exception as exc:  # noqa: BLE001
        if os.environ.get("HF_TOKEN"):
            raise SystemExit(
                f"{type(exc).__name__}: {exc}\n\n"
                "HF_TOKEN is set in this environment and takes precedence over the "
                "stored token. If it is stale, re-run with `env -u HF_TOKEN`."
            ) from exc
        raise
    print(f"uploaded to https://huggingface.co/spaces/{repo_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upload", metavar="USER/SPACE", help="upload after building")
    args = parser.parse_args()

    build()
    if args.upload:
        upload(args.upload)
    else:
        print(f"\nupload with:\n  python {Path(__file__).relative_to(REPO)} --upload <user>/<space>")


if __name__ == "__main__":
    main()
