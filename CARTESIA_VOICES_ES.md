# Cartesia Spanish Voices - Guía Rápida

Este archivo contiene todas las voces disponibles de Cartesia para español, junto con sus IDs y descripciones.

## Configuración Actual

```python
voice="b0689631-eee7-4a6c-bb86-195f1d267c2e"  # Emilio - Friendly Optimist
```

## Todas las Voces Disponibles

| Nombre | Voice ID | Descripción | Uso Recomendado |
|--------|----------|-------------|-----------------|
| **Emilio** | `b0689631-eee7-4a6c-bb86-195f1d267c2e` | Friendly Optimist | ✅ DEFAULT - Asistente amigable y positivo |
| **Catalina** | `162e0f37-8504-474c-bb33-c606c01890dc` | Neighborly Guide | Voz vecinal, cercana y guía |
| **Andrea** | `59b37da2-92ba-401a-9e4e-b1d16898d9bc` | Clear Communicator | Comunicación clara y profesional |
| **Paola** | `e361b786-2768-4308-9369-a09793d4dd73` | Expressive Performer | Expresiva y emotiva |
| **Mariana** | `ae823354-f9be-4aef-8543-f569644136b4` | Nurturing Guide | Guía nutritiva y de apoyo |
| **Pedro** | `15d0c2e2-8d29-44c3-be23-d585d5f154a1` | Formal Speaker | Para situaciones formales |
| **Alondra** | `ccfea4bf-b3f4-421e-87ed-dd05dae01431` | Reassuring Sister | Hermana tranquilizadora |
| **Elena** | `cefcB124-080b-4655-b31f-932f3ee743de` | Narrator | Para narraciones y cuentos |
| **Fran** | `79743797-2087-422f-8dc7-86f9efca85f1` | Confident Young Professional | Profesional joven y seguro |
| **Benito** | `02aeee94-c02b-456e-be7a-659672acf82d` | Digital Voice | Voz digital/robotica |

## Cómo Cambiar la Voz

Edita `bot_server.py` y cambia el `voice` en la configuración:

```python
tts = CartesiaTTSService(
    api_key=os.getenv("CARTESIA_API_KEY"),
    settings=CartesiaTTSService.Settings(
        model="sonic-3",
        voice="PON_AQUI_EL_VOICE_ID",  # ← Cambiar este valor
        language=language_to_cartesia_language(Language.ES),
        generation_config=GenerationConfig(
            speed=1.0,
            emotion="neutral"
        )
    ),
    text_aggregation_mode=TextAggregationMode.TOKEN,
)
```

## Emociones Disponibles

El parámetro `emotion` en `GenerationConfig` acepta:
- `neutral` (default)
- `happy`
- `excited`
- `content`
- `sad`
- `scared`
- `angry`
- `calm`
- `enthusiastic`
- `curious`
- Y más de 60 emociones disponibles

## Configuración de Velocidad

```python
generation_config=GenerationConfig(
    speed=1.0,  # 0.6 (lento) a 1.5 (rápido)
    emotion="neutral"
)
```

## Configuración de Volumen

```python
generation_config=GenerationConfig(
    volume=1.0,  # 0.5 a 2.0 (1.0 = normal)
    speed=1.0,
    emotion="neutral"
)
```

## Prueba Rápida de Voces

Para probar diferentes voces rápidamente, puedes crear este script de prueba:

```python
# test_voices.py
from pipecat.services.cartesia import CartesiaTTSService, language_to_cartesia_language, GenerationConfig
from pipecat.services.tts_service import TextAggregationMode
from pipecat.transcriptions.language import Language
import os
import asyncio

VOICES = {
    "Emilio": "b0689631-eee7-4a6c-bb86-195f1d267c2e",
    "Catalina": "162e0f37-8504-474c-bb33-c606c01890dc",
    "Andrea": "59b37da2-92ba-401a-9e4e-b1d16898d9bc",
}

async def test_voice(voice_name, voice_id):
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        settings=CartesiaTTSService.Settings(
            model="sonic-3",
            voice=voice_id,
            language=language_to_cartesia_language(Language.ES),
        ),
        text_aggregation_mode=TextAggregationMode.TOKEN,
    )
    print(f"Probando {voice_name}...")

# Ejecutar pruebas
for name, voice_id in VOICES.items():
    await test_voice(name, voice_id)
```

## Referencias

- Documentación de Cartesia: https://docs.cartesia.ai/
- API de voces: https://docs.cartesia.ai/api-reference/voices/list
- Modelos sonic-3: https://docs.cartesia.ai/build-with-cartesia/tts-models/latest
- Español en Cartesia: https://cartesia.ai/languages/spanish

## Notas de Latencia

- **Modelo sonic-3**: ~90ms de latencia del modelo
- **TOKEN mode**: Reduce ~200-300ms adicionales
- **Latencia total esperada**: ~300-400ms desde que el LLM termina hasta que el audio comienza

## Troubleshooting

### La voz no suena natural en español
- Verifica que `language=language_to_cartesia_language(Language.ES)` esté configurado
- Asegúrate de estar usando una voz con `language="es"` (todas las de esta lista)

### La latencia es alta
- Confirma que `text_aggregation_mode=TextAggregationMode.TOKEN` esté activo
- Verifica que estés usando `model="sonic-3"`

### Error de autenticación
- Verifica que `CARTESIA_API_KEY` sea correcta en `.env`
- Confirma que la API key tenga acceso al servicio TTS
