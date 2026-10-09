# video-agent (VideoDigest — AI Video & Lecture Summarizer)

## What this is
Takes audio from a YouTube URL or a local audio/video file, transcribes it locally with
Whisper, summarizes it and extracts action items/decisions/questions via LangChain LCEL +
Claude's API, and supports RAG-based chat over the transcript via ChromaDB + HuggingFace
embeddings. Streamlit UI (`app.py`) with PDF/TXT export is live at
https://aivideoagent.streamlit.app. YouTube URL input is gated off in the UI there (disabled
radio option, explained inline) — Streamlit Cloud's IP range is blocked by YouTube regardless
of auth; file upload is the only enabled input path on that deployment. The YouTube code path
itself works (verified on Render, see README's Docker section) — this is a hosting choice, not
missing functionality.

## Architecture
- `utils/audio_processor.py` — download/convert/chunk audio. Entry point: `process_input(source)`.
- `core/transcriber.py` — local Whisper transcription. Singleton-cached model via `load_model()`.
- `core/llm.py` — shared `get_llm(model)` for ChatAnthropic (default `claude-haiku-4-5`).
  `core/rag_engine.py` overrides to `claude-sonnet-5` for RAG chat.
- `core/summarize.py` — LCEL map-reduce summarization via Claude. `summarize()`, `generate_title()`.
- `core/extractor.py` — LCEL chains for action items / key decisions / open questions.
  NOTE: unlike summarize.py, these currently send the FULL transcript in one call, not chunked —
  fine for short recordings, will need map-reduce for long ones.
- `core/vector_store.py` — Chroma + HuggingFace embeddings (all-MiniLM-L6-v2).
  One collection per meeting, named by `meeting_id(source)` (hash of the URL/path); rebuilding
  a meeting drops its old collection first. Persisted in `vector_db/`.
- `core/rag_engine.py` — assembles the RAG chain (retriever | prompt | llm | parser).
- `main.py` — orchestrates the full pipeline end-to-end; has an interactive CLI chat loop at the end.
  `load_dotenv()` must stay above the `core` imports (transcriber reads `WHISPER_MODEL` at import).

## Environment
- Python 3.14, managed via a `.venv` (note: this project uses `.venv`, not `venv` — different
  naming convention than my rag-api project).
- `pip3`/`python3 -m pip` — plain `pip` is not aliased in this shell.
- `ffmpeg` required as a system binary (installed via Homebrew) — both yt-dlp and Whisper depend
  on it silently; there's no clear error if it's missing until you try to actually process audio.
- `audioop-lts` is a required dependency because Python 3.13+ removed the stdlib `audioop` module
  that `pydub` depends on.
- Anthropic API key: `ANTHROPIC_API_KEY` in `.env`. Don't pass `api_key=` explicitly —
  `ChatAnthropic` reads the env var itself.
- `requirements.txt` lists direct dependencies only.

## Git workflow
- Feature branches per component, merged via PR on GitHub (not committed directly to main).
- `.gitignore` excludes `.venv/`, `__pycache__/`, `downloads/`, `vector_db/`, `.env`, `.DS_Store`.

## Known gaps / next steps
- YouTube URL ingestion is fragile against upstream yt-dlp/YouTube extraction changes
  (see `utils/audio_processor.py` for the current cookies/player-client workarounds).
  File upload (audio or video) is unaffected and is the reliable path.
