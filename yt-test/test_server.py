"""Throwaway diagnostic: does yt-dlp reach YouTube from THIS host's network?
Runs once at container startup, serves the static result on every request.
Delete this whole yt-test/ directory once the question is answered.
"""
import http.server
import os
import socketserver

import yt_dlp

TEST_VIDEO = "https://www.youtube.com/watch?v=GecQwh2iwJY"


def _cookiefile_from_env() -> str | None:
    cookies = os.environ.get("YOUTUBE_COOKIES")
    if not cookies:
        return None
    path = "/tmp/cookies.txt"
    with open(path, "w") as f:
        f.write(cookies)
    return path


def run_test() -> str:
    try:
        opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "extractor_args": {"youtube": {"player_client": ["default", "-tv_downgraded"]}},
        }
        cookiefile = _cookiefile_from_env()
        if cookiefile:
            opts["cookiefile"] = cookiefile
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(TEST_VIDEO, download=False)
        formats = [f for f in info.get("formats", []) if f.get("acodec") != "none"]
        auth = "WITH cookies" if cookiefile else "WITHOUT cookies"
        return f"SUCCESS ({auth}): {len(formats)} real audio formats found from this host's network."
    except Exception as e:
        auth = "WITH cookies" if cookiefile else "WITHOUT cookies"
        return f"FAILED ({auth}): {type(e).__name__}: {e}"


RESULT = run_test()
print(RESULT, flush=True)


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(RESULT.encode())

    def log_message(self, *args):
        pass  # keep the logs to just the one result line


port = int(os.environ.get("PORT", 8000))
with socketserver.TCPServer(("0.0.0.0", port), Handler) as httpd:
    httpd.serve_forever()
