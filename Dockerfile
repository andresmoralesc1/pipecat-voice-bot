FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    portaudio19-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

RUN useradd -m -u 1001 pipecat && \
    chown -R pipecat:pipecat /app

USER pipecat

EXPOSE 8765

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["python", "bot_telnyx.py", "-t", "telnyx", "-x", "https://telnyx.anfitrion.online", "--host", "0.0.0.0", "--port", "8765"]
