def clean_tts_text(t):
    """
    Clean text before sending to TTS to avoid pronunciation issues.
    Fixes Cartesia errors when text starts with inverted punctuation.
    """
    # PRIMERO: Eliminar signos de exclamación/interrogación invertidos AL INICIO
    # Esto es crítico para Cartesia TTS que rechaza texto que empieza con "¡" o "¿"
    while t.startswith(("¡", "¿")):
        t = t[1:].lstrip()  # Eliminar primer carácter y espacios

    # SEGUNDO: Eliminar caracteres de formato markdown que el TTS no debe pronunciar
    t = t.replace("**", "").replace("__", "").replace("##", "").replace("##", "")
    t = t.replace("*", "").replace("_", "").replace("#", "")

    # TERCERO: Eliminar signos de exclamación/interrogación invertidos en todo el texto
    # (los normales "!" y "?" se mantienen para la entonación correcta)
    t = t.replace("¡", "").replace("¿", "")

    # CUARTO: Expandir códigos de reserva a pronunciación en español
    import re

    def expandir_codigo_reserva(match):
        codigo = match.group(0)  # Ej: RES-WDI77
        letras = codigo.split('-')[1]  # Ej: WDI77

        # Convertir letras a pronunciación española
        pronunciacion = []
        for letra in letras:
            if letra == 'W': pronunciacion.append('uve doble')
            elif letra == 'w': pronunciacion.append('uve doble')
            elif letra == 'Y': pronunciacion.append('i griega')
            elif letra == 'y': pronunciacion.append('i griega')
            elif letra.isdigit():
                pronunciacion.append(letra)
            else:
                pronunciacion.append(letra)

        return f"RES, guion, {', '.join(pronunciacion)}"

    # Buscar y reemplazar códigos RES-XXXXX
    t = re.sub(r'RES-[A-Z0-9]{5}', expandir_codigo_reserva, t)

    # NUEVO: Expandir códigos de reserva formato NOMBRE-XXXX (ej: ALEJANDRO-7708 o DANIEL7708)
    def expandir_codigo_nombre_con_guion(match):
        """Expandir código con guion: ALEJANDRO-7708 → ALEJANDRO 7 7 0 8"""
        codigo = match.group(0)
        partes = codigo.split('-')
        nombre = partes[0]
        digitos = partes[1]
        digitos_separados = ' '.join(digitos)
        return f"{nombre} {digitos_separados}"

    def expandir_codigo_nombre_sin_guion(match):
        """Expandir código sin guion: DANIEL7708 → DANIEL 7 7 0 8"""
        codigo = match.group(0)
        # Separar letras de números: buscar el punto donde empiezan los números
        import re as re2
        match_sep = re2.search(r'(\D+)(\d{4})$', codigo)
        if match_sep:
            nombre = match_sep.group(1)
            digitos = match_sep.group(2)
            digitos_separados = ' '.join(digitos)
            return f"{nombre} {digitos_separados}"
        return codigo

    # Buscar y reemplazar códigos CON guion (NOMBRE-XXXX)
    t = re.sub(r'[A-ZÁÉÍÓÚÑ]{2,}-\d{4}', expandir_codigo_nombre_con_guion, t)

    # Buscar y reemplazar códigos SIN guion (NOMBREXXXX) - patrón: 4+ letras mayúsculas seguidas de 4 dígitos
    # IMPORTANTE: Esto debe ir después del con guion para no reemplazar dos veces
    t = re.sub(r'\b[A-ZÁÉÍÓÚÑ]{4,}\d{4}\b', expandir_codigo_nombre_sin_guion, t)

    # QUINTO: Corregir comas seguidas de números (caso más común)
    t = t.replace(",15", ", 15").replace(",16", ", 16").replace(",17", ", 17").replace(",18", ", 18")
    t = t.replace(",19", ", 19").replace(",20", ", 20").replace(",21", ", 21").replace(",22", ", 22")
    t = t.replace(",23", ", 23").replace(",24", ", 24").replace(",25", ", 25").replace(",30", ", 30")
    t = t.replace(",13", ", 13").replace(",14", ", 14")

    # SEXTO: Corregir espacios faltantes entre números y texto
    t = t.replace("es6", "es 6").replace("es9", "es 9")
    t = t.replace("el1", "el 1").replace("el2", "el 2").replace("el3", "el 3")
    t = t.replace("las1", "las 1").replace("las2", "las 2").replace("las3", "las 3")
    t = t.replace("a las1", "a las 1").replace("a las2", "a las 2")
    t = t.replace("para1", "para 1").replace("para2", "para 2").replace("para3", "para 3")
    t = t.replace("para4", "para 4").replace("para5", "para 5").replace("para6", "para 6")

    # Corregir "a las" seguido de hora (20-23)
    t = t.replace("a las20", "a las 20").replace("a las21", "a las 21")
    t = t.replace("a las22", "a las 22").replace("a las23", "a las 23")
    t = t.replace("a las14", "a las 14").replace("a las15", "a las 15")

    # Corregir otros casos
    t = t.replace("de2026", "de 2026")

    return t.strip()  # Eliminar espacios extra al inicio y final
