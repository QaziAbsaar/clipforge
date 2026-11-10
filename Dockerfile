FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY clipforge ./clipforge
COPY clipforge_web ./clipforge_web
COPY audio_library ./audio_library
ENV CLIPFORGE_HOST=0.0.0.0 CLIPFORGE_PORT=8000 CLIPFORGE_DATA=/data HF_HOME=/data/hf PYTHONUNBUFFERED=1
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')" || exit 1
CMD ["python", "-m", "clipforge_web"]
