# 🎙️ AI Meeting Assistant

Takes audio from a YouTube URL or an uploaded file, transcribes it locally with Whisper,
summarizes it and extracts action items / key decisions / open questions via LangChain LCEL
chains + Claude, and supports RAG-based chat over the transcript via ChromaDB + HuggingFace
embeddings.

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Requires `ffmpeg` as a system binary (`brew install ffmpeg` on macOS) and an `ANTHROPIC_API_KEY`
in a local `.env` file (see `.env` — never commit this file).

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub (already the case — deploys straight from `main`).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub.
3. **New app** → pick this repo, branch `main`, main file `app.py`.
4. Before deploying, open **Advanced settings**:
   - Set a Python version close to 3.11 — Whisper, ChromaDB, and sentence-transformers are
     far more likely to have prebuilt wheels there than for the 3.14 this project uses locally.
   - Add secrets in TOML format:
     ```toml
     ANTHROPIC_API_KEY = "sk-ant-..."
     WHISPER_MODEL = "base"
     ```
     `WHISPER_MODEL` is optional — the free tier is slower than a local machine, and the code
     defaults to `small` if unset. Never commit a real key; `.env` stays gitignored.
5. **Deploy.** `requirements.txt` and `packages.txt` (ffmpeg) are picked up automatically.
   Future pushes to `main` redeploy automatically.

**Known limitations on the free tier:**
- `downloads/` and `vector_db/` are ephemeral — wiped on every reboot/redeploy. Fine for a
  live demo; don't rely on it for persistence.
- Free-tier RAM is limited (historically ~1GB) — torch + Whisper + ChromaDB +
  sentence-transformers loaded together can be tight. If the app crashes or won't start,
  try `WHISPER_MODEL=tiny` first.
