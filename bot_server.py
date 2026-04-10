#
# Pipecat Voice Bot Server - Enhanced Version
# Copyright (c) 2024-2025
#
"""Pipecat Voice Bot using RTVI framework with improvements:
- Retry logic for API calls
- Adaptive VAD
- Language detection (Spanish/Catalan)
- Contextual conversation prompts
- Structured metrics and logging
"""
import os
import sys
import asyncio
from dotenv import load_dotenv
from loguru import logger

# Pipecat imports - updated structure for 2025
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments, SmallWebRTCRunnerArguments
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.anthropic.llm import AnthropicLLMService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.cartesia.tts import CartesiaTTSService, language_to_cartesia_language, GenerationConfig
from pipecat.services.tts_service import TextAggregationMode
from pipecat.transcriptions.language import Language
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

# Function calling imports
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams
from pipecat.frames.frames import TTSSpeakFrame

# Load environment variables
load_dotenv(override=True)

# Import enhanced modules
from config import settings, conversation_state
from api_client import call_reservations_api, check_availability_with_cache, validate_and_create_reservation
from validators import validate_reservation_params, sanitize_special_requests
from metrics import metrics, latency_tracker
from text_normalizer import normalize_customer_name, normalize_text
from adaptive_vad import adaptive_vad, conversation_tracker
from conversation_prompts import conversation_prompts, language_detector

# Validate required environment variables
REQUIRED_API_KEYS = ["OPENAI_API_KEY", "DEEPGRAM_API_KEY", "CARTESIA_API_KEY"]
missing_keys = [key for key in REQUIRED_API_KEYS if not os.getenv(key)]

if missing_keys:
    logger.error(f"❌ Faltan variables de entorno requeridas: {', '.join(missing_keys)}")
    logger.error("Por favor, configura las siguientes variables en tu archivo .env:")
    for key in missing_keys:
        logger.error(f"  - {key}")
    sys.exit(1)

logger.info("✅ Todas las variables de entorno requeridas están configuradas")
logger.info(f"📊 Bot: {settings.BOT_NAME}")
logger.info(f"🌐 Voz: {settings.DEFAULT_VOICE} ({settings.voice_id})")
logger.info(f"⚡ API Timeout: {settings.API_TIMEOUT}s | Max Retries: {settings.MAX_RETRIES}")
logger.info(f"🎯 VAD: Active={settings.VAD_SILENCE_MS_ACTIVE}ms | Relaxed={settings.VAD_SILENCE_MS_RELAXED}ms")


# ============================================================================
# Function Handlers with Enhanced Error Handling and Metrics
# ============================================================================

async def handle_create_reservation(params: FunctionCallParams):
    """Handle create_reservation function call with validation and retry."""
    metrics.function_called("create_reservation")

    # Validate parameters
    is_valid, errors = validate_reservation_params(
        customer_name=params.arguments.get("customer_name", ""),
        customer_phone=params.arguments.get("customer_phone", ""),
        restaurant_id=params.arguments.get("restaurant_id", ""),
        reservation_date=params.arguments.get("reservation_date", ""),
        reservation_time=params.arguments.get("reservation_time", ""),
        party_size=params.arguments.get("party_size", 1),
        special_requests=params.arguments.get("special_requests"),
        available_restaurants=settings.restaurant_ids
    )

    if not is_valid:
        metrics.function_call_failures("create_reservation")
        await params.result_callback({
            "voice_message": "Por favor, corrige los siguientes errores: " + "; ".join(errors),
            "success": False
        })
        return

    # Sanitize special requests
    if "special_requests" in params.arguments:
        params.arguments["special_requests"] = sanitize_special_requests(
            params.arguments["special_requests"]
        )

    # TAREA 11: Normalizar texto del cliente (nombres y números)
    customer_name = normalize_customer_name(params.arguments.get("customer_name", ""))
    customer_phone = normalize_text(params.arguments.get("customer_phone", ""))
    
    # Map schema fields to API fields
    api_params = {
        "customerName": customer_name,
        "customerPhone": customer_phone,
        "date": params.arguments.get("reservation_date", ""),
        "time": params.arguments.get("reservation_time", ""),
        "partySize": params.arguments.get("party_size", 1),
    }
    if params.arguments.get("special_requests"):
        api_params["specialRequests"] = params.arguments["special_requests"]
    # Call API with retry logic
    result = await call_reservations_api("createReservation", api_params)

    await params.result_callback({
        "voice_message": result.get("voiceMessage", "Reserva creada"),
        "reservation_code": result.get("reservationCode"),
        "success": result.get("success", False)
    })


async def handle_get_reservation(params: FunctionCallParams):
    """Handle get_reservation function call."""
    metrics.function_called("get_reservation")

    result = await call_reservations_api("getReservation", {"code": params.arguments["code"]})
    await params.result_callback({
        "voice_message": result.get("voiceMessage", "Reserva encontrada"),
        "reservation": result.get("reservation"),
        "success": result.get("success", False)
    })


async def handle_cancel_reservation(params: FunctionCallParams):
    """Handle cancel_reservation function call."""
    metrics.function_called("cancel_reservation")

    result = await call_reservations_api("cancelReservation", params.arguments)
    await params.result_callback({
        "voice_message": result.get("voiceMessage", "Reserva cancelada"),
        "success": result.get("success", False)
    })


async def handle_modify_reservation(params: FunctionCallParams):
    """Handle modify_reservation function call."""
    metrics.function_called("modify_reservation")

    result = await call_reservations_api("modifyReservation", params.arguments)
    await params.result_callback({
        "voice_message": result.get("voiceMessage", "Reserva modificada"),
        "success": result.get("success", False)
    })


async def handle_check_availability(params: FunctionCallParams):
    """Handle check_availability function call with caching."""
    metrics.function_called("check_availability")

    # Use cache for availability checks
    result = await check_availability_with_cache(
        date=params.arguments["date"],
        time=params.arguments["time"],
        party_size=params.arguments["partySize"]
    )

    # Build clear voice message for LLM
    success = result.get("success", False)
    available_slots = result.get("availableSlots", [])
    
    if success:
        voice_message = f"HAY DISPONIBILIDAD para {params.arguments['date']} a las {params.arguments['time']} para {params.arguments['partySize']} personas. Pide nombre y teléfono para crear la reserva."
    else:
        voice_message = result.get("message", result.get("voiceMessage", "No hay disponibilidad"))

    # If not available and there are alternative slots, add them to the message
    if not success and available_slots:
        # Format slots nicely (e.g., "13:00, 13:30, y 14:00")
        if len(available_slots) == 1:
            slots_text = available_slots[0]
        elif len(available_slots) == 2:
            slots_text = f"{available_slots[0]} y {available_slots[1]}"
        else:
            slots_text = ", ".join(available_slots[:-1]) + f", y {available_slots[-1]}"

        voice_message += f" Sin embargo, tenemos mesas disponibles a las {slots_text}. ¿Te gustaría alguna de estas opciones?"

    await params.result_callback({
        "voice_message": voice_message,
        "availableSlots": available_slots,
        "success": success
    })


# ============================================================================
# Main Bot Logic with All Improvements
# ============================================================================

async def run_bot(transport, runner_args: RunnerArguments):
    """Main bot logic with enhanced features."""
    import time
    call_id = f"call_{int(time.time() * 1000)}"
    metrics.call_started(call_id)
    conversation_tracker.start_conversation()
    adaptive_vad.reset()
    conversation_state.reset()

    logger.info(f"Starting Pipecat Voice Bot... (call_id: {call_id})")

    # Get contextual system prompt based on conversation state
    system_prompt = conversation_prompts.get_system_prompt()

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
    ]

    # Define function schemas for OpenAI (dynamic restaurant list)
    create_reservation_func = FunctionSchema(
        name="create_reservation",
        description="Create reservation IMMEDIATELY when you have name, phone, date, time and partySize. Do NOT ask for confirmation.",
        properties={
            "customer_name": {"type": "string", "description": "Customer full name"},
            "customer_phone": {"type": "string", "description": "Phone number (format: Spanish mobile: 6XX XXX XXX)"},
            "restaurant_id": {"type": "string", "enum": settings.restaurant_ids, "description": f"Restaurant location: {', '.join(settings.restaurant_ids)}"},
            "reservation_date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
            "reservation_time": {"type": "string", "description": "Time in HH:MM format (24h). Business hours: 13:00-16:00, 20:00-23:30"},
            "party_size": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Number of people"},
            "special_requests": {"type": "string", "description": "Special requests or allergies (optional)"}
        },
        required=["customer_name", "customer_phone", "restaurant_id", "reservation_date", "reservation_time", "party_size"]
    )

    get_reservation_func = FunctionSchema(
        name="get_reservation",
        description="Get details of an existing reservation by code",
        properties={
            "code": {"type": "string", "description": "Reservation code (e.g., RES-12345)"}
        },
        required=["code"]
    )

    cancel_reservation_func = FunctionSchema(
        name="cancel_reservation",
        description="Cancel an existing reservation. Requires code and phone for verification.",
        properties={
            "code": {"type": "string", "description": "Reservation code"},
            "phone": {"type": "string", "description": "Phone number used for reservation"}
        },
        required=["code", "phone"]
    )

    modify_reservation_func = FunctionSchema(
        name="modify_reservation",
        description="Modify an existing reservation. Requires code, phone, and changes to make.",
        properties={
            "code": {"type": "string", "description": "Reservation code"},
            "phone": {"type": "string", "description": "Phone number for verification"},
            "changes": {
                "type": "object",
                "description": "Changes to make (at least one required)",
                "properties": {
                    "newDate": {"type": "string", "description": "New date YYYY-MM-DD"},
                    "newTime": {"type": "string", "description": "New time HH:MM"},
                    "newPartySize": {"type": "integer", "description": "New number of people"}
                }
            }
        },
        required=["code", "phone", "changes"]
    )

    check_availability_func = FunctionSchema(
        name="check_availability",
        description="ALWAYS call this IMMEDIATELY when you have date, time and partySize. Do NOT ask for confirmation first.",
        properties={
            "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
            "time": {"type": "string", "description": "Time in HH:MM format"},
            "partySize": {"type": "integer", "description": "Number of people"}
        },
        required=["date", "time", "partySize"]
    )

    tools = ToolsSchema(standard_tools=[
        create_reservation_func,
        get_reservation_func,
        cancel_reservation_func,
        modify_reservation_func,
        check_availability_func
    ])

    # ============================================================================
    # Initialize Services with Enhanced Configuration
    # ============================================================================

    try:
        # Initialize STT service with Spanish language
        stt = DeepgramSTTService(
            api_key=settings.DEEPGRAM_API_KEY,
            settings=DeepgramSTTService.Settings(
                language=Language.ES,
            ),
        )
        logger.info("✅ Deepgram STT inicializado (español)")
    except Exception as e:
        logger.error(f"❌ Error inicializando Deepgram STT: {e}")
        raise

    # Use Cartesia TTS with configured voice
    try:
        tts = CartesiaTTSService(
            api_key=settings.CARTESIA_API_KEY,
            settings=CartesiaTTSService.Settings(
                model="sonic-3",
                voice=settings.voice_id,
                language=language_to_cartesia_language(Language.ES),
                generation_config=GenerationConfig(
                    speed=settings.TTS_SPEED,
                    emotion=settings.TTS_EMOTION
                )
            ),
            text_aggregation_mode=TextAggregationMode.TOKEN,
        )
        logger.info(f"✅ Cartesia TTS inicializado ({settings.DEFAULT_VOICE} - sonic-3)")
    except Exception as e:
        logger.error(f"❌ Error inicializando Cartesia TTS: {e}")
        raise

    # Use configured LLM model
    try:
        llm = OpenAILLMService(
            api_key=settings.OPENAI_API_KEY,
            model=settings.LLM_MODEL,
        )
        logger.info(f"✅ OpenAI LLM inicializado ({settings.LLM_MODEL})")
    except Exception as e:
        logger.error(f"❌ Error inicializando OpenAI LLM: {e}")
        raise

    # Register function handlers
    llm.register_function("create_reservation", handle_create_reservation)
    llm.register_function("get_reservation", handle_get_reservation)
    llm.register_function("cancel_reservation", handle_cancel_reservation)
    llm.register_function("modify_reservation", handle_modify_reservation)
    llm.register_function("check_availability", handle_check_availability)
    logger.info("✅ Function handlers registered")

    # Event handler for function calls with contextual prompts
    @llm.event_handler("on_function_calls_started")
    async def on_function_calls_started(service, function_calls):
        # TAREA 8: Agregar filler durante function calls
        for fc in function_calls:
            if fc.name == "check_availability":
                await tts.queue_frame(TTSSpeakFrame("Déjame verificar disponibilidad..."))
            elif fc.name == "create_reservation":
                await tts.queue_frame(TTSSpeakFrame("Un momento, creo tu reserva..."))
            elif fc.name == "modify_reservation":
                await tts.queue_frame(TTSSpeakFrame("Déjame modificar tu reserva..."))
            elif fc.name == "cancel_reservation":
                await tts.queue_frame(TTSSpeakFrame("Proceso a cancelar tu reserva..."))

        # TAREA 9: Truncamiento de contexto (ya implementado)
        msgs = context.get_messages()
        if len(msgs) > 15:
            context.set_messages([msgs[0]] + msgs[-14:])
            logger.debug(f"Context truncated: {len(msgs)} -> {len(context.get_messages())}")

    # Create LLM context and aggregators with ADAPTIVE VAD
    context = LLMContext(messages, tools=tools)

    # Use Adaptive VAD that adjusts based on conversation state
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(
                params=adaptive_vad.get_params(),
            ),
        ),
    )
    logger.info(f"✅ Adaptive VAD configurado: mode={adaptive_vad.mode}")

    # Build pipeline
    pipeline = Pipeline([
        transport.input(),
        stt,
        user_aggregator,
        llm,
        tts,
        transport.output(),
        assistant_aggregator,
    ])

    # Create task with metrics enabled
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    # RTVI event handler with contextual greeting
    @task.rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        await rtvi.set_bot_ready()

        # Get contextual greeting based on language
        greeting_prompt, _ = conversation_prompts.get_prompt("greeting")
        await task.queue_frames([TTSSpeakFrame(greeting_prompt)])

        logger.info(f"📞 Call started: {call_id}")

    # Transport event handlers with metrics
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected: {client}")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected: {client}")

        # Record metrics
        metrics.call_ended(call_id, success=True)

        # Log conversation summary
        summary = conversation_tracker.get_summary()
        logger.info(f"📊 Conversation summary: {summary}")

        # Log metrics summary
        metrics.log_summary()

        # Cleanup
        try:
            await task.cancel()
            logger.info("✅ Task y recursos liberados correctamente")
        except Exception as e:
            logger.warning(f"⚠️  Error durante cleanup: {e}")

    # Run pipeline
    from pipecat.pipeline.runner import PipelineRunner
    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point."""
    if not isinstance(runner_args, SmallWebRTCRunnerArguments):
        logger.error(f"Unsupported runner arguments type: {type(runner_args)}")
        return

    logger.info(f"WebRTC connection: {runner_args.webrtc_connection}")

    # Add TURN servers for NAT traversal
    from pipecat.transports.smallwebrtc.connection import IceServer
    runner_args.webrtc_connection.ice_servers = [
        IceServer(urls="stun:stun.l.google.com:19302"),
        IceServer(urls=settings.TURN_SERVER_URL, username=settings.TURN_USERNAME, credential=settings.TURN_CREDENTIAL),
        IceServer(urls=f"{settings.TURN_SERVER_URL}?transport=tcp", username=settings.TURN_USERNAME, credential=settings.TURN_CREDENTIAL),
    ]
    logger.info("✅ TURN/STUN servers configured")

    # Create transport with WebRTC
    transport = SmallWebRTCTransport(
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
        webrtc_connection=runner_args.webrtc_connection,
    )

    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
