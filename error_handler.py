#
# Error Handler with Extensive Logging
# Captures detailed context for debugging "cannot unpack" errors
#
"""Enhanced error handling and logging for production debugging."""
import sys
import traceback
from datetime import datetime
from loguru import logger
from typing import Any, Callable
from functools import wraps


def log_error_context(error: Exception, context: dict[str, Any]) -> None:
    """
    Log extensive error context for debugging.

    Args:
        error: The exception that occurred
        context: Dictionary with relevant variables and state
    """
    logger.error("=" * 80)
    logger.error(f"🚨 ERROR DETECTADO: {type(error).__name__}")
    logger.error(f"📅 Timestamp: {datetime.now().isoformat()}")
    logger.error(f"💬 Mensaje: {str(error)}")
    logger.error("-" * 80)

    # Log traceback completo
    logger.error("📍 TRACEBACK COMPLETO:")
    logger.error(traceback.format_exc())

    # Log contexto de variables
    logger.error("-" * 80)
    logger.error("🔍 CONTEXTO DE VARIABLES:")
    for key, value in context.items():
        if value is None:
            logger.error(f"  {key}: None")
        elif isinstance(value, (str, int, float, bool)):
            logger.error(f"  {key}: {value}")
        elif isinstance(value, (list, tuple)):
            logger.error(f"  {key}: {type(value).__name__} (len={len(value)})")
            logger.error(f"    Valor: {value}")
        elif isinstance(value, dict):
            logger.error(f"  {key}: dict con {len(value)} keys")
            logger.error(f"    Keys: {list(value.keys())}")
        else:
            logger.error(f"  {key}: {type(value).__name__}")
            logger.error(f"    Valor: {str(value)[:100]}")

    logger.error("=" * 80)


def safe_unpack_wrapper(func: Callable) -> Callable:
    """
    Decorator to safely unpack function returns and log errors.

    Use this on functions that return tuples where unpack errors might occur.
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"✅ {func.__name__} ejecutado correctamente")
            logger.debug(f"   Resultado tipo: {type(result)}")
            if isinstance(result, tuple):
                logger.debug(f"   Tupla longitud: {len(result)}")
                for i, item in enumerate(result):
                    logger.debug(f"     Item[{i}]: {type(item).__name__} = {str(item)[:50]}")
            return result
        except Exception as e:
            context = {
                "function": func.__name__,
                "args": str(args)[:200],
                "kwargs": str(kwargs)[:200],
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()) if kwargs else [],
            }
            log_error_context(e, context)
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            logger.debug(f"✅ {func.__name__} ejecutado correctamente")
            logger.debug(f"   Resultado tipo: {type(result)}")
            if isinstance(result, tuple):
                logger.debug(f"   Tupla longitud: {len(result)}")
                for i, item in enumerate(result):
                    logger.debug(f"     Item[{i}]: {type(item).__name__} = {str(item)[:50]}")
            return result
        except Exception as e:
            context = {
                "function": func.__name__,
                "args": str(args)[:200],
                "kwargs": str(kwargs)[:200],
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()) if kwargs else [],
            }
            log_error_context(e, context)
            raise

    # Detectar si es async o sync
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def validate_function_return(func: Callable, expected_return_type: str) -> Callable:
    """
    Decorator to validate function return types.

    Args:
        func: Function to wrap
        expected_return_type: Description of expected return type
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)

            # Validar que el resultado sea el tipo esperado
            if expected_return_type == "tuple[bool, list[str]]":
                if not isinstance(result, tuple):
                    logger.error(f"❌ {func.__name__} no devolvió tupla")
                    logger.error(f"   Devolvió: {type(result).__name__}")
                    logger.error(f"   Valor: {result}")
                    # Forzar retorno correcto para no romper
                    return False, [f"Error interno: {func.__name__} devolvió {type(result).__name__} en lugar de tupla"]

                if len(result) != 2:
                    logger.error(f"❌ {func.__name__} devolvió tupla de longitud incorrecta")
                    logger.error(f"   Longitud: {len(result)}, esperada: 2")
                    logger.error(f"   Valor: {result}")
                    return False, [f"Error interno: {func.__name__} devolvió tupla de {len(result)} elementos"]

                if not isinstance(result[0], bool):
                    logger.error(f"❌ {func.__name__} primer elemento no es bool")
                    logger.error(f"   Tipo: {type(result[0]).__name__}")
                    logger.error(f"   Valor: {result[0]}")
                    return False, [f"Error interno: {func.__name__} primer elemento es {type(result[0]).__name__}"]

                if not isinstance(result[1], list):
                    logger.error(f"❌ {func.__name__} segundo elemento no es list")
                    logger.error(f"   Tipo: {type(result[1]).__name__}")
                    logger.error(f"   Valor: {result[1]}")
                    return False, ["Error interno: error de validación"]

            return result

        except Exception as e:
            context = {
                "function": func.__name__,
                "expected_return": expected_return_type,
                "args": str(args)[:200],
                "kwargs": str(kwargs)[:200],
            }
            log_error_context(e, context)
            # Retornar valor seguro por defecto
            return False, [f"Error en {func.__name__}: {str(e)}"]

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)

            # Validar que el resultado sea el tipo esperado
            if expected_return_type == "tuple[bool, list[str]]":
                if not isinstance(result, tuple):
                    logger.error(f"❌ {func.__name__} no devolvió tupla")
                    logger.error(f"   Devolvió: {type(result).__name__}")
                    logger.error(f"   Valor: {result}")
                    # Forzar retorno correcto para no romper
                    return False, [f"Error interno: {func.__name__} devolvió {type(result).__name__} en lugar de tupla"]

                if len(result) != 2:
                    logger.error(f"❌ {func.__name__} devolvió tupla de longitud incorrecta")
                    logger.error(f"   Longitud: {len(result)}, esperada: 2")
                    logger.error(f"   Valor: {result}")
                    return False, [f"Error interno: {func.__name__} devolvió tupla de {len(result)} elementos"]

                if not isinstance(result[0], bool):
                    logger.error(f"❌ {func.__name__} primer elemento no es bool")
                    logger.error(f"   Tipo: {type(result[0]).__name__}")
                    logger.error(f"   Valor: {result[0]}")
                    return False, [f"Error interno: {func.__name__} primer elemento es {type(result[0]).__name__}"]

                if not isinstance(result[1], list):
                    logger.error(f"❌ {func.__name__} segundo elemento no es list")
                    logger.error(f"   Tipo: {type(result[1]).__name__}")
                    logger.error(f"   Valor: {result[1]}")
                    return False, ["Error interno: error de validación"]

            return result

        except Exception as e:
            context = {
                "function": func.__name__,
                "expected_return": expected_return_type,
                "args": str(args)[:200],
                "kwargs": str(kwargs)[:200],
            }
            log_error_context(e, context)
            # Retornar valor seguro por defecto
            return False, [f"Error en {func.__name__}: {str(e)}"]

    # Detectar si es async o sync
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# Logger especial para errores de unpack
class UnpackErrorMonitor:
    """Monitor específico para errores de unpack."""

    def __init__(self):
        self.unpack_errors = []
        self.validation_results = []

    def log_unpack_attempt(self, variable_name: str, value: Any, expected_type: str):
        """Log intento de unpack."""
        logger.debug(f"🔄 Unpack attempt: {variable_name}")
        logger.debug(f"   Expected: {expected_type}")
        logger.debug(f"   Received type: {type(value).__name__}")
        logger.debug(f"   Received value: {str(value)[:100]}")

    def log_validation_result(self, func_name: str, result: Any):
        """Log resultado de validación."""
        self.validation_results.append({
            "timestamp": datetime.now().isoformat(),
            "function": func_name,
            "result_type": type(result).__name__,
            "result_value": str(result)[:200],
        })
        logger.debug(f"✅ Validation logged: {func_name} -> {type(result).__name__}")


# Instancia global del monitor
unpack_monitor = UnpackErrorMonitor()
