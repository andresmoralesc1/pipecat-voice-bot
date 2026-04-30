#
# TAREA 19: Timeout y Retry Logic para TTS
# Función wrapper para llamadas TTS con timeout dinámico y reintentos
#

import asyncio
from asyncio import TimeoutError as AsyncTimeoutError
from loguru import logger


async def tts_call_with_timeout(tts_service, text: str, max_retries: int = 2):
    """
    Ejecutar llamada TTS con timeout dinámico y reintentos automáticos.

    Args:
        tts_service: Servicio TTS de Cartesia
        text: Texto a sintetizar
        max_retries: Número máximo de reintentos (default: 2)

    Returns:
        Resultado de la llamada TTS

    Raises:
        AsyncTimeoutError: Si todos los reintentos fallan
        Exception: Si hay otro error irrecuperable
    """
    for attempt in range(max_retries + 1):
        try:
            # Timeout dinámico basado en la longitud del texto
            # Fórmula: 2s base + 0.5s * longitud del texto / 100
            # Ejemplo: 200 caracteres → 2 + 0.5 * 2 = 3 segundos
            text_length = len(text)
            timeout = 2 + (text_length / 100) * 0.5

            logger.debug(f"🎤 TTS call (intento {attempt + 1}/{max_retries + 1}, timeout={timeout:.2f}s, longitud={text_length} caracteres)")

            # Ejecutar llamada TTS con timeout
            result = await asyncio.wait_for(
                tts_service.generate(text),
                timeout=timeout
            )

            if attempt > 0:
                logger.info(f"✅ TTS call exitoso después de {attempt} reintentos")

            return result

        except AsyncTimeoutError:
            if attempt < max_retries:
                wait_time = 0.5 * (attempt + 1)  # Backoff exponencial: 0.5s, 1.0s, 1.5s...
                logger.warning(
                    f"⚠️ TTS timeout (intento {attempt + 1}/{max_retries + 1}, "
                    f"timeout={timeout:.2f}s), reintentando en {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"❌ TTS timeout CRÍTICO después de {max_retries + 1} intentos "
                    f"(timeout={timeout:.2f}s, longitud={text_length} caracteres)"
                )
                raise

        except Exception as e:
            logger.error(f"❌ Error TTS irrecuperable: {e}")
            raise