"""Filtro de texto personalizado para español/catalán.

Este módulo proporciona un filtro de texto que normaliza nombres propios
españoles/catalanes y números en el contexto del bot de voz Pipecat.
"""

import re
from typing import Any, Mapping
from pipecat.utils.text.base_text_filter import BaseTextFilter


class SpanishTextFilter(BaseTextFilter):
    """Filtro de texto para normalizar español/catalán.
    
    Proporciona normalización de:
    - Nombres propios españoles/catalanes (Montserrat, Jordi, Núria, etc.)
    - Números escritos en formato verbal (seis uno dos → 612)
    - Tildes y caracteres especiales
    """
    
    # Lista de nombres comunes españoles/catalanes que deben ir con mayúscula
    SPANISH_NAMES = {
        "maría", "montserrat", "jordi", "núria", "jose", "carmen", 
        "francisco", "pilar", "teresa", "javier", "raquel", "david",
        "ana", "mar", "merci", "xavier", "joan", "lluis", "marta",
        "albert", "carles", "pol", "ona", "laia", "julia", "sofia",
        "emma", "leo", "lucas", "hugo", "martín", "daniel", "pablo",
        "alejandro", "adrián", "álvaro", "diego", "nicolás", "rafael"
    }
    
    # Número palabras a dígitos
    NUMBER_WORDS = {
        "cero": "0", "uno": "1", "una": "1", "dos": "2", "tres": "3", 
        "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7", "ocho": "8",
        "nueve": "9"
    }
    
    def __init__(self, **kwargs):
        """Inicializa el filtro de texto español."""
        super().__init__(**kwargs)
        self._interrupted = False
    
    async def filter(self, text: str) -> str:
        """Aplica filtrado de texto español.
        
        Args:
            text: Texto de entrada del STT
            
        Returns:
            Texto filtrado con nombres capitalizados y números normalizados
        """
        if not text or self._interrupted:
            return text
        
        filtered_text = text
        
        # 1. Normalizar nombres propios
        filtered_text = self._capitalize_names(filtered_text)
        
        # 2. Normalizar números (seis uno dos → 612)
        filtered_text = self._normalize_numbers(filtered_text)
        
        return filtered_text
    
    def _capitalize_names(self, text: str) -> str:
        """Capitaliza nombres propios españoles/catalanes."""
        words = text.split()
        for i, word in enumerate(words):
            # Limpiar puntuación
            clean_word = word.lower().strip(".,!?;:")
            if clean_word in self.SPANISH_NAMES:
                # Capitalizar preservando acentos
                words[i] = word.replace(clean_word, clean_word.capitalize())
        
        return " ".join(words)
    
    def _normalize_numbers(self, text: str) -> str:
        """Normaliza números escritos en formato verbal.
        
        Convierte expresiones como "seis uno dos" → "612"
        """
        # Buscar secuencias de palabras numéricas
        words = text.split()
        normalized_words = []
        i = 0
        
        while i < len(words):
            word = words[i].lower().strip(".,!?;:")
            
            # Si es una palabra numérica, convertirla
            if word in self.NUMBER_WORDS:
                num_sequence = self.NUMBER_WORDS[word]
                i += 1
                
                # Buscar más palabras numéricas consecutivas
                while i < len(words):
                    next_word = words[i].lower().strip(".,!?;:")
                    if next_word in self.NUMBER_WORDS:
                        num_sequence += self.NUMBER_WORDS[next_word]
                        i += 1
                    else:
                        break
                
                # Si tenemos más de un dígito, es una secuencia válida
                if len(num_sequence) >= 2:
                    normalized_words.append(num_sequence)
                else:
                    normalized_words.append(words[i-1])
            else:
                normalized_words.append(words[i])
                i += 1
        
        return " ".join(normalized_words)
    
    async def update_settings(self, settings: Mapping[str, Any]):
        """Actualiza configuración del filtro."""
        pass
    
    async def handle_interruption(self):
        """Maneja interrupciones en el pipeline."""
        self._interrupted = True
    
    async def reset_interruption(self):
        """Resetea estado después de interrupción."""
        self._interrupted = False
