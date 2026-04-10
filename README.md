# Pipecat Voice Bot

Servicio de asistente de voz con IA usando el framework Pipecat.

## Características

- Speech-to-Text con Deepgram
- LLM con OpenAI GPT-4o
- Text-to-Speech con Deepgram
- Voice Activity Detection con Silero
- Conexión vía Daily (WebRTC)
- Soporte multi-idioma (español por defecto)

## Configuración

1. Copia `.env.example` a `.env`:
   ```bash
   cp .env.example .env
   ```

2. Agrega tus API Keys:
   - `OPENAI_API_KEY` - Para GPT-4o
   - `DEEPGRAM_API_KEY` - Para STT/TTS
   - `DAILY_API_KEY` - Para videoconferencia WebRTC

## Uso

### En desarrollo:
```bash
docker-compose up --build
```

### En producción:
El servicio ya está configurado en el docker-compose principal.

## API Endpoints

- `https://voice.microbts.online` - WebSocket server

## Documentación

- [Pipecat Docs](https://github.com/pipecat-ai/pipecat)
- [Deepgram Docs](https://developers.deepgram.com/)
- [Daily Docs](https://docs.daily.co/)
