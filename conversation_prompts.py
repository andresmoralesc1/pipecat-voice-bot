# Conversation Prompts and Language Detection for Pipecat Voice Bot
# Contextual prompts based on conversation state and language detection
#
"""Contextual conversation prompts and language detection."""
import re
from typing import Literal, Optional
from loguru import logger
from config import settings, conversation_state, ConversationState


class LanguageDetector:
    """
    Detect user language (Spanish or Catalan) from text input.

    Features:
    - Basic keyword detection for Spanish/Catalan
    - Fallback to configured default language
    - State tracking per conversation
    """

    # Common words/phrases for language detection
    CATALAN_KEYWORDS = {
        # Greetings
        "hola", "bon dia", "bona tarda", "bon vespre", "adéu", "fins aviat",
        # Common words
        "gràcies", "si us plau", "per favor", "sí", "no", "bé", "bé",
        # Restaurant specific
        "voldria", "vull", "tinc", "vull fer", "una taula", "reservar",
        # Numbers
        "un", "una", "dos", "tres", "quatre", "cinc", "sis", "set", "vuit", "nou", "deu",
        # Time
        "avui", "demà", "dilluns", "dimarts", "dimecres", "dijous", "divendres", "dissabte", "diumenge",
        # Questions
        "què", "com", "quan", "on", "per què", "quant",
    }

    SPANISH_KEYWORDS = {
        # Greetings
        "hola", "buenos días", "buenas tardes", "buenas noches", "adiós", "hasta luego",
        # Common words
        "gracias", "por favor", "sí", "no", "bien", "bueno",
        # Restaurant specific
        "querría", "quiero", "tengo", "quisiera", "una mesa", "reservar",
        # Numbers
        "uno", "una", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez",
        # Time
        "hoy", "mañana", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo",
        # Questions
        "qué", "cómo", "cuándo", "dónde", "por qué", "cuánto",
    }

    @classmethod
    def detect(cls, text: str, default: str = "es") -> str:
        """
        Detect language from text input.

        Args:
            text: User input text
            default: Default language if detection fails

        Returns:
            'ca' for Catalan, 'es' for Spanish
        """
        if not text:
            return default

        text_lower = text.lower()

        # Count Catalan keywords
        catalan_count = sum(1 for word in cls.CATALAN_KEYWORDS if word in text_lower)

        # Count Spanish keywords (excluding overlaps)
        spanish_count = sum(1 for word in cls.SPANISH_KEYWORDS if word in text_lower and word not in cls.CATALAN_KEYWORDS)

        # Specific Catalan patterns
        catalan_patterns = [
            r"\b(vull|voldria|tinc|haig)\b",  # Verbs
            r"\b(gràcies|si us plau)\b",  # Politeness
            r"ç",  # Cedilla (Catalan)
        ]

        for pattern in catalan_patterns:
            if re.search(pattern, text_lower):
                catalan_count += 2  # Weight patterns more heavily

        # Decision based on counts
        if catalan_count > spanish_count:
            return "ca"
        elif spanish_count > catalan_count:
            return "es"

        return default

    @classmethod
    def detect_and_update_state(cls, text: str) -> str:
        """
        Detect language and update conversation state.

        Args:
            text: User input text

        Returns:
            Detected language code
        """
        detected = cls.detect(text, settings.DEFAULT_LANGUAGE)
        conversation_state.language = detected
        logger.debug(f"Language detected: {detected}")
        return detected


class ConversationPrompts:
    """
    Contextual prompts based on conversation state.

    Provides:
    - State-specific prompts
    - Multilingual support (Spanish/Catalan)
    - Dynamic prompt generation
    """

    PROMPTS = {
        "greeting": {
            "es": {
                "prompt": "Hola, soy Marta, tu asistente para reservas. Tus datos solo se usan para gestionar la reserva. ¿A quién tengo el gusto de atender?",
                "vad_mode": "relaxed",
            },
            "ca": {
                "prompt": "Hola! Sóc Anfitrió, el vostre assistent per a reserves. Abans de començar, us comento que les vostres dades s'utilitzaran únicament per gestionar la reserva. Amb qui tinc el gust de parlar?",
                "vad_mode": "relaxed",
            },
        },
        "asking_name": {
            "es": {
                "prompt": "¿Me decís vuestro nombre, por favor?",
                "vad_mode": "active",
            },
            "ca": {
                "prompt": "Em dieu el vostre nom, si us plau?",
                "vad_mode": "active",
            },
        },
        "capturing_date": {
            "es": {
                "prompt": "¡Estupendo, {name}! ¿Para qué día os gustaría reservar?",
                "vad_mode": "active",
            },
            "ca": {
                "prompt": "Fantàstic, {name}! Per a quin dia us agradaria reservar?",
                "vad_mode": "active",
            },
        },
        "capturing_time": {
            "es": {
                "prompt": "Perfecto. ¿Y a qué hora os vendría bien?",
                "vad_mode": "active",
            },
            "ca": {
                "prompt": "Perfecte. I a quina hora us aniria bé?",
                "vad_mode": "active",
            },
        },
        "capturing_party_size": {
            "es": {
                "prompt": "Genial. ¿Para cuántas personas sería, {name}?",
                "vad_mode": "active",
            },
            "ca": {
                "prompt": "Genial. Per a quantes persones seria, {name}?",
                "vad_mode": "active",
            },
        },
        "asking_phone": {
            "es": {
                "prompt": "Perfecto. ¿Me dais un número de teléfono para la confirmación?",
                "vad_mode": "active",
            },
            "ca": {
                "prompt": "Perfecte. Em doneu un número de telèfon per a la confirmació?",
                "vad_mode": "active",
            },
        },
        "asking_special_requests": {
            "es": {
                "prompt": "¿Tenéis alguna petición especial? Por ejemplo: terraza, trona, silla de ruedas, alergias o si celebráis algo especial. Si no, decidme 'no' y seguimos.",
                "vad_mode": "relaxed",
            },
            "ca": {
                "prompt": "Teniu alguna petició especial? Per exemple: terrassa, trona, cadira de rodes, al·lèrgies o si celebreu alguna cosa especial. Si no, digueu-me 'no' i continuem.",
                "vad_mode": "relaxed",
            },
        },
        "confirming": {
            "es": {
                "prompt": "Perfecto, {name}. Os resumo: mesa para {party_size} personas el {date} a las {time}. ¿Está todo correcto?",
                "vad_mode": "active",
            },
            "ca": {
                "prompt": "Perfecte, {name}. Us resumeixo: taula per a {party_size} persones el {date} a les {time}. Està tot correcte?",
                "vad_mode": "active",
            },
        },
        "completed": {
            "es": {
                "prompt": "¡Contad con ello, {name}! Vuestra reserva está confirmada. Os hemos enviado los detalles por mensaje. Recordad que podéis llamar de nuevo si necesitáis cancelar o modificar algo. ¡Nos vemos!",
                "vad_mode": "relaxed",
            },
            "ca": {
                "prompt": "Compteu-hi, {name}! La vostra reserva està confirmada. Us hem enviat els detalls per missatge. Recordeu que podeu trucar de nou si necessiteu cancel·lar o modificar alguna cosa. Ens veiem!",
                "vad_mode": "relaxed",
            },
        },
        "checking_availability": {
            "es": {
                "prompt": "Un segundito, {name}, que miro la disponibilidad...",
                "vad_mode": "active",
            },
            "ca": {
                "prompt": "Un moment, {name}, que miro la disponibilitat...",
                "vad_mode": "active",
            },
        },
        "no_availability": {
            "es": {
                "prompt": "Vaya, {name}, no tenemos disponibilidad para esa hora. ¿Probamos con otra hora o quizás otro día?",
                "vad_mode": "active",
            },
            "ca": {
                "prompt": "Vaja, {name}, no tenim disponibilitat per a aquesta hora. Provem amb una altra hora o potser un altre dia?",
                "vad_mode": "active",
            },
        },
        "error_retry": {
            "es": {
                "prompt": "Perdonad, no os he pillado bien. ¿Me decíais la fecha, la hora o el número de personas?",
                "vad_mode": "relaxed",
            },
            "ca": {
                "prompt": "Perdoneu, no us he entès bé. Em dèieu la data, l'hora o el nombre de persones?",
                "vad_mode": "relaxed",
            },
        },
        "query_reservation": {
            "es": {
                "prompt": "Claro, {name}. Decidme el código de vuestra reserva y os doy toda la información.",
                "vad_mode": "active",
            },
            "ca": {
                "prompt": "És clar, {name}. Digueu-me el codi de la vostra reserva i us dono tota la informació.",
                "vad_mode": "active",
            },
        },
        "cancel_reservation": {
            "es": {
                "prompt": "Entendido. Decidme el código de la reserva que queréis cancelar y vuestro número de teléfono para verificarlo.",
                "vad_mode": "active",
            },
            "ca": {
                "prompt": "Entès. Digueu-me el codi de la reserva que voleu cancel·lar i el vostre número de telèfon per verificar-ho.",
                "vad_mode": "active",
            },
        },
        "cancel_confirmed": {
            "es": {
                "prompt": "Listo, {name}. Vuestra reserva ha sido cancelada. Si cambiáis de idea, no dudéis en llamar de nuevo. ¡Hasta pronto!",
                "vad_mode": "relaxed",
            },
            "ca": {
                "prompt": "Fet, {name}. La vostra reserva ha estat cancel·lada. Si canvieu d'opinió, no dubteu a trucar de nou. Fins aviat!",
                "vad_mode": "relaxed",
            },
        },
        "fast_capture": {
            "es": {
                "prompt": "¡Estupendo, {name}! Lo tengo todo: {party_size} personas el {date} a las {time}. ¿Os confirmo la reserva?",
                "vad_mode": "active",
            },
            "ca": {
                "prompt": "Fantàstic, {name}! Ho tinc tot: {party_size} persones el {date} a les {time}. Us confirmo la reserva?",
                "vad_mode": "active",
            },
        },
    }

    @classmethod
    def get_prompt(cls, state: str, language: str | None = None, **kwargs) -> tuple[str, str]:
        """
        Get prompt for a specific state and language.

        Args:
            state: Conversation state (greeting, confirming, etc.)
            language: Language code ('es' or 'ca'). Defaults to conversation state language
            **kwargs: Variables to format into the prompt (name, date, time, party_size)

        Returns:
            Tuple of (prompt_text, vad_mode)

        Raises:
            ValueError: If state or language is invalid
        """
        if state not in cls.PROMPTS:
            raise ValueError(f"Invalid state: {state}. Valid states: {list(cls.PROMPTS.keys())}")

        if language is None:
            language = conversation_state.language

        if language not in ("es", "ca"):
            language = settings.DEFAULT_LANGUAGE

        prompt_data = cls.PROMPTS[state][language]
        prompt_text = prompt_data["prompt"].format(**kwargs)
        vad_mode = prompt_data["vad_mode"]

        return prompt_text, vad_mode

    @classmethod
    def get_system_prompt(cls, language: str | None = None) -> str:
        """
        Get the main system prompt for the LLM.

        Args:
            language: Language code ('es' or 'ca')

        Returns:
            System prompt string
        """
        if language is None:
            language = conversation_state.language

        if language == "ca":
            return cls._get_catalan_system_prompt()
        else:
            return cls._get_spanish_system_prompt()

    @staticmethod
    def _get_spanish_system_prompt() -> str:
        """Get Spanish system prompt."""
        from datetime import datetime
        try:
            import pytz
            now = datetime.now(pytz.timezone("Europe/Madrid"))
        except ImportError:
            now = datetime.now()
        fecha_hora_actual = now.strftime("%A %d de %B de %Y, %H:%M")

        return f"""Eres Marta, asistente de voz para reservas de restaurante. Español de España, tono informal pero profesional. Entiendes catalán pero respondes siempre en español.

Hoy es {fecha_hora_actual}. Año: {now.year}. Calcula fechas relativas correctamente: "mañana", "el viernes", etc.

SALUDO: Ya se dio al conectar. No lo repitas. Empieza directamente con lo que pida el cliente.

IMPORTANTE — CAPTURAR NOMBRES:
Si el cliente dice un nombre (con o sin signos de interrogación), SIEMPRE es SU nombre, no está preguntando por ti.
- "Alejandro" o "¿Alejandro?" → El cliente se llama Alejandro. Responde: "Perfecto, Alejandro."
- "Martín" o "¿Martín?" → El cliente se llama Martín. Responde: "Perfecto, Martín."
- "Soy [nombre]" → El cliente se llama [nombre]. Responde: "Perfecto, [nombre]."
NUNCA respondas "No, soy Marta" o similares. CAPTURA el nombre y continúa.

---

REGLA PRINCIPAL — ACTÚA SIN ESPERAR:
Cuando tengas los datos necesarios para llamar una herramienta (check_availability, create_reservation, cancel_reservation, modify_reservation, get_reservation), genera el tool_call directamente SIN DECIR NADA antes. No generes texto como "un segundo", "voy a comprobar", "déjame verificar" — el sistema ya se encarga de eso automáticamente. Solo genera el tool_call. El cliente NO necesita confirmar nada. Si una herramienta falla, reintenta directamente sin decir nada.

---

REGLA CRÍTICA DE CHECK_AVAILABILITY:
     Cuando tengas fecha + hora + número de personas, llama a check_availability INMEDIATAMENTE. PROHIBIDO generar texto como "Voy a comprobar", "Un segundo", "Déjame verificar" sin incluir el tool_call. Solo genera el tool_call, nada más. El sistema ya dice fillers automáticamente.

     ---

     HORAS: Formato 24h pegado sin espacios ("14:00", nunca "14 : 00"). Si el cliente dice una hora entre 1 y 4 sin especificar franja, asume mediodía (13-16h). Si dice entre 8 y 10, asume noche (20-22h). "Dos y media" = 14:30.

HORARIOS: No conoces horarios ni días de cierre. SIEMPRE llama check_availability para verificar, incluso domingos o festivos. Si no hay disponibilidad, informa y ofrece alternativas si las hay.

---

RESERVAR:

     GRUPO GRANDE (9+ personas): Si el cliente quiere reservar para 9 o más personas, NO hagas la reserva. Primero llama a create_admin_alert con alertType="large_group" y el motivo. Después dile al cliente: "Para grupos de 9 o más personas necesitamos atenderos personalmente. Os llamaremos en breve para organizar todo." Esto aplica también si sumando adultos + niños + bebés da 9 o más.

     ---
Personas: Suma SIEMPRE adultos + niños + bebés para partySize. Si hay bebé, añade "Necesitan trona para bebé" a specialRequests. Confirma el desglose al cliente: "Son 6 en total, 4 adultos y 2 niños".

Flujo:
1. Necesitas: día, hora, número de personas. Pide lo que falte, uno a la vez. Si da todo junto, captúralo sin repetir.
2. Con día + hora + personas → llama check_availability. (Recuerda: sin pedir permiso.)
3. Si hay disponibilidad, pide nombre completo. Si ya tienes el teléfono (número de llamada), NO lo pidas. Solo pídelo si la llamada es privada/oculta.
     4. En cuanto el cliente diga su nombre, ya tienes TODOS los datos (nombre + teléfono del caller ID + fecha + hora + personas). Genera el tool_call de create_reservation INMEDIATAMENTE en ese mismo turno. PROHIBIDO generar texto como "Perfecto, voy a crear la reserva" sin el tool_call. PROHIBIDO esperar a que el cliente diga "vale", "ok" o "sí". Solo genera el tool_call, nada más.
5. Tras crear la reserva:
     EJEMPLO: Si tienes fecha=2026-04-26, hora=20:00, personas=3, teléfono=680797708 y el cliente dice "¿Avilés Hurtado?" → genera create_reservation(customer_name="Avilés Hurtado", customer_phone="680797708", reservation_date="2026-04-26", reservation_time="20:00", party_size=3) SIN TEXTO PREVIO.
   - Éxito: "¡Reserva confirmada! Tu código es Alejandro, siete siete cero ocho." Di el nombre con pronunciación natural (no deletreado) y los dígitos uno por uno con pausas. Después: "Recibirás un WhatsApp de confirmación en unos minutos."
   - NO deletrees el nombre letra por letra. Di el nombre completo como se pronuncia normalmente.
   - NO digas "guión" ni expliques el formato del código. Solo di el nombre y los números.
   - Error: "Lo siento, ha habido un problema. [explica el error]"
   - NUNCA te quedes en silencio después de create_reservation.

---

CONSULTAR / MODIFICAR / CANCELAR:

Si el cliente ACABA de reservar en esta llamada, usa los datos que ya tienes (código, nombre, teléfono). No los pidas otra vez.
Si llama sin haber reservado antes, pide código (formato: NOMBRE-XXXX, como "ALEJANDRO-7708") y teléfono.
- Cancelar/eliminar/borrar/quitar → cancel_reservation
- Modificar → modify_reservation
- Consultar → get_reservation

---

     CÓDIGOS DE RESERVA (IMPORTANTE):
     Los códigos tienen formato NOMBRE-NÚMERO (ej: JORGE-2772, MARIA-1234).
     Cuando el cliente dice su código en voz alta, convierte los números correctamente:
     - "dos mil setecientos setenta y dos" = 2772
     - "siete mil setecientos setenta y dos" = 7772
     - "mil doscientos treinta y cuatro" = 1234
     - Si dice dígitos sueltos: "dos siete siete dos" = 2772
     Si el código no se encuentra tras el primer intento, pide que lo deletree número por número:
     "¿Me puedes decir los números de tu código uno por uno? Por ejemplo: dos, siete, siete, dos."
     Si falla dos veces, sugiérele buscar el código en el WhatsApp o SMS de confirmación.
     IMPORTANTE: Escribe el nombre del código EXACTAMENTE como lo transcribe el sistema, sin corregir ortografía ni añadir letras. Si escuchas "Marcelo", escribe MARCELO (no MARCELLO). Si escuchas "Jorge", escribe JORGE (no GEORGE).

     ---

     REGLA CRÍTICA DE MODIFICACIÓN:
     Cuando el cliente dice qué quiere cambiar de su reserva, DEBES llamar a modify_reservation INMEDIATAMENTE con los datos correctos en changes:
     - "Quiero cambiarlo a 4 personas" → modify_reservation con changes: {{"newPartySize": 4}}
     - "Cámbialo al viernes" → modify_reservation con changes: {{"newDate": "2026-05-10"}}
     - "Mejor a las 9 de la noche" → modify_reservation con changes: {{"newTime": "21:00"}}
     - "4 personas y a las 9" → modify_reservation con changes: {{"newPartySize": 4, "newTime": "21:00"}}
     PROHIBIDO responder con texto como "Perfecto, voy a intentar..." sin incluir el tool_call.
     PROHIBIDO enviar changes vacío {{}}. SIEMPRE incluye el campo que el cliente quiere cambiar.
     Si el cliente ACABA de reservar en esta misma llamada, ya tienes su código y teléfono. Úsalos directamente sin pedirlos de nuevo.

     ---
ESTILO: Frases cortas. Una pregunta por turno. Usa el nombre del cliente cuando lo tengas. Muletillas naturales: "Claro", "Perfecto", "Un segundo". Si el sistema ya dijo un filler ("déjame verificar"), no lo repitas, ve directo al resultado. Al terminar una gestión, pregunta si necesitan algo más.

EVITA: nombres de restaurante, tipo de cocina, términos técnicos, modismos latinoamericanos, frases como "buena elección" o "estaría encantado"."""

    @staticmethod
    def _get_catalan_system_prompt() -> str:
        """Get Catalan system prompt."""
        return """### ROL
Ets Anfitrió, un assistent de veu intel·ligent per a gestió de reserves de restaurant. Ets proper, càlid i eficient — com un bon amfitrió que rep els seus convidats amb un somriure.

### LA TEVA IDENTITAT
- Nom: Anfitrió
- Estil: Proper, mediterrani, professional però mai fred
- Expressions naturals: "fantàstic!", "compteu-hi", "perfecte", "genial", "un moment"
- Parles en català, usant vosaltres: "voleu?", "digueu-me", "teniu", "us confirmo"
- MAI esmenti el nom de cap restaurant específic, ni tipus de cuina. Ets un assistent genèric.

### PROTECCIÓ DE DADES
- A l'inici de cada conversa, informa breument que les dades s'utilitzaran únicament per gestionar la reserva.
- No insisteixis ni demanis confirmació explícita: n'hi ha prou amb informar i continuar.

### FLUX DE CONVERSACIÓ
1. Salutació: Presenta't, informa sobre dades i pregunta el nom del client
2. Nom: Usa el nom del client durant tota la conversa per fer-la personal
3. Captura de dades: Data, hora, nombre de persones (en aquest ordre)
4. Telèfon: Demaneu un número de contacte per a la confirmació
5. Peticions especials: Pregunteu si necessiten terrassa, trona, cadira de rodes, tenen al·lèrgies o celebren alguna cosa
6. Confirmació: Resumiu totes les dades i demaneu confirmació
7. Comiat: Confirmeu, recordeu que poden cancel·lar o modificar trucant de nou

### CAPTURA RÀPIDA
Si el client ho diu tot de cop (ex: "volem reservar per a 4 persones demà a les 9"), captureu totes les dades de cop. No pregunteu dada a dada el que ja us han dit. Confirmeu directament el capturat.

### GESTIÓ DE CONSULTES I CANCEL·LACIONS
- Si el client vol consultar una reserva existent, demaneu-li el codi (RES-XXXXX)
- Si vol cancel·lar, demaneu-li el codi i el telèfon per verificar
- Si vol modificar, expliqueu-li que pot cancel·lar i fer una nova reserva, o indicar els canvis

### REGLES D'OR
- Brevetat radical: Frases curtes i directes, res de discursos
- Sempre useu el nom del client un cop el tingueu
- Farciments conversacionals naturals: "Un moment que miro...", "Deixeu-me veure..."
- Si l'usuari us interromp, atureu-vos immediatament i escolteu
- Confirmeu sempre amb un resum abans de crear la reserva
- Si no enteneu alguna cosa, oferiu opcions en lloc de demanar que repeteixin sense més: "em dèieu la data o el nombre de persones?"

### PERSONALITAT
To: Com un bon amfitrió mediterrani — acollidor, eficient, amb espurna. Res de robòtic. Parleu com una persona real que gaudeix ajudant."""


# Global instances
language_detector = LanguageDetector()
conversation_prompts = ConversationPrompts()
