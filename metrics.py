#
# Metrics and Monitoring for Pipecat Voice Bot
# Structured logging and performance tracking
#
"""Metrics collection and structured logging system for voice bot monitoring."""
import time
import functools
from typing import Callable, Any, TYPE_CHECKING
from collections import defaultdict
from datetime import datetime
from loguru import logger as loguru_logger

if TYPE_CHECKING:
    from collections.abc import Counter


class BotMetrics:
    """
    Metrics collector for voice bot operations.

    Tracks:
    - Call statistics (total, active, completed, failed)
    - API call performance (latency, errors, retries)
    - LLM/STT/TTS performance
    - Conversation metrics (duration, turns)
    """

    def __init__(self):
        # Call metrics
        self._calls_total = 0
        self._calls_active = 0
        self._calls_completed = 0
        self._calls_failed = 0
        self._call_start_times = {}

        # API metrics
        self._api_calls_total = 0
        self._api_calls_success = 0
        self._api_calls_failed = 0
        self._api_latency_sum = 0.0
        self._api_latency_count = 0
        self._api_errors_by_endpoint: dict[str, int] = defaultdict(int)
        self._api_retries_total = 0

        # Service metrics
        self._stt_latency_sum = 0.0
        self._stt_latency_count = 0
        self._tts_latency_sum = 0.0
        self._tts_latency_count = 0
        self._llm_latency_sum = 0.0
        self._llm_latency_count = 0

        # Conversation metrics
        self._conversation_durations = []
        self._conversation_turns = []
        self._current_turns = {}

        # Function call metrics
        self._function_calls: dict[str, int] = defaultdict(int)
        self._function_call_failures: dict[str, int] = defaultdict(int)

    def call_started(self, call_id: str) -> None:
        """Record the start of a new call."""
        self._calls_total += 1
        self._calls_active += 1
        self._call_start_times[call_id] = time.time()
        self._current_turns[call_id] = 0
        loguru_logger.info(f"call_started", call_id=call_id, timestamp=datetime.now().isoformat())

    def call_ended(self, call_id: str, success: bool = True) -> None:
        """Record the end of a call."""
        if call_id not in self._call_start_times:
            loguru_logger.warning(f"call_ended without call_started", call_id=call_id)
            return

        duration = time.time() - self._call_start_times.pop(call_id)
        turns = self._current_turns.pop(call_id, 0)

        self._calls_active -= 1
        if success:
            self._calls_completed += 1
        else:
            self._calls_failed += 1

        self._conversation_durations.append(duration)
        self._conversation_turns.append(turns)

        loguru_logger.info(
            "call_ended",
            call_id=call_id,
            duration_seconds=round(duration, 2),
            turns=turns,
            success=success,
            timestamp=datetime.now().isoformat()
        )

    def api_call_made(self, endpoint: str, latency_ms: float, success: bool, retries: int = 0) -> None:
        """Record an API call."""
        self._api_calls_total += 1
        self._api_retries_total += retries

        if success:
            self._api_calls_success += 1
        else:
            self._api_calls_failed += 1
            self._api_errors_by_endpoint[endpoint] += 1

        self._api_latency_sum += latency_ms
        self._api_latency_count += 1

        loguru_logger.info(
            "api_call",
            endpoint=endpoint,
            latency_ms=round(latency_ms, 2),
            success=success,
            retries=retries
        )

    def stt_processed(self, latency_ms: float) -> None:
        """Record STT processing latency."""
        self._stt_latency_sum += latency_ms
        self._stt_latency_count += 1

    def tts_generated(self, latency_ms: float) -> None:
        """Record TTS generation latency."""
        self._tts_latency_sum += latency_ms
        self._tts_latency_count += 1

    def llm_processed(self, latency_ms: float) -> None:
        """Record LLM processing latency."""
        self._llm_latency_sum += latency_ms
        self._llm_latency_count += 1

    def conversation_turn(self, call_id: str) -> None:
        """Record a conversation turn (user spoke)."""
        if call_id in self._current_turns:
            self._current_turns[call_id] += 1

    def function_called(self, function_name: str, success: bool = True) -> None:
        """Record a function call."""
        self._function_calls[function_name] += 1
        if not success:
            self._function_call_failures[function_name] += 1

        loguru_logger.info(
            "function_call",
            function=function_name,
            success=success
        )

    # Statistics properties
    @property
    def calls_total(self) -> int:
        return self._calls_total

    @property
    def calls_active(self) -> int:
        return self._calls_active

    @property
    def calls_completed(self) -> int:
        return self._calls_completed

    @property
    def calls_failed(self) -> int:
        return self._calls_failed

    @property
    def completion_rate(self) -> float:
        if self._calls_total == 0:
            return 0.0
        return round(self._calls_completed / self._calls_total * 100, 2)

    @property
    def avg_call_duration(self) -> float:
        if not self._conversation_durations:
            return 0.0
        return round(sum(self._conversation_durations) / len(self._conversation_durations), 2)

    @property
    def avg_conversation_turns(self) -> float:
        if not self._conversation_turns:
            return 0.0
        return round(sum(self._conversation_turns) / len(self._conversation_turns), 2)

    @property
    def avg_api_latency(self) -> float:
        if self._api_latency_count == 0:
            return 0.0
        return round(self._api_latency_sum / self._api_latency_count, 2)

    @property
    def avg_stt_latency(self) -> float:
        if self._stt_latency_count == 0:
            return 0.0
        return round(self._stt_latency_sum / self._stt_latency_count, 2)

    @property
    def avg_tts_latency(self) -> float:
        if self._tts_latency_count == 0:
            return 0.0
        return round(self._tts_latency_sum / self._tts_latency_count, 2)

    @property
    def avg_llm_latency(self) -> float:
        if self._llm_latency_count == 0:
            return 0.0
        return round(self._llm_latency_sum / self._llm_latency_count, 2)

    @property
    def api_error_rate(self) -> float:
        if self._api_calls_total == 0:
            return 0.0
        return round(self._api_calls_failed / self._api_calls_total * 100, 2)

    def get_summary(self) -> dict:
        """Get a summary of all metrics."""
        return {
            "calls": {
                "total": self.calls_total,
                "active": self.calls_active,
                "completed": self.calls_completed,
                "failed": self.calls_failed,
                "completion_rate": self.completion_rate,
                "avg_duration": self.avg_call_duration,
                "avg_turns": self.avg_conversation_turns,
            },
            "api": {
                "total_calls": self._api_calls_total,
                "success": self._api_calls_success,
                "failed": self._api_calls_failed,
                "error_rate": self.api_error_rate,
                "avg_latency_ms": self.avg_api_latency,
                "total_retries": self._api_retries_total,
                "errors_by_endpoint": dict(self._api_errors_by_endpoint),
            },
            "services": {
                "avg_stt_latency_ms": self.avg_stt_latency,
                "avg_tts_latency_ms": self.avg_tts_latency,
                "avg_llm_latency_ms": self.avg_llm_latency,
            },
            "functions": {
                "calls": dict(self._function_calls),
                "failures": dict(self._function_call_failures),
            },
        }

    def log_summary(self) -> None:
        """Log a summary of all metrics."""
        summary = self.get_summary()
        loguru_logger.info("metrics_summary", **summary)


# Global metrics instance
metrics = BotMetrics()


def track_call(func: Callable) -> Callable:
    """
    Decorator to track call metrics for async functions.

    Usage:
        @track_call
        async def handle_some_call(params):
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        call_id = kwargs.get("call_id") or f"call_{int(time.time() * 1000)}"
        metrics.call_started(call_id)
        try:
            result = await func(*args, **kwargs)
            metrics.call_ended(call_id, success=True)
            return result
        except Exception as e:
            metrics.call_ended(call_id, success=False)
            loguru_logger.error(f"call_error", call_id=call_id, error=str(e))
            raise

    return wrapper


def track_api_call(endpoint: str):
    """
    Decorator to track API call metrics.

    Usage:
        @track_api_call("reservations")
        async def call_reservations_api(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            retries = kwargs.get("attempt", 0)
            try:
                result = await func(*args, **kwargs)
                latency_ms = (time.time() - start_time) * 1000
                success = result.get("success", True) if isinstance(result, dict) else True
                metrics.api_call_made(endpoint, latency_ms, success, retries)
                return result
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                metrics.api_call_made(endpoint, latency_ms, False, retries)
                loguru_logger.error(f"api_error", endpoint=endpoint, error=str(e))
                raise

        return wrapper
    return decorator


class AdaptiveLatencyTracker:
    """Track and adapt latency thresholds based on recent performance."""

    def __init__(self, window_size: int = 100):
        self._window_size = window_size
        self._recent_latencies: list[float] = []
        self._latency_threshold_ms = 2000.0  # Default threshold

    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        self._recent_latencies.append(latency_ms)
        if len(self._recent_latencies) > self._window_size:
            self._recent_latencies.pop(0)

    def get_threshold(self) -> float:
        """Get adaptive latency threshold based on p95 of recent latencies."""
        if not self._recent_latencies:
            return self._latency_threshold_ms

        sorted_latencies = sorted(self._recent_latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[p95_index]

        # Add 20% buffer to p95
        return p95_latency * 1.2

    @property
    def avg_latency(self) -> float:
        """Get average latency."""
        if not self._recent_latencies:
            return 0.0
        return sum(self._recent_latencies) / len(self._recent_latencies)

    @property
    def p50_latency(self) -> float:
        """Get median (p50) latency."""
        if not self._recent_latencies:
            return 0.0
        sorted_latencies = sorted(self._recent_latencies)
        return sorted_latencies[len(sorted_latencies) // 2]


# Global latency tracker
latency_tracker = AdaptiveLatencyTracker()
