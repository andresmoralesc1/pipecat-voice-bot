#
# API Client with Retry Logic for Pipecat Voice Bot
# Robust HTTP client with exponential backoff and error handling
#
"""HTTP client with retry logic for reservations API."""
import asyncio
import aiohttp
from typing import Any, Callable
from loguru import logger
from config import settings
from metrics import metrics, track_api_call


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(self, message: str, status_code: int | None = None, response_data: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class APITimeoutError(APIError):
    """Exception raised when API request times out."""

    pass


class APIConnectionError(APIError):
    """Exception raised when API connection fails."""

    pass


async def call_reservations_api(
    action: str,
    params: dict,
    max_retries: int | None = None,
    timeout: int | None = None,
    validate_response: bool = True
) -> dict[str, Any]:
    """
    Make HTTP call to reservations API with retry logic and exponential backoff.

    Args:
        action: API action to perform (e.g., 'createReservation', 'checkAvailability')
        params: Parameters to send in the request body
        max_retries: Maximum number of retry attempts (defaults to settings.MAX_RETRIES)
        timeout: Request timeout in seconds (defaults to settings.API_TIMEOUT)
        validate_response: Whether to validate the response structure

    Returns:
        Dictionary with API response data

    Raises:
        APITimeoutError: If all retry attempts timeout
        APIConnectionError: If all retry attempts fail to connect
        APIError: For other API errors
    """
    if max_retries is None:
        max_retries = settings.MAX_RETRIES

    if timeout is None:
        timeout = settings.API_TIMEOUT

    base_timeout = aiohttp.ClientTimeout(total=timeout)
    last_error = None

    for attempt in range(max_retries):
        retry_count = attempt  # Track attempt number for metrics

        try:
            async with aiohttp.ClientSession(timeout=base_timeout) as session:
                request_payload = {
                    "action": action,
                    "params": params
                    }

                logger.debug(f"API call attempt {attempt + 1}/{max_retries}: {action}")

                # Prepare headers with authentication
                headers = {"Content-Type": "application/json"}
                if settings.VOICE_BRIDGE_API_KEY:
                    headers["X-Voice-Bridge-Key"] = settings.VOICE_BRIDGE_API_KEY

                async with session.post(
                    settings.RESERVATIONS_API_URL,
                    json=request_payload,
                    headers=headers
                ) as response:
                    # Handle successful response
                    if response.status == 200:
                        data = await response.json()

                        if validate_response:
                            # Validate response has expected structure
                            if not isinstance(data, dict):
                                logger.warning(f"API returned non-dict response: {type(data)}")
                                data = {"data": data}

                        metrics.api_call_made(f"reservations.{action}", 0, True, retry_count)
                        return data

                    # Handle server errors (5xx) - retry
                    elif response.status >= 500:
                        error_msg = f"Server error {response.status}"
                        logger.warning(f"{error_msg} on attempt {attempt + 1}/{max_retries}")
                        last_error = APIError(
                            error_msg,
                            status_code=response.status,
                            response_data=await response.json() if response.content_length else None
                        )

                        # Retry for server errors with exponential backoff
                        if attempt < max_retries - 1:
                            await asyncio.sleep(_calculate_backoff(attempt))
                            continue

                    # Handle client errors (4xx) - don't retry
                    elif response.status >= 400:
                        error_data = await response.json() if response.content_length else {}
                        error_msg = error_data.get("voiceMessage") or error_data.get("message") or f"Client error {response.status}"
                        logger.error(f"Client error {response.status}: {error_msg}")
                        metrics.api_call_made(f"reservations.{action}", 0, False, retry_count)
                        return {
                            "success": False,
                            "voiceMessage": error_msg,
                            "statusCode": response.status
                            }

        except asyncio.TimeoutError as e:
            logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries}")
            last_error = APITimeoutError(
                "El servidor tardó demasiado en responder",
                status_code=None
            )

            # Retry for timeouts
            if attempt < max_retries - 1:
                await asyncio.sleep(_calculate_backoff(attempt))
                continue

        except aiohttp.ClientConnectionError as e:
            logger.warning(f"Connection error on attempt {attempt + 1}/{max_retries}: {e}")
            last_error = APIConnectionError(f"Error de conexión: {e}")

            # Retry for connection errors
            if attempt < max_retries - 1:
                await asyncio.sleep(_calculate_backoff(attempt))
                continue

        except aiohttp.ClientError as e:
            logger.error(f"Unexpected client error on attempt {attempt + 1}: {e}")
            last_error = APIError(f"Error del cliente HTTP: {e}")

            # Don't retry on unexpected client errors
            break

        except Exception as e:
            logger.error(f"Unexpected error calling API on attempt {attempt + 1}: {e}")
            last_error = APIError(f"Error inesperado: {e}")

            # Don't retry on unexpected errors
            break

    # All retries exhausted
    metrics.api_call_made(f"reservations.{action}", 0, False, max_retries - 1)

    # Return user-friendly error message
    if isinstance(last_error, APITimeoutError):
        return {
            "success": False,
            "voiceMessage": "Tardó mucho en responder. Por favor, intenta de nuevo en unos momentos."
            }
    elif isinstance(last_error, APIConnectionError):
        return {
            "success": False,
            "voiceMessage": "No puedo conectar con el servidor de reservas. Por favor, verifica tu conexión o intenta más tarde."
            }
    else:
        return {
            "success": False,
            "voiceMessage": "Lo siento, estoy teniendo problemas para procesar tu solicitud. Por favor, intenta de nuevo."
            }


def _calculate_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 10.0) -> float:
    """
    Calculate exponential backoff delay for retries.

    Args:
        attempt: Current retry attempt (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Delay in seconds
    """
    # Exponential backoff: base_delay * (2 ^ attempt), capped at max_delay
    delay = min(base_delay * (2 ** attempt), max_delay)
    return delay


async def check_availability_with_cache(
    date: str,
    time: str,
    party_size: int,
    cache_ttl: int | None = None
) -> dict[str, Any]:
    """
    Check availability with simple in-memory caching.

    Args:
        date: Date in YYYY-MM-DD format
        time: Time in HH:MM format
        party_size: Number of people
        cache_ttl: Cache TTL in seconds (defaults to settings.CACHE_TTL_SECONDS)

    Returns:
        Availability response from API
    """
    if cache_ttl is None:
        cache_ttl = settings.CACHE_TTL_SECONDS

    # Simple in-memory cache (for production, use Redis or similar)
    cache_key = f"availability:{date}:{time}:{party_size}"

    # Check cache
    if hasattr(check_availability_with_cache, "_cache"):
        cached_entry = check_availability_with_cache._cache.get(cache_key)
        if cached_entry:
            import time
            if time.time() - cached_entry["timestamp"] < cache_ttl:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_entry["data"]
    else:
        check_availability_with_cache._cache = {}

    # Call API
    result = await call_reservations_api(
        "checkAvailability",
        {"date": date, "time": time, "partySize": party_size}
    )

    # Only cache successful results
    if result.get("success", False):
        check_availability_with_cache._cache[cache_key] = {
            "data": result,
            "timestamp": __import__("time").time()
        }

    # Clean old cache entries periodically
    if len(check_availability_with_cache._cache) > 1000:
        current_time = __import__("time").time()
        check_availability_with_cache._cache = {
            k: v for k, v in check_availability_with_cache._cache.items()
            if current_time - v["timestamp"] < cache_ttl
            }

    return result


async def validate_and_create_reservation(params: dict) -> tuple[bool, dict, list[str]]:
    """
    Validate reservation parameters and create reservation.

    Args:
        params: Reservation parameters

    Returns:
        Tuple of (success, response_data, errors)
    """
    from validators import validate_reservation_params

    is_valid, errors = validate_reservation_params(
        customer_name=params.get("customer_name", ""),
        customer_phone=params.get("customer_phone", ""),
        restaurant_id=params.get("restaurant_id", ""),
        reservation_date=params.get("reservation_date", ""),
        reservation_time=params.get("reservation_time", ""),
        party_size=params.get("party_size", 1),
        special_requests=params.get("special_requests"),
        available_restaurants=settings.restaurant_ids
    )

    if not is_valid:
        return False, {"voiceMessage": "Por favor, corrige los siguientes errores: " + "; ".join(errors)}, errors

    # Create reservation
    result = await call_reservations_api("createReservation", params)

    return result.get("success", False), result, []
