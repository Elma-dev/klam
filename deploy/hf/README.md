---
title: Klam
emoji: 🎬
colorFrom: indigo
colorTo: red
sdk: gradio
app_file: app.py
pinned: false
python_version: "3.12"
---

# Klam

Arabic and Darija captions: upload a clip, the GPU transcribes it with word-level
timings, edit the captions in the table, then burn them in or download an SRT.

**Set the Space hardware to ZeroGPU** in Settings (Gradio SDK + ZeroGPU). Docker
and Static Spaces cannot schedule onto ZeroGPU at all.

## Why the interface is Gradio and not the React editor

ZeroGPU only works with the Gradio SDK, and a custom frontend misses the
`postMessage` handshake that sets `window.supports_zerogpu_headers` — without it
`@gradio/client` never fetches the identity token, and a signed-in PRO user is
billed as anonymous (about 2 minutes a day instead of 40). See gradio#13209. The
React editor remains the local experience; this is the hosted one.

## Quota

ZeroGPU gives each visitor a daily GPU budget — around 5 minutes free, 40 for
PRO. The Space asks only for the GPU time a clip actually needs: the requested
duration is derived from the media length, because a call asking for more than
the caller has left is refused outright.

## Notes

- Both models load at module scope so the first visitor does not pay to load
  ~15 GB.
- Transcription is one GPU call for the whole clip, not one per chunk.
- The export is CPU work (ffmpeg + libass from `packages.txt`) and needs no
  GPU request.
- Model transcripts come from the public Arabic Voxtral checkpoint; the local
  MLX fine-tunes are Apple-only and cannot be loaded here.
