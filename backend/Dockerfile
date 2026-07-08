# Backend: FastAPI + yt-dlp + ffmpeg + deno
FROM python:3.12-slim

# ffmpeg for conversion; curl/unzip to fetch deno; ca-certificates for TLS.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Deno gives yt-dlp a JS runtime to solve YouTube's signature challenge.
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh
ENV PATH="/usr/local/bin:${PATH}"

WORKDIR /app

# Install Python deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -U --pre "yt-dlp[default]" \
    && pip install --no-cache-dir fastapi "uvicorn[standard]" python-multipart

COPY app ./app

ENV OUTPUT_DIR=/tmp/audtube
EXPOSE 8000

# Render provides $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
