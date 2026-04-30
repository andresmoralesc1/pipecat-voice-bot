#
# TAREA 19: Monitoreo de Latencias TTS
# Sistema de monitoreo y alertas para latencias TTS anormales
#

import time
from collections import deque
from statistics import median
from loguru import logger
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import contextmanager


class TTSLatencyMonitor:
    """
    Monitor de latencias TTS con detección de anomalías y alertas.

    Características:
    - Monitoreo continuo de latencias TTS
    - Detección de anomalías (>2s warning, >4s critical)
    - Alertas proactivas
    - Métricas de salud del sistema
    """

    def __init__(self, window_size: int = 50):
        """
        Inicializar monitor de latencias TTS.

        Args:
            window_size: Tamaño de la ventana de latencias a mantener
        """
        self._latencies = deque(maxlen=window_size)
        self._threshold_warning = 2.0  # 2 segundos
        self._threshold_critical = 4.0  # 4 segundos

        # Estadísticas adicionales
        self._total_calls = 0
        self._high_latency_calls = 0
        self._critical_calls = 0

    def record_latency(self, latency_ms: float):
        """
        Registrar latencia TTS y generar alertas si es necesario.

        Args:
            latency_ms: Latencia en segundos
        """
        self._latencies.append(latency_ms)
        self._total_calls += 1

        # Detectar anomalías y generar alertas
        if latency_ms > self._threshold_critical:
            self._critical_calls += 1
            logger.critical(
                f"🚨 CRÍTICO: Latencia TTS {latency_ms:.3f}s - "
                f"Muy por encima del umbral ({self._threshold_critical}s)"
            )
        elif latency_ms > self._threshold_warning:
            self._high_latency_calls += 1
            logger.warning(
                f"⚠️ ADVERTENCIA: Latencia TTS {latency_ms:.3f}s - "
                f"Por encima del umbral ({self._threshold_warning}s)"
            )
        else:
            logger.debug(f"✅ Latencia TTS normal: {latency_ms:.3f}s")

    def get_health_status(self) -> Dict:
        """
        Obtener estado de salud del sistema TTS.

        Returns:
            Dict con estado, latencia promedio, y tasa de llamadas problemáticas
        """
        if len(self._latencies) == 0:
            return {
                "status": "unknown",
                "avg_latency": 0.0,
                "median_latency": 0.0,
                "high_latency_rate": 0.0,
                "total_calls": 0
            }

        avg_latency = sum(self._latencies) / len(self._latencies)
        median_latency = median(self._latencies)

        # Calcular tasa de llamadas problemáticas
        if self._total_calls > 0:
            high_latency_rate = (self._high_latency_calls + self._critical_calls) / self._total_calls
        else:
            high_latency_rate = 0.0

        # Determinar estado de salud
        if avg_latency > self._threshold_critical:
            status = "critical"
        elif avg_latency > self._threshold_warning:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "avg_latency": round(avg_latency, 3),
            "median_latency": round(median_latency, 3),
            "high_latency_rate": round(high_latency_rate * 100, 2),  # Porcentaje
            "total_calls": self._total_calls,
            "high_latency_calls": self._high_latency_calls,
            "critical_calls": self._critical_calls
        }

    def should_use_long_filler(self) -> bool:
        """
        Decidir si usar filler largo basado en latencia reciente.

        Returns:
            True si el promedio reciente de latencia > 1.5s
        """
        if len(self._latencies) < 10:
            return False  # No hay suficientes datos

        # Calcular promedio de las últimas 10 latencias
        recent_latencies = list(self._latencies)[-10:]
        recent_avg = sum(recent_latencies) / 10

        should_use_long = recent_avg > 1.5

        if should_use_long:
            logger.warning(
                f"⚠️ Latencia reciente alta ({recent_avg:.3f}s), "
                f"recomendado usar fillers largos"
            )

        return should_use_long

    def get_summary(self) -> Dict:
        """
        Obtener resumen completo del sistema de monitoreo.

        Returns:
            Dict con todas las métricas y estadísticas
        """
        health = self.get_health_status()

        return {
            "monitor": {
                "window_size": len(self._latencies),
                "threshold_warning": self._threshold_warning,
                "threshold_critical": self._threshold_critical,
                "timestamp": datetime.now().isoformat()
            },
            "health": health,
            "statistics": {
                "min_latency": round(min(self._latencies), 3) if self._latencies else 0.0,
                "max_latency": round(max(self._latencies), 3) if self._latencies else 0.0,
                "p95_latency": self._calculate_percentile(95),
                "p99_latency": self._calculate_percentile(99)
            }
        }

    def _calculate_percentile(self, percentile: int) -> float:
        """
        Calcular percentil de latencias.

        Args:
            percentile: Percentil a calcular (0-100)

        Returns:
            Valor del percentil calculado
        """
        if len(self._latencies) == 0:
            return 0.0

        sorted_latencies = sorted(self._latencies)
        index = int(len(sorted_latencies) * percentile / 100)
        return round(sorted_latencies[index], 3)


# Instancia global del monitor
tts_monitor = TTSLatencyMonitor()


# ============================================================================
# Funciones de integración con el sistema existente
# ============================================================================

def record_tts_latency(latency_ms: float):
    """
    Función helper para registrar latencia TTS.

    Args:
        latency_ms: Latencia en segundos
    """
    tts_monitor.record_latency(latency_ms)


def get_tts_health_status() -> Dict:
    """
    Función helper para obtener estado de salud TTS.

    Returns:
        Dict con estado de salud del sistema
    """
    return tts_monitor.get_health_status()


def get_tts_summary() -> Dict:
    """
    Función helper para obtener resumen del monitor TTS.

    Returns:
        Dict con resumen completo del sistema
    """
    return tts_monitor.get_summary()


# ============================================================================
# Context Manager para medición automática de latencias
# ============================================================================

@contextmanager
def measure_tts_latency(text: str = ""):
    """
    Context manager para medir latencias TTS automáticamente.

    Uso:
        with measure_tts_latency("Texto a procesar"):
            result = await tts_service.generate(text)

    Args:
        text: Texto procesado (para contexto en logs)
    """
    start_time = time.time()
    try:
        yield
    finally:
        latency = time.time() - start_time
        tts_monitor.record_latency(latency)
        logger.debug(f"TTS latency: {latency:.3f}s for '{text[:30]}...'")


# ============================================================================
# Integración con el sistema de métricas existente
# ============================================================================

def log_tts_summary():
    """Imprimir resumen del monitor TTS en los logs."""
    summary = get_tts_summary()
    health = summary["health"]

    logger.info(
        f"📊 TTS Latency Monitor | "
        f"Status: {health['status'].upper()} | "
        f"Avg: {health['avg_latency']:.3f}s | "
        f"Median: {health['median_latency']:.3f}s | "
        f"P95: {summary['statistics']['p95_latency']:.3f}s | "
        f"P99: {summary['statistics']['p99_latency']:.3f}s | "
        f"Warnings: {health['high_latency_calls']} | "
        f"Criticals: {health['critical_calls']}"
    )


def reset_tts_monitor():
    """Reiniciar el monitor TTS."""
    global tts_monitor
    tts_monitor = TTSLatencyMonitor()
    logger.info("🔄 TTS Latency Monitor reiniciado")


# ============================================================================
# Decorador para medir latencias en funciones
# ============================================================================

def track_tts_latency(text_param: str = "text"):
    """
    Decorador para rastrear latencias TTS en funciones.

    Args:
        text_param: Nombre del parámetro que contiene el texto

    Uso:
        @track_tts_latency("text")
        async def my_tts_function(text: str, ...):
            ...
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                latency = time.time() - start_time
                # Intentar obtener el texto para contexto
                text_value = ""
                if text_param in kwargs:
                    text_value = kwargs[text_param]
                elif args and len(args) > 0:
                    # Asumir que el primer argumento posicional es el texto
                    text_value = str(args[0]) if args[0] else ""

                tts_monitor.record_latency(latency)
                logger.debug(f"TTS latency: {latency:.3f}s for '{text_value[:30]}...'")

        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                latency = time.time() - start_time
                text_value = kwargs.get(text_param, "")
                tts_monitor.record_latency(latency)
                logger.debug(f"TTS latency: {latency:.3f}s for '{text_value[:30]}...'")

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator