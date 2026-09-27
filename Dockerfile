FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Pre-cache Whisper base model during build so container boots in 1s without runtime HF downloads
RUN python -c "import faster_whisper; faster_whisper.WhisperModel('base', device='cpu', compute_type='int8')"
COPY . .
ENV WHISPER_MODEL=base
ENV WHISPER_DEVICE=cpu
ENV WHISPER_COMPUTE_TYPE=int8
ENV WHISPER_BEAM_SIZE=1
ENV WHISPER_BEST_OF=1
ENV WHISPER_THREADS=2
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
