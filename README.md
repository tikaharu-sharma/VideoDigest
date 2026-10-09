# 🎬 VideoDigest — AI Video & Lecture Summarizer

**[Live demo](https://aivideoagent.streamlit.app)** · Built Jul 2026 – Sep 2026

Turns a recorded lecture, meeting, or any long video into a summary, key questions, and
action items — then lets you ask it follow-up questions directly, instead of scrubbing
back through the recording to find one answer.

## Why

Long recordings are slow to get through when you just need the substance. This started as
a personal tool for missed lectures — rather than replaying a full recording, I wanted the
key points up front and the ability to ask something specific ("what did they say the
deadline was?") and get a grounded answer pulled from the actual transcript.

## How it works

1. **Ingest** — a YouTube URL or an uploaded audio/video file is downloaded/converted and
   chunked (`yt-dlp` + `ffmpeg`/`pydub`). YouTube URL input is currently disabled on the live
   demo — see **Try it** below for why.
2. **Transcribe** — chunks are transcribed locally with OpenAI's Whisper (no audio leaves
   the machine at this stage).
3. **Summarize & extract** — LangChain (LCEL) pipelines run the transcript through Claude:
   - Map-reduce summarization, so a long transcript doesn't have to fit in one context
     window or one API call.
   - Structured extraction (action items, key decisions, open questions), chunked the same
     way for long recordings.
4. **Index for chat** — the transcript is embedded (Hugging Face sentence-transformers,
   `all-MiniLM-L6-v2`) into a per-video ChromaDB collection.
5. **Ask questions** — a RAG chain retrieves the most relevant transcript passages for each
   question and answers from those only — the prompt explicitly instructs the model to say
   so if the answer isn't in the retrieved context, rather than guess.

## Stack

Python · Streamlit · LangChain (LCEL) · Anthropic Claude API · OpenAI Whisper · ChromaDB ·
Hugging Face sentence-transformers · yt-dlp · ffmpeg/pydub

## Try it

Upload a short audio or video file on the [live demo](https://aivideoagent.streamlit.app) —
fully supported, with local Whisper transcription, Claude summarization, and RAG chat all
working end-to-end.

**YouTube URL input is currently disabled on the live demo.** YouTube actively blocks
automated downloads from shared cloud-hosting IP ranges regardless of authentication — a
widely documented anti-scraping measure that affects most free-tier hosting platforms, not a
bug specific to this app (confirmed by testing against a second, different host — same
cookies, same code, blocked on one, worked on the other). The backend implementation (cookie-
based auth, JS-challenge solving via Deno, correct YouTube player-client selection) is done
and does work — see `utils/audio_processor.py`, `Dockerfile`, and `yt-test/` — re-enabling it
on the live demo is a hosting decision (which platform, and its RAM budget for the rest of the
app) rather than something left to build.

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
- YouTube URL downloads are disabled on this host — see **Try it** above for why.

## Deploying with Docker (Render, Fly.io, or any container host)

Not currently used for the live demo (Streamlit Community Cloud is), but kept in the repo and
working — this is what YouTube URL support was verified against, on a host whose IP isn't
blocked. A `Dockerfile` is included for hosts without Streamlit Cloud's
`packages.txt`/`requirements.txt` auto-detection. Re-enabling YouTube on the live demo means
deploying from this instead, with enough RAM for the full app under active use (Render's free
512MB tier was not enough — confirmed by an actual OOM running the real pipeline, not just a
theoretical concern).

```bash
docker build -t videodigest .
docker run -p 8501:8501 -e PORT=8501 -e ANTHROPIC_API_KEY=sk-ant-... videodigest
```

On Render: **New → Web Service**, connect this repo, environment **Docker** (it auto-detects
the `Dockerfile`), add `ANTHROPIC_API_KEY` / `YOUTUBE_COOKIES` / `WHISPER_MODEL` under
**Environment**. Render injects `$PORT` automatically — the `CMD` already binds to it.

The image pins a CPU-only `torch` build on Linux (see `requirements.txt`) — the default PyPI
wheel bundles ~10GB of unused CUDA libraries even without a GPU, which matters on a
free-tier build/storage budget.
