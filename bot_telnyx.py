#
# Pipecat Voice Bot - Telnyx Telephony Transport
# Inbound phone calls via Telnyx WebSocket
# Reuses same reservation logic as WebRTC bot
#
"""Pipecat Voice Bot for Telnyx telephony.
Handles inbound phone calls via Telnyx WebSocket connection.
Same reservation logic as the WebRTC bot, different transport layer.
"""
import os
import sys
import asyncio
import time
from dotenv import load_dotenv
from loguru import logger

# Pipecat core
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame, TTSSpeakFrame, EndFrame, BotStoppedSpeakingFrame, BotStartedSpeakingFrame, VADUserStartedSpeakingFrame, UserStartedSpeakingFrame
from pipecat.observers.base_observer import BaseObserver, FrameProcessed
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.telnyx import TelnyxFrameSerializer

# Services
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.cartesia.tts import (
    CartesiaTTSService,
    language_to_cartesia_language,
    GenerationConfig,
)
from pipecat.services.tts_service import TextAggregationMode
from pipecat.transcriptions.language import Language

# Transport
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

# Function calling
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams

# Load environment
load_dotenv(override=True)

# Shared modules (same as WebRTC bot)
from config import settings, conversation_state
from api_client import call_reservations_api, check_availability_with_cache
from validators import validate_reservation_params, sanitize_special_requests
from metrics import metrics
from tts_monitor import tts_monitor, measure_tts_latency, log_tts_summary
from text_normalizer import normalize_customer_name, normalize_text
from adaptive_vad import adaptive_vad, conversation_tracker
from conversation_prompts import conversation_prompts

# Validate required env vars
REQUIRED_KEYS = ["OPENAI_API_KEY", "DEEPGRAM_API_KEY", "CARTESIA_API_KEY", "TELNYX_API_KEY"]
missing_keys = [k for k in REQUIRED_KEYS if not os.getenv(k)]
if missing_keys:
    logger.error(f"❌ Missing env vars: {', '.join(missing_keys)}")
    sys.exit(1)

logger.info("📞 Telnyx Telephony Bot initializing...")
logger.info(f"📊 Bot: {settings.BOT_NAME}")
logger.info(f"🎙️ Voice: {settings.DEFAULT_VOICE} ({settings.voice_id})")


# ============================================================================
# Function Handlers (identical to WebRTC bot)
# ============================================================================

async def handle_create_reservation(params: FunctionCallParams):
    """Handle create_reservation function call with validation and retry."""
    metrics.function_called("create_reservation")

    is_valid, errors = validate_reservation_params(
        customer_name=params.arguments.get("customer_name", ""),
        customer_phone=params.arguments.get("customer_phone", ""),
        restaurant_id=params.arguments.get("restaurant_id", ""),
        reservation_date=params.arguments.get("reservation_date", ""),
        reservation_time=params.arguments.get("reservation_time", ""),
        party_size=params.arguments.get("party_size", 1),
        special_requests=params.arguments.get("special_requests"),
        available_restaurants=settings.restaurant_ids,
    )

    if not is_valid:
        metrics.function_called("create_reservation", success=False)
        await params.result_callback({
            "voice_message": "Por favor, corrige los siguientes errores: " + "; ".join(errors),
            "success": False,
        })
        return

    if "special_requests" in params.arguments:
        params.arguments["special_requests"] = sanitize_special_requests(
            params.arguments["special_requests"]
        )

    customer_name = normalize_customer_name(params.arguments.get("customer_name", ""))
    customer_phone = normalize_text(params.arguments.get("customer_phone", ""))

    # Generate reservation code: NAME + last 4 digits of phone
    # Example: ALEJANDRO-7708 (for phone 680797708)
    name_part = customer_name.split()[0].upper()  # First name only, uppercase
    phone_part = customer_phone[-4:] if len(customer_phone) >= 4 else customer_phone
    reservation_code = f"{name_part}-{phone_part}"

    api_params = {
        "customerName": customer_name,
        "customerPhone": customer_phone,
        "date": params.arguments.get("reservation_date", ""),
        "time": params.arguments.get("reservation_time", ""),
        "partySize": params.arguments.get("party_size", 1),
        "reservationCode": reservation_code,  # Suggest code to API
    }
    if params.arguments.get("special_requests"):
        api_params["specialRequests"] = params.arguments["special_requests"]

    result = await call_reservations_api("createReservation", api_params)

    await params.result_callback({
        "voice_message": result.get("voiceMessage", "Reserva creada"),
        "reservation_code": result.get("reservationCode"),
        "success": result.get("success", False),
    })


async def handle_get_reservation(params: FunctionCallParams):
    """Handle get_reservation function call."""
    metrics.function_called("get_reservation")
    # Normalize reservation code to uppercase (STT may return lowercase)
    code = params.arguments["code"].upper()
    result = await call_reservations_api("getReservation", {"code": code})
    await params.result_callback({
        "voice_message": result.get("voiceMessage", "Reserva encontrada"),
        "reservation": result.get("reservation"),
        "success": result.get("success", False),
    })


async def handle_cancel_reservation(params: FunctionCallParams):
    """Handle cancel_reservation function call."""
    metrics.function_called("cancel_reservation")
    # Normalize reservation code to uppercase (STT may return lowercase)
    args = params.arguments.copy()
    if "code" in args:
        args["code"] = args["code"].upper()
    result = await call_reservations_api("cancelReservation", args)
    await params.result_callback({
        "voice_message": result.get("voiceMessage", "Reserva cancelada"),
        "success": result.get("success", False),
    })


async def handle_modify_reservation(params: FunctionCallParams):
    """Handle modify_reservation function call."""
    metrics.function_called("modify_reservation")
    # Normalize reservation code to uppercase (STT may return lowercase)
    args = params.arguments.copy()
    if "code" in args:
        args["code"] = args["code"].upper()
    result = await call_reservations_api("modifyReservation", args)
    await params.result_callback({
        "voice_message": result.get("voiceMessage", "Reserva modificada"),
        "success": result.get("success", False),
    })


async def handle_check_availability(params: FunctionCallParams):
    """Handle check_availability function call with caching."""
    metrics.function_called("check_availability")

    result = await check_availability_with_cache(
        date=params.arguments["date"],
        time=params.arguments["time"],
        party_size=params.arguments["partySize"],
    )

    success = result.get("success", False)
    available_slots = result.get("availableSlots", [])

    if success:
        voice_message = (
            f"HAY DISPONIBILIDAD para {params.arguments['date']} "
            f"a las {params.arguments['time']} para {params.arguments['partySize']} personas. "
            f"Pide nombre y teléfono para crear la reserva."
        )
    else:
        voice_message = result.get("message", result.get("voiceMessage", "No hay disponibilidad"))

    if not success and available_slots:
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
        "success": success,
    })


# ============================================================================
# Tool Definitions (identical to WebRTC bot)
# ============================================================================

def build_tools():
    """Build the function schemas and tools for the LLM."""
    create_reservation_func = FunctionSchema(
        name="create_reservation",
        description="Call this function when user confirms their name and you already have phone from caller ID, date, time and partySize. Generate ONLY the tool_call. The phone number is in the system prompt under INFORMACIÓN DE LA LLAMADA. Do not generate any text, only the tool_call.",
        properties={
            "customer_name": {"type": "string", "description": "Customer full name"},
            "customer_phone": {"type": "string", "description": "Phone number (format: Spanish mobile: 6XX XXX XXX)"},
            "restaurant_id": {"type": "string", "enum": settings.restaurant_ids, "description": f"Restaurant location: {', '.join(settings.restaurant_ids)}"},
            "reservation_date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
            "reservation_time": {"type": "string", "description": "Time in HH:MM format (24h). Business hours: 13:00-16:00, 20:00-23:30"},
            "party_size": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Number of people"},
            "special_requests": {"type": "string", "description": "Special requests or allergies (optional)"},
        },
        required=["customer_name", "customer_phone", "restaurant_id", "reservation_date", "reservation_time", "party_size"],
    )

    get_reservation_func = FunctionSchema(
        name="get_reservation",
        description="Get details of an existing reservation by code. Code format: NAME-XXXX (e.g., ALEJANDRO-7708). The code is the customer's first name followed by the last 4 digits of their phone.",
        properties={
            "code": {"type": "string", "description": "Reservation code in format NAME-XXXX (e.g., ALEJANDRO-7708)"},
        },
        required=["code"],
    )

    cancel_reservation_func = FunctionSchema(
        name="cancel_reservation",
        description="Cancel an existing reservation. Requires code (format: NAME-XXXX, e.g., ALEJANDRO-7708) and phone for verification.",
        properties={
            "code": {"type": "string", "description": "Reservation code"},
            "phone": {"type": "string", "description": "Phone number used for reservation"},
        },
        required=["code", "phone"],
    )

    modify_reservation_func = FunctionSchema(
        name="modify_reservation",
        description="Modify an existing reservation. Requires code (format: NAME-XXXX, e.g., ALEJANDRO-7708), phone, and changes to make.",
        properties={
            "code": {"type": "string", "description": "Reservation code in format NAME-XXXX (e.g., ALEJANDRO-7708)"},
            "phone": {"type": "string", "description": "Phone number for verification"},
            "changes": {
                "type": "object",
                "description": "Changes to make (at least one required)",
                "properties": {
                    "newDate": {"type": "string", "description": "New date YYYY-MM-DD"},
                    "newTime": {"type": "string", "description": "New time HH:MM"},
                    "newPartySize": {"type": "integer", "description": "New number of people"},
                    "newSpecialRequests": {"type": "string", "description": "Special requests or observations"},
                },
            },
        },
        required=["code", "phone", "changes"],
    )

    check_availability_func = FunctionSchema(
        name="check_availability",
        description="Call this function when you have date, time and partySize. Generate ONLY the tool_call, do not generate any text before or instead of calling this function.",
        properties={
            "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
            "time": {"type": "string", "description": "Time in HH:MM format"},
            "partySize": {"type": "integer", "description": "Number of people"},
        },
        required=["date", "time", "partySize"],
    )

    return ToolsSchema(standard_tools=[
        create_reservation_func,
        get_reservation_func,
        cancel_reservation_func,
        modify_reservation_func,
        check_availability_func,
    ])


# ============================================================================
# Main Bot Logic — Telnyx Telephony
# ============================================================================

async def bot(runner_args: RunnerArguments):
    """Main bot entry point for Telnyx inbound calls."""

    # Parse the Telnyx WebSocket handshake
    _, call_data = await parse_telephony_websocket(runner_args.websocket)

    from_number = call_data.get("from", "unknown")
    stream_id = call_data.get("stream_id", "")
    call_control_id = call_data.get("call_control_id", "")

    logger.info(f"📞 Incoming call from: {from_number}")
    logger.info(f"🔗 Stream ID: {stream_id}")

    call_id = f"telnyx_{int(time.time() * 1000)}"
    metrics.call_started(call_id)
    conversation_tracker.start_conversation()
    adaptive_vad.reset()
    conversation_state.reset()

    # ── Timeout management ─────────────────────────────────────────────────
    # End call if user doesn't speak within timeout seconds after bot stops
    timeout_seconds = settings.CALL_TIMEOUT_SECONDS

    class CallTimeoutObserver(BaseObserver):
        """Observer that ends the call if user doesn't speak within timeout."""

        def __init__(self):
            super().__init__()
            self.timeout_task = None
            self.user_has_spoken = False
            self.task_ref = None

        def set_task(self, task):
            """Set reference to the PipelineTask."""
            self.task_ref = task

        async def end_call_on_timeout(self):
            """End the call after timeout seconds of silence."""
            try:
                await asyncio.sleep(timeout_seconds)
                if not self.user_has_spoken and self.task_ref:
                    logger.info(f"⏱️ Timeout: No user speech for {timeout_seconds}s, ending call")
                    await self.task_ref.queue_frames([EndFrame()])
            except asyncio.CancelledError:
                pass

        def start_timeout(self):
            """Start the timeout timer when bot stops speaking."""
            if self.timeout_task and not self.timeout_task.done():
                self.timeout_task.cancel()
            self.user_has_spoken = False
            self.timeout_task = asyncio.create_task(self.end_call_on_timeout())

        def cancel_timeout(self):
            """Cancel the timeout when user starts speaking."""
            if self.timeout_task and not self.timeout_task.done():
                self.timeout_task.cancel()
            self.user_has_spoken = True

        async def on_process_frame(self, data: FrameProcessed):
            """Monitor all frames flowing through the pipeline."""
            frame = data.frame
            # When bot stops speaking, start timeout
            if isinstance(frame, BotStoppedSpeakingFrame):
                logger.debug(f"🤖 Bot stopped speaking, starting {timeout_seconds}s timeout")
                self.start_timeout()
            # When bot starts speaking again, cancel any pending timeout
            elif isinstance(frame, BotStartedSpeakingFrame):
                logger.debug("🤖 Bot started speaking, cancelling pending timeout")
                self.cancel_timeout()
            # When user starts speaking, cancel timeout (VAD or Transcription-based)
            elif isinstance(frame, (VADUserStartedSpeakingFrame, UserStartedSpeakingFrame)):
                logger.debug("👤 User started speaking, cancelling timeout")
                self.cancel_timeout()

    timeout_observer = CallTimeoutObserver()

    # ── Telnyx serializer ──────────────────────────────────────────────
    serializer = TelnyxFrameSerializer(
        stream_id=stream_id,
        outbound_encoding=call_data.get("outbound_encoding", "PCMU"),
        inbound_encoding=call_data.get("inbound_encoding", "PCMU"),
        call_control_id=call_control_id,
        api_key=os.getenv("TELNYX_API_KEY"),
    )

    # ── WebSocket transport (8 kHz telephony audio) ────────────────────
    transport = FastAPIWebsocketTransport(
        websocket=runner_args.websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
        ),
    )

    # ── System prompt ──────────────────────────────────────────────────
    system_prompt = conversation_prompts.get_system_prompt()

    # Add caller-ID context to system prompt
    if from_number and from_number != "unknown":
        # Remove +34 prefix for display
        clean_number = from_number.replace("+34", "")
        system_prompt += (
            f"\n\nINFORMACIÓN DE LA LLAMADA:"
            f"\n- El cliente llama desde el número: {clean_number}"
            f"\n- Ya tienes su teléfono: {clean_number}"
            f"\n- NO se lo pidas de nuevo. Úsalo directamente como customer_phone."
            f"\n- Solo pide teléfono si el cliente dice explícitamente que quiere usar otro número."
            f"\n- Cuando el cliente confirme su nombre (incluso como pregunta: \"¿Juan García?\"), eso completa todos los datos. Genera el tool_call de create_reservation directamente."
        )
    else:
        # Número privado/oculto
        system_prompt += (
            f"\n\nINFORMACIÓN DE LA LLAMADA:"
            f"\n- El cliente llama desde número privado/oculto"
            f"\n- DEBES pedir su número de teléfono para la reserva"
            f"\n- Pídelo diciendo: 'Como estoy llamando desde número privado, ¿me puedes dar tu teléfono para la reserva?'"
        )

    messages = [{"role": "system", "content": system_prompt}]

    # ── Tools ──────────────────────────────────────────────────────────
    tools = build_tools()

    # ── Services (8 kHz for telephony) ─────────────────────────────────
    stt = DeepgramSTTService(
        api_key=settings.DEEPGRAM_API_KEY,
        settings=DeepgramSTTService.Settings(
            language=Language.ES,
        ),
    )
    logger.info("✅ Deepgram STT initialized (8 kHz, Spanish)")

    tts = CartesiaTTSService(
        api_key=settings.CARTESIA_API_KEY,
        settings=CartesiaTTSService.Settings(
            model="sonic-3",
            voice=settings.voice_id,
            language=language_to_cartesia_language(Language.ES),
            generation_config=GenerationConfig(
                speed=settings.TTS_SPEED,
                emotion=settings.TTS_EMOTION,
            ),
        ),
        text_aggregation_mode=TextAggregationMode.TOKEN,
    )
    logger.info(f"✅ Cartesia TTS initialized (8 kHz, {settings.DEFAULT_VOICE})")

    llm = OpenAILLMService(
        api_key=settings.OPENAI_API_KEY,
        model=settings.LLM_MODEL,
    )
    logger.info(f"✅ OpenAI LLM initialized ({settings.LLM_MODEL})")

    # Register function handlers
    llm.register_function("create_reservation", handle_create_reservation)
    llm.register_function("get_reservation", handle_get_reservation)
    llm.register_function("cancel_reservation", handle_cancel_reservation)
    llm.register_function("modify_reservation", handle_modify_reservation)
    llm.register_function("check_availability", handle_check_availability)

    # ── Filler phrases during function calls ───────────────────────────
    # TAREA 19: Fillers mejorados (5-7s) para cubrir latencias TTS anormales
    @llm.event_handler("on_function_calls_started")
    async def on_function_calls_started(service, function_calls):
        for fc in function_calls:
            logger.debug(f"FunctionCall: {fc.function_name}")
            if fc.function_name == "check_availability":
                # Filler de ~5 segundos
                await tts.queue_frame(TTSSpeakFrame(
                    "Déjame verificar disponibilidad en ese horario. "
                    "Un momento, por favor, estoy consultando el sistema..."
                ))
            elif fc.function_name == "create_reservation":
                # Filler de ~6 segundos
                await tts.queue_frame(TTSSpeakFrame(
                    "Perfecto, voy a crear tu reserva. "
                    "Déjame un momento que registro todos los datos en el sistema..."
                ))
            elif fc.function_name == "modify_reservation":
                # Filler contextual según el tipo de modificación
                changes = fc.arguments.get("changes", {}) if hasattr(fc, 'arguments') else {}
                change_type = next(iter(changes.keys())) if changes else None

                if change_type == "newSpecialRequests":
                    await tts.queue_frame(TTSSpeakFrame(
                        "Perfecto, estoy añadiendo esa observación a tu reserva. "
                        "Déjame un momento que actualizo los detalles en el sistema..."
                    ))
                elif change_type == "newDate":
                    await tts.queue_frame(TTSSpeakFrame(
                        "Entendido, quieres cambiar el día de la reserva. "
                        "Déjame verificar la disponibilidad para la nueva fecha..."
                    ))
                elif change_type == "newTime":
                    await tts.queue_frame(TTSSpeakFrame(
                        "Vale, quieres cambiar la hora. "
                        "Déjame un momento que compruebo si hay mesas disponibles..."
                    ))
                elif change_type == "newPartySize":
                    await tts.queue_frame(TTSSpeakFrame(
                        "Perfecto, estás cambiando el número de personas. "
                        "Déjame actualizar la reserva con el nuevo grupo..."
                    ))
                else:
                    # Filler genérico de ~6 segundos
                    await tts.queue_frame(TTSSpeakFrame(
                        "Déjame modificar tu reserva con esos cambios. "
                        "Un momento, por favor, estoy actualizando el sistema..."
                    ))
            elif fc.function_name == "cancel_reservation":
                # Filler de ~5 segundos
                await tts.queue_frame(TTSSpeakFrame(
                    "Vale, voy a procesar la cancelación de tu reserva. "
                    "Déjame un momento que lo hago en el sistema..."
                ))
            elif fc.function_name == "get_reservation":
                # Filler de ~4 segundos
                await tts.queue_frame(TTSSpeakFrame(
                    "Déjame buscar tu reserva en el sistema..."
                ))

        # Context truncation
        msgs = context.get_messages()
        if len(msgs) > 15:
            context.set_messages([msgs[0]] + msgs[-14:])
            logger.debug(f"Context truncated: {len(msgs)} -> {len(context.get_messages())}")

    # ── LLM context + VAD ──────────────────────────────────────────────
    context = LLMContext(messages, tools=tools)

    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(
                params=adaptive_vad.get_params(),
            ),
        ),
    )

    # ── Pipeline ───────────────────────────────────────────────────────
    pipeline = Pipeline([
        transport.input(),
        stt,
        user_aggregator,
        llm,
        tts,
        transport.output(),
        assistant_aggregator,
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[timeout_observer],  # Add timeout observer
    )

    # Set task reference in timeout observer
    timeout_observer.set_task(task)

    # ── Handle call disconnect ─────────────────────────────────────────
    @transport.event_handler("on_connection_closed")
    async def on_connection_closed(transport_obj):
        logger.info(f"📞 Call ended: {from_number} (call_id: {call_id})")
        metrics.call_ended(call_id, success=True)
        summary = conversation_tracker.get_summary()
        logger.info(f"📊 Conversation summary: {summary}")
        metrics.log_summary()

        # TAREA 19: Log TTS latency summary
        log_tts_summary()

    # ── Start: greet the caller via LLM ────────────────────────────────
    # Queue an LLMRunFrame so the LLM generates the initial greeting
    # based on the system prompt (same greeting as WebRTC)
    greeting_prompt, _ = conversation_prompts.get_prompt("greeting")
    await task.queue_frames([TTSSpeakFrame(greeting_prompt)])

    # ── Run ────────────────────────────────────────────────────────────
    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)

    logger.info(f"✅ Call pipeline finished: {call_id}")


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
