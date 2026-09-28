import yt_dlp
from pydub import AudioSegment
import os

DOWNLOAD_DIR = 'downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def _cookiefile_from_env() -> str | None:
    """Hosted deployments get IP-blocked by YouTube (403) without an
    authenticated session. YOUTUBE_COOKIES holds a full cookies.txt export
    (Netscape format) as a secret; write it out once per process so yt-dlp
    can use it. Unset locally -- local downloads work without it."""
    cookies = os.getenv("YOUTUBE_COOKIES")
    if not cookies:
        print("YOUTUBE_COOKIES not set -- downloading without authentication.")
        return None
    path = os.path.join(DOWNLOAD_DIR, "cookies.txt")
    if not os.path.isfile(path):
        with open(path, "w") as f:
            f.write(cookies)
    header_ok = cookies.lstrip().startswith(("# Netscape", "# HTTP Cookie File"))
    print(f"Using YouTube cookies from {path} ({len(cookies)} chars, "
          f"{'looks like valid Netscape format' if header_ok else 'MISSING expected Netscape header -- check how the secret was pasted'}).")
    return path


def download_youtube_audio(url :str) ->str:
    output_path = os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        "quiet": True,
        # yt-dlp's default player client for logged-in sessions (tv_downgraded) is
        # currently broken upstream (yt-dlp/yt-dlp#17389, "The page needs to be
        # reloaded") -- force the clients yt-dlp's own maintainers recommend as a
        # workaround until that's fixed in a release.
        'extractor_args': {'youtube': {'player_client': ['default', 'web_embedded']}},
    }

    cookiefile = _cookiefile_from_env()
    if cookiefile:
        ydl_opts['cookiefile'] = cookiefile

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = os.path.splitext(ydl.prepare_filename(info))[0] + '.wav'
    return filename

def convert_to_wav(input_file: str) -> str:
    output_path = os.path.splitext(input_file)[0] + '_converted.wav'
    audio = AudioSegment.from_file(input_file)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format='wav')
    return output_path

def chunk_audio(wav_path:str, chunk_minutes:int = 10) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000
    chunks = []

    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start: start+chunk_ms]
        base = os.path.splitext(wav_path)[0]
        chunk_path = f"{base}_chunk_{i}.wav"
        chunk.export(chunk_path, format='wav')
        chunks.append(chunk_path)
    return chunks


def process_input(source: str) -> list:
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected Youtube URL. Downloading audio...")
        raw_path = download_youtube_audio(source)
    else:
        print("Detected local audio file. Converting to WAV...")
        if not os.path.isfile(source):
            raise FileNotFoundError(f"Audio file not found: {source}")
        raw_path = source
    
    wav_path = convert_to_wav(raw_path)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready - {len(chunks)} chunks created.")
    return chunks
