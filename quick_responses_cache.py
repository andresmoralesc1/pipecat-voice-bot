#
# Quick Responses Cache System
# Pre-generated responses for common interactions to reduce LLM latency
#
from typing import Optional, Dict
from loguru import logger
import random

class QuickResponsesCache:
    """
    Cache system for pre-generated common responses.
    This dramatically reduces latency for frequent interactions.
    """

    def __init__(self):
        """Initialize the quick responses cache."""
        self.greetings = [
            "Hola, soy Marta, tu asistente para reservas. Tus datos solo se usan para gestionar la reserva. ¿A quién tengo el gusto de atender?",
            "Hola, soy Marta, tu asistente para reservas. Tus datos solo se usan para gestionar la reserva. ¿A quién tengo el gusto de atender?",
            "Hola, soy Marta, tu asistente para reservas. Tus datos solo se usan para gestionar la reserva. ¿A quién tengo el gusto de atender?",
        ]

        self.name_responses = [
            "¡Perfecto, {name}! ¿Para qué día y hora te gustaría hacer la reserva?",
            "¡Genial, {name}! ¿Qué día y a qué hora necesitas la mesa?",
            "¡Excelente, {name}! ¿Para qué día y hora es la reserva?",
        ]

        self.confirmation_responses = [
            "Perfecto, te he entendido. Un segundo...",
            "¡De acuerdo! Déjame verificar...",
            "Perfecto, un momento...",
        ]

        self.availability_check = [
            "Un segundo, voy a comprobar la disponibilidad...",
            "Déjame verificar disponibilidad...",
            "Voy a comprobar si hay mesa disponible...",
        ]

        self.thank_you = [
            "¿Algo más en lo que pueda ayudarte?",
            "¿Necesitas algo más?",
            "¿Te puedo ayudar con algo más?",
        ]

        logger.info("✅ Quick Responses Cache initialized")

    def get_greeting(self) -> str:
        """Get a random greeting message."""
        return random.choice(self.greetings)

    def get_name_response(self, name: str) -> str:
        """Get a response when user provides their name."""
        template = random.choice(self.name_responses)
        return template.format(name=name)

    def get_confirmation(self) -> str:
        """Get a confirmation message."""
        return random.choice(self.confirmation_responses)

    def get_availability_check(self) -> str:
        """Get availability check message."""
        return random.choice(self.availability_check)

    def get_thank_you(self) -> str:
        """Get thank you/closing message."""
        return random.choice(self.thank_you)

    def detect_quick_response(self, user_input: str, context: Dict) -> Optional[str]:
        """
        Detect if user input can use a quick cached response.

        Args:
            user_input: User's text input
            context: Conversation context

        Returns:
            Cached response if available, None otherwise
        """
        user_input_lower = user_input.lower().strip()

        # Greeting patterns
        if any(word in user_input_lower for word in ['hola', 'buenas', 'buenas tardes', 'hey']):
            if not context.get('name_provided', False):
                return self.get_greeting()

        # Name patterns (simple detection)
        if context.get('expecting_name', False):
            # If we just asked for name and got a short response, assume it's a name
            if len(user_input_lower) < 30 and not any(word in user_input_lower for word in ['para', 'hora', 'dia', 'mesa', 'personas']):
                name = user_input.strip()
                context['name_provided'] = True
                context['customer_name'] = name
                return self.get_name_response(name)

        return None


# Global instance
_quick_cache: Optional[QuickResponsesCache] = None

def get_quick_cache() -> QuickResponsesCache:
    """Get or create global quick cache instance."""
    global _quick_cache
    if _quick_cache is None:
        _quick_cache = QuickResponsesCache()
        logger.info("✅ Quick Cache instance created")
    return _quick_cache
