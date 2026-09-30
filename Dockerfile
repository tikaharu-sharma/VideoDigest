# Used for hosts without Streamlit Cloud's packages.txt/requirements.txt
# auto-detection (e.g. Render) -- same app, same deps, just a different host/IP,
# to test whether YouTube's IP-level blocking is specific to Streamlit Cloud.
FROM python:3.11-slim

# ffmpeg: yt-dlp/pydub/Whisper all depend on it silently, no clear error if missing
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render (and most PaaS hosts) inject $PORT at runtime -- must bind to it and to
# 0.0.0.0, not localhost, for external traffic to reach the container. Shell form
# (not exec-array form) so $PORT actually gets substituted.
CMD streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
