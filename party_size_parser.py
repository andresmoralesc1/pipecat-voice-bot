#
# Party Size Parser - Parse adults, children and babies
#
"""Parser para detectar y calcular correctamente el número de personas
incluyendo adultos, niños y bebés con trona."""
import re
from typing import Dict, Tuple, Optional
from loguru import logger


def parse_party_size(
    party_size_value,
    user_message: str = ""
) -> Tuple[int, str, Dict[str, int]]:
    """
    Parsea party_size detectando adultos, niños y bebés.

    Args:
        party_size_value: Valor de partySize (puede ser int, float o string)
        user_message: Mensaje original del usuario para contexto adicional

    Returns:
        Tuple[int, str, Dict]: (
            total_personas: int,
            observaciones: str,
            desglose: dict con 'adultos', 'ninos', 'bebes'
        )

    Examples:
        >>> parse_party_size(4)
        (4, '', {'adultos': 4, 'ninos': 0, 'bebes': 0})

        >>> parse_party_size("4 adultos 2 niños")
        (6, '', {'adultos': 4, 'ninos': 2, 'bebes': 0})

        >>> parse_party_size("4 personas y 1 bebé")
        (5, 'Necesitan trona para bebé', {'adultos': 4, 'ninos': 0, 'bebes': 1})
    """
    # Valores por defecto
    result = {
        'total': 0,
        'adultos': 0,
        'ninos': 0,
        'bebes': 0,
        'observaciones': ''
    }

    # Caso 1: Si ya es un número simple, retornar directamente
    if isinstance(party_size_value, (int, float)):
        total = int(party_size_value)
        result['total'] = total
        result['adultos'] = total
        return total, '', {'adultos': total, 'ninos': 0, 'bebes': 0}

    # Caso 2: Si es string, intentar parsear
    if isinstance(party_size_value, str):
        text_to_analyze = party_size_value.lower()
        # También incluir el user_message si está disponible
        if user_message:
            text_to_analyze += " " + user_message.lower()

        # Limpiar texto: normalizar tildes y espacios
        text_to_analyze = text_to_analyze.strip()
        text_to_analyze = re.sub(r'\s+', ' ', text_to_analyze)

        # Patrones de búsqueda
        # 1. Buscar "bebé", "bebe", "bebes", "bebés"
        bebe_pattern = r'\b(beb[éê]|bebe|bebes)\b'
        has_bebe = re.search(bebe_pattern, text_to_analyze, re.IGNORECASE)

        # 2. Extraer números asociados a adultos y niños
        adultos_match = re.search(r'(\d+)\s*(adultos?|adults?)', text_to_analyze)
        ninos_match = re.search(r'(\d+)\s*(niñ[oa]s?|infantes?|kids?|children?)', text_to_analyze)

        # 3. Extraer cualquier número mencionado (fallback)
        all_numbers = re.findall(r'\b(\d+)\b', text_to_analyze)

        # Calcular totales
        adultos = int(adultos_match.group(1)) if adultos_match else 0
        ninos = int(ninos_match.group(1)) if ninos_match else 0
        bebes = 1 if has_bebe else 0

        # Si no se detectaron adultos ni niños específicamente,
        # usar el número más grande mencionado como adultos
        if adultos == 0 and ninos == 0 and all_numbers:
            adultos = max([int(n) for n in all_numbers])

        # Si se menciona un número simple pero hay bebé, sumar
        if len(all_numbers) == 1 and bebes == 1 and adultos == 0:
            adultos = int(all_numbers[0])

        total = adultos + ninos + bebes

        # Generar observaciones si hay bebé
        observaciones = ''
        if bebes > 0:
            observaciones = 'Necesitan trona para bebé'

        result = {
            'total': total,
            'adultos': adultos,
            'ninos': ninos,
            'bebes': bebes,
            'observaciones': observaciones
        }

        logger.info(f"🔍 Party size parseado: {result}")
        return total, observaciones, {'adultos': adultos, 'ninos': ninos, 'bebes': bebes}

    # Caso fallback: retornar valor original
    logger.warning(f"⚠️ No se pudo parsear party_size: {party_size_value}")
    return int(party_size_value) if party_size_value else 1, '', {'adultos': 1, 'ninos': 0, 'bebes': 0}


def format_confirmation_message(desglose: Dict[str, int]) -> Optional[str]:
    """
    Genera mensaje de confirmación con desglose si es relevante.

    Args:
        desglose: Dict con 'adultos', 'ninos', 'bebes'

    Returns:
        str: Mensaje de confirmación o None si no es necesario

    Examples:
        >>> format_confirmation_message({'adultos': 4, 'ninos': 2, 'bebes': 0})
        'son 6 personas en total (4 adultos y 2 niños)'

        >>> format_confirmation_message({'adultos': 4, 'ninos': 0, 'bebes': 1})
        'son 5 personas en total (4 adultos y 1 bebé)'

        >>> format_confirmation_message({'adultos': 4, 'ninos': 0, 'bebes': 0})
        None
    """
    adultos = desglose.get('adultos', 0)
    ninos = desglose.get('ninos', 0)
    bebes = desglose.get('bebes', 0)
    total = adultos + ninos + bebes

    # Si es solo adultos, no confirmar desglose
    if ninos == 0 and bebes == 0:
        return None

    # Construir mensaje de desglose
    partes = []
    if adultos > 0:
        partes.append(f"{adultos} adulto{'s' if adultos > 1 else ''}")
    if ninos > 0:
        partes.append(f"{ninos} niño{'s' if ninos > 1 else ''}")
    if bebes > 0:
        partes.append(f"{bebes} bebé{'s' if bebes > 1 else ''}")

    desglose_str = " y ".join(partes)
    return f"son {total} personas en total ({desglose_str})"


def merge_special_requests(existing_requests: str, new_requests: str) -> str:
    """
    Combina observaciones existentes con nuevas de forma inteligente.

    Args:
        existing_requests: Observaciones ya existentes
        new_requests: Nuevas observaciones a agregar

    Returns:
        str: Observaciones combinadas
    """
    if not existing_requests:
        return new_requests
    if not new_requests:
        return existing_requests

    # Evitar duplicados
    if new_requests.lower() in existing_requests.lower():
        return existing_requests
    if existing_requests.lower() in new_requests.lower():
        return new_requests

    # Combinar con separador
    return f"{existing_requests}. {new_requests}"
