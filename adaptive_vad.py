#
# Adaptive VAD (Voice Activity Detection) for Pipecat Voice Bot
# Dynamic VAD parameters based on conversation state and user behavior
#
"""Adaptive Voice Activity Detection for optimized conversation flow."""
from typing import Optional
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.audio.vad.silero import SileroVADAnalyzer
from loguru import logger
from config import settings, conversation_state


class AdaptiveVAD:
    """
    Dynamic VAD that adjusts parameters based on conversation state.

    Benefits:
    - Faster response during active conversation (350ms silence)
    - More relaxed at greeting/start (600ms silence)
    - Reduces false positives and interruptions
    - Better user experience

    States:
    - greeting: More relaxed VAD (user needs time to speak)
    - capturing_location: Standard VAD (expecting specific input)
    - capturing_details: Active VAD (quick back-and-forth)
    - confirming: Active VAD (quick confirmation)
    - completed: Relaxed VAD (closing conversation)
    """

    def __init__(self, initial_mode: str = "relaxed"):
        """
        Initialize Adaptive VAD.

        Args:
            initial_mode: Initial VAD mode ('relaxed' or 'active')
        """
        self._mode = initial_mode
        self._silence_samples = []  # Track recent silence durations for calibration
        self._interruption_count = 0  # Track user interruptions
        self._last_speech_duration = 0.0

    def get_params(self) -> VADParams:
        """
        Get VAD parameters based on current conversation state and mode.

        Returns:
            VADParams with optimized settings for current context
        """
        # Check conversation state for automatic mode selection
        if conversation_state.is_greeting:
            self._mode = "relaxed"
        elif conversation_state.is_active:
            self._mode = "active"

        if self._mode == "active":
            return VADParams(
                silence_duration_ms=settings.VAD_SILENCE_MS_ACTIVE,
                speech_probability=settings.VAD_PROBABILITY_ACTIVE,
                min_volume=settings.VAD_MIN_VOLUME,
            )
        else:  # relaxed mode
            return VADParams(
                silence_duration_ms=settings.VAD_SILENCE_MS_RELAXED,
                speech_probability=settings.VAD_PROBABILITY_RELAXED,
                min_volume=settings.VAD_MIN_VOLUME,
            )

    def get_vad_analyzer(self) -> SileroVADAnalyzer:
        """
        Get a new Silero VAD analyzer with current parameters.

        Returns:
            SileroVADAnalyzer instance with adaptive parameters
        """
        return SileroVADAnalyzer(params=self.get_params())

    def set_mode(self, mode: str) -> None:
        """
        Manually set VAD mode.

        Args:
            mode: 'relaxed' or 'active'
        """
        if mode not in ("relaxed", "active"):
            raise ValueError(f"Invalid VAD mode: {mode}. Must be 'relaxed' or 'active'")
        self._mode = mode
        logger.debug(f"VAD mode set to: {mode}")

    @property
    def mode(self) -> str:
        """Get current VAD mode."""
        return self._mode

    def record_interruption(self) -> None:
        """Record that user interrupted the bot (may indicate need for faster VAD)."""
        self._interruption_count += 1

        # If many interruptions, switch to more active mode
        if self._interruption_count >= 3 and self._mode == "relaxed":
            self._mode = "active"
            logger.debug("Switching to active VAD mode due to frequent interruptions")

    def record_silence_duration(self, duration_ms: float) -> None:
        """
        Record silence duration for adaptive calibration.

        Args:
            duration_ms: Silence duration in milliseconds
        """
        self._silence_samples.append(duration_ms)

        # Keep only recent samples (last 50)
        if len(self._silence_samples) > 50:
            self._silence_samples.pop(0)

    def get_optimal_silence_duration(self) -> int:
        """
        Calculate optimal silence duration based on conversation history.

        Returns:
            Optimal silence duration in milliseconds
        """
        if not self._silence_samples:
            return settings.VAD_SILENCE_MS_ACTIVE

        # Use 75th percentile of silence durations
        sorted_samples = sorted(self._silence_samples)
        percentile_index = int(len(sorted_samples) * 0.75)
        optimal = int(sorted_samples[percentile_index])

        # Clamp to reasonable range
        return max(200, min(optimal, 1000))

    def reset(self) -> None:
        """Reset VAD state (call when starting new conversation)."""
        self._interruption_count = 0
        self._silence_samples = []
        self._mode = "relaxed"
        logger.debug("Adaptive VAD reset")


class ConversationFlowTracker:
    """
    Track conversation flow to optimize VAD and prompts.

    Monitors:
    - Turn-taking patterns
    - User speaking rate
    - Conversation tempo
    """

    def __init__(self):
        self._turn_count = 0
        self._user_speech_durations = []
        self._bot_response_durations = []
        self._pause_durations = []
        self._start_time = None
        self._last_activity_time = None

    def start_conversation(self) -> None:
        """Start tracking a new conversation."""
        import time
        self._start_time = time.time()
        self._last_activity_time = time.time()
        self._turn_count = 0
        self._user_speech_durations = []
        self._bot_response_durations = []
        logger.debug("Conversation flow tracking started")

    def record_user_turn(self, speech_duration: float) -> None:
        """
        Record a user turn in the conversation.

        Args:
            speech_duration: Duration of user speech in seconds
        """
        import time
        now = time.time()

        if self._last_activity_time:
            pause = now - self._last_activity_time
            self._pause_durations.append(pause)

        self._user_speech_durations.append(speech_duration)
        self._turn_count += 1
        self._last_activity_time = now

    def record_bot_response(self, response_duration: float) -> None:
        """
        Record a bot response.

        Args:
            response_duration: Duration of bot response in seconds
        """
        import time
        self._bot_response_durations.append(response_duration)
        self._last_activity_time = time.time()

    def get_conversation_tempo(self) -> str:
        """
        Determine conversation tempo based on turn patterns.

        Returns:
            'fast', 'medium', or 'slow'
        """
        if not self._pause_durations:
            return "medium"

        avg_pause = sum(self._pause_durations) / len(self._pause_durations)

        if avg_pause < 1.0:
            return "fast"
        elif avg_pause < 2.5:
            return "medium"
        else:
            return "slow"

    def get_optimal_vad_mode(self) -> str:
        """
        Get optimal VAD mode based on conversation tempo.

        Returns:
            'active' for fast conversations, 'relaxed' for slow
        """
        tempo = self.get_conversation_tempo()
        return "active" if tempo == "fast" else "relaxed"

    @property
    def turn_count(self) -> int:
        """Get number of conversation turns."""
        return self._turn_count

    @property
    def duration(self) -> float:
        """Get total conversation duration in seconds."""
        if not self._start_time:
            return 0.0
        import time
        return time.time() - self._start_time

    def get_summary(self) -> dict:
        """Get conversation flow summary."""
        import time
        return {
            "turn_count": self._turn_count,
            "duration_seconds": round(self.duration, 2),
            "avg_user_speech": round(sum(self._user_speech_durations) / max(len(self._user_speech_durations), 1), 2),
            "avg_bot_response": round(sum(self._bot_response_durations) / max(len(self._bot_response_durations), 1), 2),
            "avg_pause": round(sum(self._pause_durations) / max(len(self._pause_durations), 1), 2),
            "tempo": self.get_conversation_tempo(),
        }


# Global instances
adaptive_vad = AdaptiveVAD()
conversation_tracker = ConversationFlowTracker()
