#
# TAREA 19: Timeout y Retry Logic para TTS
# Wrapper con timeout dinámico y reintentos automáticos
#

import asyncio
import time
from loguru import logger
from typing import Optional, Callable, Any
from functools import wraps


# ============================================================================
# Configuración de timeouts y reintentos
# ============================================================================

DEFAULT_TIMEOUT_BASE = 2.0  # Timeout base en segundos
DEFAULT_TIMEOUT_PER_CHAR = 0.005  # 5ms por carácter
MAX_RETRIES = 2
RETRY_DELAY_BASE = 0.5  # Segundos de espera entre reintentos


def calculate_tts_timeout(text: str, base: float = DEFAULT_TIMEOUT_BASE) -> float:
    """
    Calcular timeout dinámico basado en la longitud del texto.

    Args:
        text: Texto a procesar
        base: Timeout base en segundos

    Returns:
        Timeout calculado en segundos
    """
    # Timeout = base + (longitud del texto * factor por carácter)
    # Ejemplo: "Hola mundo" (10 chars) = 2 + (10 * 0.005) = 2.05s
    # Ejemplo: Texto largo (200 chars) = 2 + (200 * 0.005) = 3.0s
    timeout = base + (len(text) * DEFAULT_TIMEOUT_PER_CHAR)
    
    # Timeout máximo de 10 segundos
    return min(timeout, 10.0)


async def tts_with_timeout(
    tts_func: Callable,
    text: str,
    max_retries: int = MAX_RETRIES,
    timeout_base: float = DEFAULT_TIMEOUT_BASE,
) -> Any:
    """
    Ejecutar función TTS con timeout y reintentos automáticos.

    Args:
        tts_func: Función TTS a ejecutar (puede ser async o sync)
        text: Texto a procesar
        max_retries: Número máximo de reintentos
        timeout_base: Timeout base en segundos

    Returns:
        Resultado de la función TTS

    Raises:
        TimeoutError: Si todos los reintentos fallan
        Exception: Si ocurre otro error no relacionado con timeout
    """
    timeout = calculate_tts_timeout(text, timeout_base)
    
    for attempt in range(max_retries + 1):
        try:
            # Ejecutar con timeout
            if asyncio.iscoroutinefunction(tts_func):
                result = await asyncio.wait_for(
                    tts_func(text),
                    timeout=timeout
                )
            else:
                # Si es una función síncrona, ejecutar en executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: tts_func(text)
                )
            
            # Si tiene éxito, registrar y devolver
            if attempt > 0:
                logger.info(f"✅ TTS retry successful (attempt {attempt + 1})")
            
            return result
            
        except asyncio.TimeoutError:
            if attempt < max_retries:
                # Calcular delay con backoff exponencial
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(
                    f"⚠️ TTS timeout ({timeout:.2f}s) on attempt {attempt + 1}, "
                    f"retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"❌ TTS timeout después de {max_retries + 1} intentos "
                    f"(timeout: {timeout:.2f}s, text: '{text[:40]}...')"
                )
                raise
        
        except Exception as e:
            # Otros errores no se reintentan
            logger.error(f"❌ Error en TTS (no timeout): {e}")
            raise


class TTSRetryWrapper:
    """
    Wrapper para servicios TTS con timeout y reintentos automáticos.

    Uso:
        wrapper = TTSRetryWrapper(tts_service)
        await wrapper.generate("Texto a generar")
    """

    def __init__(
        self,
        tts_service: Any,
        max_retries: int = MAX_RETRIES,
        timeout_base: float = DEFAULT_TIMEOUT_BASE,
    ):
        """
        Inicializar wrapper TTS.

        Args:
            tts_service: Servicio TTS a envolver
            max_retries: Número máximo de reintentos
            timeout_base: Timeout base en segundos
        """
        self._tts_service = tts_service
        self._max_retries = max_retries
        self._timeout_base = timeout_base
        logger.info(
            f"✅ TTS Retry Wrapper inicializado "
            f"(retries: {max_retries}, timeout_base: {timeout_base}s)"
        )

    async def generate(self, text: str, **kwargs) -> Any:
        """
        Generar audio desde texto con timeout y reintentos.

        Args:
            text: Texto a generar
            **kwargs: Argumentos adicionales para el servicio TTS

        Returns:
            Resultado del servicio TTS
        """
        timeout = calculate_tts_timeout(text, self._timeout_base)
        
        for attempt in range(self._max_retries + 1):
            try:
                # Ejecutar con timeout
                result = await asyncio.wait_for(
                    self._tts_service.generate(text, **kwargs),
                    timeout=timeout
                )
                
                if attempt > 0:
                    logger.info(f"✅ TTS retry successful (attempt {attempt + 1})")
                
                return result
                
            except asyncio.TimeoutError:
                if attempt < self._max_retries:
                    delay = RETRY_DELAY_BASE * (2 ** attempt)
                    logger.warning(
                        f"⚠️ TTS timeout ({timeout:.2f}s) on attempt {attempt + 1}, "
                        f"retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"❌ TTS timeout después de {self._max_retries + 1} intentos "
                        f"(timeout: {timeout:.2f}s)"
                    )
                    # En lugar de fallar completamente, devolver un resultado fallback
                    # Esto permite que la conversación continúe
                    logger.warning("⚠️ Devolviendo resultado fallback para TTS")
                    return None
            
            except Exception as e:
                logger.error(f"❌ Error en TTS (no timeout): {e}")
                raise

    def __getattr__(self, name: str) -> Any:
        """Delegar atributos no manejados al servicio TTS original."""
        return getattr(self._tts_service, name)


# ============================================================================
# Decoradores para facilitar el uso
# ============================================================================

def with_tts_timeout(
    max_retries: int = MAX_RETRIES,
    timeout_base: float = DEFAULT_TIMEOUT_BASE,
):
    """
    Decorador para agregar timeout y reintentos a funciones TTS.

    Args:
        max_retries: Número máximo de reintentos
        timeout_base: Timeout base en segundos

    Uso:
        @with_tts_timeout(max_retries=2)
        async def my_tts_function(text: str):
            return await tts_service.generate(text)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(text: str, *args, **kwargs):
            timeout = calculate_tts_timeout(text, timeout_base)
            
            for attempt in range(max_retries + 1):
                try:
                    result = await asyncio.wait_for(
                        func(text, *args, **kwargs),
                        timeout=timeout
                    )
                    
                    if attempt > 0:
                        logger.info(f"✅ TTS retry successful (attempt {attempt + 1})")
                    
                    return result
                    
                except asyncio.TimeoutError:
                    if attempt < max_retries:
                        delay = RETRY_DELAY_BASE * (2 ** attempt)
                        logger.warning(
                            f"⚠️ TTS timeout ({timeout:.2f}s) on attempt {attempt + 1}, "
                            f"retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"❌ TTS timeout después de {max_retries + 1} intentos"
                        )
                        # Devolver None en lugar de fallar
                        return None
                
                except Exception as e:
                    logger.error(f"❌ Error en TTS: {e}")
                    raise
        
        return async_wrapper
    
    return decorator
