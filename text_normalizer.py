"""Normalizador de texto para español/catalán.

Este módulo proporciona funciones para normalizar texto del STT,
incluyendo capitalización de nombres y normalización de números.
"""

import re
from typing import Optional


# Lista de nombres comunes españoles/catalanes
SPANISH_NAMES = {
    "maría", "montserrat", "jordi", "núria", "jose", "carmen", 
    "francisco", "pilar", "teresa", "javier", "raquel", "david",
    "ana", "mar", "merci", "xavier", "joan", "lluis", "marta",
    "albert", "carles", "pol", "ona", "laia", "julia", "sofia",
    "emma", "leo", "lucas", "hugo", "martín", "daniel", "pablo",
    "alejandro", "adrián", "álvaro", "diego", "nicolás", "rafael",
    "carla", "sara", "marina", "claudia", "noa", "iaia", "jana",
    "biel", "pau", "jan", "nil", "roger", "marc", "arnau"
}

# Número palabras a dígitos
NUMBER_WORDS = {
    "cero": "0", "uno": "1", "una": "1", "dos": "2", "tres": "3", 
    "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7", "ocho": "8",
    "nueve": "9"
}


def normalize_text(text: Optional[str]) -> str:
    """Normaliza texto del STT.
    
    Args:
        text: Texto de entrada del STT
        
    Returns:
        Texto normalizado con nombres capitalizados y números normalizados
    """
    if not text:
        return ""
    
    normalized = text
    
    # 1. Normalizar nombres propios
    normalized = _capitalize_names(normalized)
    
    # 2. Normalizar números (seis uno dos → 612)
    normalized = _normalize_numbers(normalized)
    
    return normalized


def _capitalize_names(text: str) -> str:
    """Capitaliza nombres propios españoles/catalanes."""
    words = text.split()
    for i, word in enumerate(words):
        # Limpiar puntuación
        clean_word = word.lower().strip(".,!?;:")
        if clean_word in SPANISH_NAMES:
            # Capitalizar preservando estructura
            if word[0].islower():
                # Reemplazar manteniendo puntuación
                punct = word[len(clean_word):]
                words[i] = clean_word.capitalize() + punct
    return " ".join(words)


def _normalize_numbers(text: str) -> str:
    """Normaliza números escritos en formato verbal.
    
    Convierte expresiones como "seis uno dos" → "612"
    Solo convierte secuencias de 2+ dígitos para evitar falsos positivos.
    """
    words = text.split()
    result = []
    i = 0
    
    while i < len(words):
        word = words[i].lower().strip(".,!?;:")
        
        if word in NUMBER_WORDS:
            num_sequence = NUMBER_WORDS[word]
            i += 1
            
            # Buscar más palabras numéricas consecutivas
            while i < len(words):
                next_word = words[i].lower().strip(".,!?;:")
                if next_word in NUMBER_WORDS:
                    num_sequence += NUMBER_WORDS[next_word]
                    i += 1
                else:
                    break
            
            # Solo convertir si tenemos 2+ dígitos (teléfono, código, etc.)
            if len(num_sequence) >= 2:
                result.append(num_sequence)
            else:
                result.append(words[i-1])
        else:
            result.append(words[i])
            i += 1
    
    return " ".join(result)


def normalize_customer_name(name: Optional[str]) -> str:
    """Normaliza específicamente nombres de clientes.
    
    Args:
        name: Nombre del cliente del STT
        
    Returns:
        Nombre con mayúsculas correctas
    """
    if not name:
        return ""
    
    # Capitalizar cada palabra
    words = name.split()
    normalized = []
    
    for word in words:
        clean = word.lower().strip(".,!?;:")
        # Si es un nombre conocido, capitalizar correctamente
        if clean in SPANISH_NAMES:
            normalized.append(clean.capitalize())
        else:
            # Capitalizar primera letra
            normalized.append(word.capitalize())
    
    return " ".join(normalized)
