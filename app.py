import os
import sys

import streamlit as st
from dotenv import load_dotenv

# stdout is block-buffered (not line-buffered) when it isn't a terminal, which is
# the case in every hosted deployment -- since this process never exits between
# reruns, print() output (ours and every core/utils module's) can sit in an
# unflushed buffer indefinitely and never reach the platform's logs. Force
# line-buffering so `print()` actually shows up when you need it for debugging.
sys.stdout.reconfigure(line_buffering=True)

# Must run before core imports: transcriber reads WHISPER_MODEL at import time
load_dotenv()

from utils.audio_processor import process_input, DOWNLOAD_DIR
from utils.export import build_txt, build_pdf, safe_filename
from core.transcriber import transcribe_all
from core.summarize import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, ask_question
from core.vector_store import meeting_id

st.set_page_config(page_title="AI Meeting Assistant", page_icon="🎙️", layout="wide")

if "result" not in st.session_state:
    st.session_state.result = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.title("🎙️ AI Meeting Assistant")
st.caption("Turn a recording into a summary, action items, decisions, and a chat-ready knowledge base.")

with st.sidebar:
    st.header("New Meeting")
    input_mode = st.radio("Input type", ["YouTube URL", "Upload audio or video file"])

    source = None
    if input_mode == "YouTube URL":
        url = st.text_input("YouTube URL")
        if url.strip():
            source = url.strip()
    else:
        # ffmpeg (via pydub) pulls the audio track straight out of a video
        # container -- no separate video path needed, just accept these too.
        uploaded = st.file_uploader(
            "Upload audio or video file",
            type=["mp3", "wav", "m4a", "flac", "ogg", "mp4", "mov", "mkv", "avi", "webm", "m4v"],
        )
        if uploaded is not None:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            local_path = os.path.join(DOWNLOAD_DIR, uploaded.name)
            with open(local_path, "wb") as f:
                f.write(uploaded.getbuffer())
            source = local_path

    process_clicked = st.button(
        "Process Meeting", disabled=source is None, type="primary", use_container_width=True
    )

# Runs only on the rerun where the button was actually clicked -- every other
# rerun (chat input, download click, etc.) skips straight to reading session_state.
if process_clicked and source:
    try:
        with st.status("Preparing audio...", expanded=True) as status:
            chunks = process_input(source)
            status.update(label="Audio ready", state="complete")

        with st.status("Transcribing with Whisper...", expanded=True) as status:
            transcript = transcribe_all(chunks)
            status.update(label="Transcription complete", state="complete")

        with st.status("Generating title & summary...", expanded=True) as status:
            title = generate_title(transcript)
            summary = summarize(transcript)
            status.update(label="Summary ready", state="complete")

        with st.status("Extracting action items, decisions & questions...", expanded=True) as status:
            action_items = extract_action_items(transcript)
            key_decisions = extract_key_decisions(transcript)
            questions = extract_questions(transcript)
            status.update(label="Extraction complete", state="complete")

        with st.status("Building searchable knowledge base...", expanded=True) as status:
            rag_chain = build_rag_chain(transcript, meeting_id(source))
            status.update(label="Knowledge base ready", state="complete")

        st.session_state.result = {
            "title": title,
            "transcript": transcript,
            "summary": summary,
            "action_items": action_items,
            "key_decisions": key_decisions,
            "questions": questions,
            "rag_chain": rag_chain,
        }
        st.session_state.chat_history = []  # new meeting -> old chat no longer applies
    except Exception as e:
        st.error(f"Processing failed: {e}")

result = st.session_state.result

if not result:
    st.info("👈 Enter a YouTube URL or upload an audio file, then click **Process Meeting** to get started.")
else:
    st.subheader(result["title"])

    tab_summary, tab_actions, tab_decisions, tab_questions, tab_transcript = st.tabs(
        ["Summary", "Action Items", "Key Decisions", "Questions", "Full Transcript"]
    )
    with tab_summary:
        st.write(result["summary"])
    with tab_actions:
        st.write(result["action_items"])
    with tab_decisions:
        st.write(result["key_decisions"])
    with tab_questions:
        st.write(result["questions"])
    with tab_transcript:
        st.text_area("Transcript", result["transcript"], height=400, label_visibility="collapsed")

    st.divider()
    st.subheader("📤 Export")
    filename = safe_filename(result["title"])
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download as .txt",
            data=build_txt(result),
            file_name=f"{filename}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "Download as .pdf",
            data=build_pdf(result),
            file_name=f"{filename}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    st.divider()
    st.subheader("💬 Chat with your meeting")

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    question = st.chat_input("Ask a question about this meeting...")
    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            try:
                answer = ask_question(result["rag_chain"], question)
            except Exception as e:
                answer = f"Something went wrong answering that: {e}"
            st.write(answer)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
