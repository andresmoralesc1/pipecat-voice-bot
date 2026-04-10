FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    portaudio19-dev \
    python3-dev \
    libgl1 \
    libegl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgthread-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1001 pipecat && \
    chown -R pipecat:pipecat /app

USER pipecat

# Expose port
EXPOSE 7860

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the application with WebRTC transport
CMD ["python", "bot_server.py", "-t", "webrtc", "--host", "0.0.0.0", "--port", "7860"]
