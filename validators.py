#
# Input Validators for Pipecat Voice Bot
# Validation for phone numbers, dates, times, and other user inputs
#
"""Input validation functions for voice bot parameters."""
import re
from datetime import datetime, timedelta
from typing import Literal


def validate_phone(phone: str, country: Literal["es", "ad", "fr"] = "es") -> tuple[bool, str | None]:
    """
    Validate phone number format based on country.

    Args:
        phone: Phone number string to validate
        country: Country code for validation (default: Spain)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return False, "El número de teléfono es obligatorio"

    # Remove common separators
    cleaned = re.sub(r"[\s\-\.\(\)]", "", phone)

    patterns = {
        "es": r"^(\+34|0034)?[67]\d{8}$",           # Spain: 6 or 7 followed by 8 digits
        "ad": r"^(\+376|00376)?[346]\d{5}$",        # Andorra
        "fr": r"^(\+33|0033)?[67]\d{8}$",           # France
    }

    pattern = patterns.get(country, patterns["es"])
    if not re.match(pattern, cleaned):
        return False, f"Formato de teléfono inválido. Para España, usa: 6XX XXX XXX o +34 6XX XXX XXX"

    return True, None


def validate_date(date_str: str) -> tuple[bool, str | None, datetime | None]:
    """
    Validate date format and ensure it's a future date.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Tuple of (is_valid, error_message, parsed_date)
    """
    if not date_str:
        return False, "La fecha es obligatoria", None

    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if date < today:
            return False, "La fecha debe ser hoy o en el futuro", None

        # Check if date is too far in the future (more than 1 year)
        if date > today + timedelta(days=365):
            return False, "La fecha no puede ser más de un año en el futuro", None

        return True, None, date

    except ValueError as e:
        if "does not match format" in str(e):
            return False, "Formato de fecha inválido. Usa el formato: AAAA-MM-DD (ejemplo: 2025-12-31)", None
        return False, f"Fecha inválida: {e}", None


def validate_time(time_str: str) -> tuple[bool, str | None, str | None]:
    """
    Validate time format and business hours.

    Args:
        time_str: Time string in HH:MM format

    Returns:
        Tuple of (is_valid, error_message, normalized_time)
    """
    if not time_str:
        return False, "La hora es obligatoria", None

    try:
        time = datetime.strptime(time_str, "%H:%M")
        hour = time.hour
        minute = time.minute

        # Validate business hours (13:00 - 16:00 lunch, 20:00 - 23:30 dinner)
        valid_periods = [
            (13, 0, 16, 0),   # Lunch: 13:00 - 16:00
            (20, 0, 23, 30),  # Dinner: 20:00 - 23:30
        ]

        is_valid_time = False
        for start_h, start_m, end_h, end_m in valid_periods:
            start_time = start_h * 60 + start_m
            end_time = end_h * 60 + end_m
            current_time = hour * 60 + minute
            if start_time <= current_time <= end_time:
                is_valid_time = True
                break

        if not is_valid_time:
            return False, "Horario fuera de servicio. Abierto 13:00-16:00 y 20:00-23:30", None

        return True, None, time_str

    except ValueError:
        return False, "Formato de hora inválido. Usa el formato: HH:MM (ejemplo: 14:30)", None


def validate_party_size(size: int) -> tuple[bool, str | None]:
    """
    Validate party size for reservation.

    Args:
        size: Number of people

    Returns:
        Tuple of (is_valid, error_message)
    """
    if size < 1:
        return False, "El número de personas debe ser al menos 1"

    if size > 20:
        return False, "Para grupos de más de 20 personas, por favor contáctanos por teléfono"

    if size > 12:
        return True, "Nota: Para grupos grandes, podemos requerir confirmación adicional", None

    return True, None


def validate_reservation_datetime(date_str: str, time_str: str) -> tuple[bool, str | None]:
    """
    Validate that the reservation datetime is in the future.

    Args:
        date_str: Date string in YYYY-MM-DD format
        time_str: Time string in HH:MM format

    Returns:
        Tuple of (is_valid, error_message)
    """
    date_valid, date_error, date_obj = validate_date(date_str)
    if not date_valid:
        return False, date_error

    time_valid, time_error, _ = validate_time(time_str)
    if not time_valid:
        return False, time_error

    try:
        time_obj = datetime.strptime(time_str, "%H:%M")
        reservation_datetime = datetime.combine(date_obj, time_obj.time())

        # Check if reservation is at least 30 minutes in the future
        min_reservation_time = datetime.now() + timedelta(minutes=30)

        if reservation_datetime < min_reservation_time:
            return False, "Las reservas deben hacerse con al menos 30 minutos de antelación"

        return True, None

    except ValueError as e:
        return False, f"Error al validar fecha y hora: {e}"


def validate_reservation_code(code: str) -> tuple[bool, str | None]:
    """
    Validate reservation code format.

    Args:
        code: Reservation code string

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not code:
        return False, "El código de reserva es obligatorio"

    # Common formats: RES-12345, 12345, ABC-12345
    pattern = r"^(RES\-)?[A-Z0-9]{5,10}$"

    if not re.match(pattern, code.upper()):
        return False, "Formato de código inválido. Formato esperado: RES-12345 o similar"

    return True, None


def validate_restaurant_id(restaurant_id: str, available_restaurants: list[str]) -> tuple[bool, str | None]:
    """
    Validate restaurant ID against available locations.

    Args:
        restaurant_id: Restaurant ID to validate
        available_restaurants: List of valid restaurant IDs

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not restaurant_id:
        return False, "Debes seleccionar un restaurante"

    restaurant_id_clean = restaurant_id.lower().strip()

    if restaurant_id_clean not in available_restaurants:
        return False, f"Restaurante no válido. Opciones disponibles: {', '.join(available_restaurants)}"

    return True, None


def validate_customer_name(name: str) -> tuple[bool, str | None]:
    """
    Validate customer name.

    Args:
        name: Customer name string

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "El nombre es obligatorio"

    name_clean = name.strip()

    if len(name_clean) < 2:
        return False, "El nombre debe tener al menos 2 caracteres"

    if len(name_clean) > 100:
        return False, "El nombre es demasiado largo"

    # Allow letters, spaces, hyphens, and apostrophes (common in Spanish/Catalan names)
    if not re.match(r"^[a-zA-ZáéíóúàèìòùâêîôûäëïöüñçÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÄËÏÖÜÑÇ\s\-'\.]+$", name_clean):
        return False, "El nombre contiene caracteres inválidos"

    return True, None


def sanitize_special_requests(requests: str | None) -> str:
    """
    Sanitize special requests input.

    Args:
        requests: Special requests string

    Returns:
        Sanitized string (max 500 chars, stripped)
    """
    if not requests:
        return ""

    cleaned = requests.strip()[:500]
    # Remove any potential script tags or dangerous patterns
    cleaned = re.sub(r"<script.*?>.*?</script>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    return cleaned


def validate_reservation_params(
    customer_name: str,
    customer_phone: str,
    restaurant_id: str,
    reservation_date: str,
    reservation_time: str,
    party_size: int,
    special_requests: str | None = None,
    available_restaurants: list[str] | None = None
) -> tuple[bool, list[str]]:
    """
    Validate all reservation parameters.

    Args:
        customer_name: Customer name
        customer_phone: Customer phone number
        restaurant_id: Restaurant location ID
        reservation_date: Date in YYYY-MM-DD format
        reservation_time: Time in HH:MM format
        party_size: Number of people
        special_requests: Optional special requests
        available_restaurants: List of valid restaurant IDs

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    validations = [
        (validate_customer_name(customer_name), "customer_name"),
        (validate_phone(customer_phone), "customer_phone"),
        (validate_reservation_datetime(reservation_date, reservation_time), "datetime"),
        (validate_party_size(party_size), "party_size"),
    ]

    # Solo validar restaurant_id si se proporcionan available_restaurants
    # Si es None, el backend usa el restaurante por defecto automáticamente
    if available_restaurants is not None:
        validations.append(
            (validate_restaurant_id(restaurant_id, available_restaurants), "restaurant_id")
        )

    for (is_valid, error), field in validations:
        if not is_valid:
            errors.append(f"{field}: {error}")

    is_valid = len(errors) == 0

    return is_valid, errors
