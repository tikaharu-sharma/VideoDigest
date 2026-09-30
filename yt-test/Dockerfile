# Throwaway diagnostic service -- deploy with Render's Root Directory set to
# yt-test/. Just yt-dlp + deno, no ML stack, trivially fits in a 512MB free tier.
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir "yt-dlp[default]==2026.8.19" deno==2.9.7

COPY test_server.py .

CMD ["python", "test_server.py"]
