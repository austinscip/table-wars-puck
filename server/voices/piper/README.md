# Piper TTS voices

Narration MP3s for Speed Pyramid are generated locally with Piper. The
voice models are large (~115MB each) and gitignored — pull them on first
checkout:

```bash
cd server/voices/piper
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx.json
```

The `.onnx.json` config IS committed (only ~4 KB).

To swap voices, change `PIPER_MODEL` in `server/scripts/generate_narration.py`
and download the new model the same way. The `rhasspy/piper-voices` HF
repo lists every available voice with samples.

Then regenerate every question MP3:

```bash
cd server
DATABASE_URL= venv/bin/python scripts/generate_narration.py --overwrite
```

68 MP3s land in `server/static/games/speed-pyramid/audio/questions/`.
The server's `_narration_url()` appends `?v=<mtime>` so the browser
cache invalidates as soon as files change.
