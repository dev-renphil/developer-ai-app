from flask import Flask, request, jsonify
import requests
import json
import base64
import time
import logging
import re
import uuid
import random
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from openai import OpenAI
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

from .ai_dtos import Step1Reply, ReceiveDTO
from .shape import Whiteboard
from .logging_helpers import log_openai_prompt, save_openai_prompt

path = os.path.abspath("/transcriber_utils/")
sys.path.insert(0, path)

from .transcriber_utils.shapes_template import (
    load_shape_template,
    get_shapes_prompt_section,
    get_available_shapes,
    detect_shapes_needed,
    inject_library_shapes,
)
from .transcriber_utils.intersection_analysis import (
    get_intersection_analysis_prompt_section,
)
from .transcriber_utils.sympy_json_converter import (
    convert_whiteboard_to_sympy_json,
    sympy_json_to_objects,
)
from .transcriber_utils.sympy_operations import (
    perform_operation,
    should_draw_result,
    check_sympy_operation_available,
)
from .utils import encode_image_to_base64_compressed
from .prompts import (
    build_main_scaffold_prompt,
    build_vision_scaffold,
    build_step1_decision_prompt_start,
    build_step1_decision_prompt_end,
    build_calculation_hint,
    build_step1_5_shape_identification_prompt,
    build_step1_5_chat_response_prompt,
    build_step2_generation_prompt_start,
    build_step2_generation_prompt_end,
    build_step3_comparison_prompt_with_images,
    build_no_draw_response_prompt,
    build_sympy_result_section_success,
    build_sympy_result_section_llm_fallback,
    step1_build,
    step2_build,
)

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

app = Flask(__name__)
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY must be set in .env file")
client = OpenAI(api_key=openai_api_key)

# Configure logging for TrustCall monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GLOBAL VARIABLES FOR AI USE
whiteboard_states = {}  # TODO: Store history of whiteboard states and use in AI

CACHE_TTL = 300  # Cache for 5 minutes

# TrustCall monitoring metrics
trustcall_metrics = {
    "webhook_calls": 0,
    "webhook_successes": 0,
    "webhook_failures": 0,
    "ai_api_calls": 0,
    "ai_api_successes": 0,
    "ai_api_failures": 0,
    "whiteboard_generations": 0,
    "whiteboard_successes": 0,
    "whiteboard_failures": 0,
    "payload_validation_errors": 0,
    "response_times": [],
}

# GLOBAL API SUFFIXES
WHITEBOARD_PREVIEW_API_SUFFIX = os.getenv("WHITEBOARD_PREVIEW_API_SUFFIX")
if not WHITEBOARD_PREVIEW_API_SUFFIX:
    raise ValueError("WHITEBOARD_PREVIEW_API_SUFFIX must be set in .env file")


def log_trustcall_event(event_type: str, details: Dict[str, Any], success: bool = True):
    """Log events for TrustCall monitoring"""
    timestamp = datetime.now().isoformat()
    event = {
        "timestamp": timestamp,
        "event_type": event_type,
        "success": success,
        "details": details,
    }
    logger.info(f"TrustCall Event: {json.dumps(event)}")

    # Update metrics
    if event_type == "webhook_call":
        trustcall_metrics["webhook_calls"] += 1
        if success:
            trustcall_metrics["webhook_successes"] += 1
        else:
            trustcall_metrics["webhook_failures"] += 1
    elif event_type == "ai_api_call":
        trustcall_metrics["ai_api_calls"] += 1
        if success:
            trustcall_metrics["ai_api_successes"] += 1
        else:
            trustcall_metrics["ai_api_failures"] += 1
    elif event_type == "whiteboard_generation":
        trustcall_metrics["whiteboard_generations"] += 1
        if success:
            trustcall_metrics["whiteboard_successes"] += 1
        else:
            trustcall_metrics["whiteboard_failures"] += 1
    elif event_type == "payload_validation_error":
        trustcall_metrics["payload_validation_errors"] += 1


def validate_whiteboard_payload(
    whiteboard_state: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Validate whiteboard payload structure for TrustCall monitoring"""
    try:
        if not isinstance(whiteboard_state, dict):
            return False, "Whiteboard state must be a dictionary"

        # Check required top-level keys
        required_keys = ["appState", "elements"]
        for key in required_keys:
            if key not in whiteboard_state:
                return False, f"Missing required key: {key}"

        # Validate appState structure
        app_state = whiteboard_state.get("appState", {})
        if not isinstance(app_state, dict):
            return False, "appState must be a dictionary"

        # Validate elements structure
        elements = whiteboard_state.get("elements", [])
        if not isinstance(elements, list):
            return False, "elements must be a list"

        # Validate each element
        for i, element in enumerate(elements):
            if not isinstance(element, dict):
                return False, f"Element {i} must be a dictionary"

            # Check required element fields
            required_element_fields = ["id", "type", "x", "y", "width", "height"]
            for field in required_element_fields:
                if field not in element:
                    return False, f"Element {i} missing required field: {field}"

        return True, None

    except Exception as e:
        return False, f"Validation error: {str(e)}"


def validate_webhook_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate incoming webhook payload for TrustCall monitoring"""
    try:
        required_fields = [
            "message",
            "history",
            "whiteboard_state",
            "session_id",
            "receiving_url",
            "topic",
        ]

        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"

        # Validate whiteboard state
        is_valid, error = validate_whiteboard_payload(data.get("whiteboard_state", {}))
        if not is_valid:
            return False, f"Invalid whiteboard state: {error}"

        return True, None

    except Exception as e:
        return False, f"Payload validation error: {str(e)}"


def clean_openai_response(content: str) -> str:
    content = content.strip()
    lines = content.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]  # Remove the first line (opening backticks)
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]  # Remove the last line (closing backticks)
    return "\n".join(lines).strip()


def encode_image_to_base64(filepath):
    """
    Encode image to base64 with compression.

    This function now uses compression to optimize image size for transmission.
    For OpenAI Vision API, uses quality=85 and max_size=2048 by default.
    """
    return encode_image_to_base64_compressed(
        filepath, quality=85, max_size=2048  # OpenAI's recommended maximum dimension
    )


def get_whiteboard_image_preview(root_url, whiteboard_json, save_name, verbose=True):
    # Build the API preview URL
    preview_url = root_url + WHITEBOARD_PREVIEW_API_SUFFIX
    # Send back to webhook

    # PROSPECTIVE NEW WHITEBOARD:
    print("PREVIEW URL:", preview_url, flush=True)
    preview_response = requests.post(
        preview_url, json=whiteboard_json, headers={"Content-Type": "application/json"}
    )

    # Check if the response is successful
    if preview_response.status_code == 200:
        # Save the image to a file
        with open(save_name, "wb") as f:
            f.write(preview_response.content)
        if verbose:
            print("Image saved successfully.")
    else:
        if verbose:
            print(f"Failed to get image. Status code: {preview_response.status_code}")


def diarize_message(msg_tup, student_id, ai_id):
    if msg_tup["user_id"] == student_id:
        return {
            "text_message": msg_tup["text_message"],
            "timestamp": msg_tup["timestamp"],
            "user_id": "Student",
        }
    elif msg_tup["user_id"] == ai_id:
        return {
            "text_message": msg_tup["text_message"],
            "timestamp": msg_tup["timestamp"],
            "user_id": "AI Tutor (You)",
        }
    else:
        return {
            "text_message": msg_tup["text_message"],
            "timestamp": msg_tup["timestamp"],
            "user_id": "AI Tutor (You)",
        }


def diarize_history(api_history, student_id, ai_id):
    return [diarize_message(m, student_id, ai_id) for m in api_history]


# LOOKBACK LENGTH (MESSAGES ONLY FOR NOW)
lookback_len_str = os.getenv("LOOKBACK_LEN")
if not lookback_len_str:
    raise ValueError("LOOKBACK_LEN must be set in .env file")
LOOKBACK_LEN = int(lookback_len_str)


def describe_user_intent(
    whiteboard,
    receive_dto: ReceiveDTO,
):
    # TODO: Remove this once Musa adds the AI_ID and Student_ID as payload attributes
    parsed_url = urlparse(receive_dto.receiving_url)
    query_params = parse_qs(parsed_url.query)
    ai_id = query_params["ai_tutor_id"][0]
    try:
        student_id = list(
            set([x["user_id"] for x in receive_dto.history if x["user_id"] != ai_id])
        )[0]
    except IndexError:
        student_id = None

    diarized_history = diarize_history(
        receive_dto.history, student_id=student_id, ai_id=ai_id
    )

    # TODO: Consider whether to pass history timestamps in context?
    history_context = "\n".join(
        [
            x["user_id"] + ": " + x["text_message"]
            for x in diarized_history[-LOOKBACK_LEN:-1]
        ]
    )

    # ERROR CHECKS
    if not receive_dto.receiving_url:
        return jsonify({"error": "receiving_url is required"}), 400

    if not any([receive_dto.user_message, whiteboard.to_excalidraw_dict()]):
        return jsonify({"error": "message or whiteboard content is required"}), 400

    PROMPT_SCAFFOLD = step1_build(
        topic=receive_dto.topic,
        history_context=history_context,
        user_message=receive_dto.user_message,
        whiteboard=whiteboard,
    )

    step1_content = [{"type": "text", "text": PROMPT_SCAFFOLD}]
    # WE CAN NOW RUN STEP 1
    # Load OpenAI configuration (used in both try and else blocks)
    openai_model_step1 = os.getenv("OPENAI_MODEL_STEP1")
    if not openai_model_step1:
        raise ValueError("OPENAI_MODEL_STEP1 must be set in .env file")
    openai_temperature_str = os.getenv("OPENAI_TEMPERATURE")
    if not openai_temperature_str:
        raise ValueError("OPENAI_TEMPERATURE must be set in .env file")
    openai_temperature = float(openai_temperature_str)

    try:
        step1_resp = client.chat.completions.create(
            model=openai_model_step1,
            messages=[{"role": "user", "content": step1_content}],
            temperature=openai_temperature,
        )
        step1_str = step1_resp.choices[0].message.content.strip()
        print("Step 1 response:", step1_str)
        step1_reply = Step1Reply(**json.loads(step1_str))

        return step1_reply

    except Exception as e:
        print("Step 1 error:", e)
        return jsonify({"error": f"Step 1 error: {e}"}), 500


def generate_shapes(whiteboard: Whiteboard, step1_response, receive_dto: ReceiveDTO):
    openai_temperature_str = os.getenv("OPENAI_TEMPERATURE")
    if not openai_temperature_str:
        raise ValueError("OPENAI_TEMPERATURE must be set in .env file")
    openai_temperature = float(openai_temperature_str)

    try:
        logger.info(f"[STEP2] Update description: {step1_response.update_description}")

        # Get shapes optimization section with actual templates
        logger.info("[STEP2] Generating shapes prompt section with templates")

        step2_content = [
            {
                "type": "text",
                "text": step2_build(whiteboard, step1_response.update_description),
            }
        ]

        openai_model_step2 = os.getenv("OPENAI_MODEL_STEP2")
        if not openai_model_step2:
            raise ValueError("OPENAI_MODEL_STEP2 must be set in .env file")
        logger.info(f"[STEP2] Sending request to OpenAI model: {openai_model_step2}")
        logger.info(
            f"[STEP2] Prompt length: {sum(len(str(c.get('text', ''))) for c in step2_content if isinstance(c, dict))} chars"
        )

        save_openai_prompt("STEP2", step2_content)

        step2_resp = client.chat.completions.create(
            model=openai_model_step2,
            messages=[{"role": "user", "content": step2_content}],
            temperature=openai_temperature,
        )
        step2_str = step2_resp.choices[0].message.content.strip()
        logger.info(f"[STEP2] Received response from OpenAI ({len(step2_str)} chars)")
        step2_json = json.loads(step2_str)
        return step2_json

    except Exception as e:
        print(f"Step 2 error", e)


@app.route("/draw", methods=["POST"])
def draw():
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("Received new request at /draw endpoint")
    logger.info("=" * 80)

    try:
        data = request.get_json()  # Get the payload from the end user
        logger.info("Payload received, starting processing")

        # TrustCall: Validate webhook payload
        is_valid, validation_error = validate_webhook_payload(data)
        if not is_valid:
            return jsonify({"error": f"Invalid payload: {validation_error}"}), 400

        receive_dto = ReceiveDTO(
            user_message=data.get("message"),  # Latest message that triggered the AI
            history=data.get("history"),  # The complete conversation history
            session_id=data.get(
                "session_id"
            ),  # Session ID (which is the same as the whiteboard ID)
            receiving_url=data.get(
                "receiving_url"
            ),  # For now, parse student ID and AI ID from URL
            topic=data.get(
                "topic"
            ),  # Topic, which will be useful in case we need to build a hard-coded AI per topic
        )
        whiteboard_state = data.get("whiteboard_state") or {}
        whiteboard = Whiteboard.model_validate(whiteboard_state)
        final_whiteboard_dict = whiteboard.to_excalidraw_dict()
        intent_timer = time.time()
        step1_response = describe_user_intent(whiteboard, receive_dto)
        logger.info(f"Total time to assume describe user intent: {time.time() - intent_timer}s")

        if step1_response.should_update:
            logger.info("\n")
            logger.info("Board should be updated!")
            logger.info("\n")
            shape_timer = time.time()
            patches = generate_shapes(
                whiteboard=whiteboard,
                receive_dto=receive_dto,
                step1_response=step1_response,
            )
            logger.info(f"Total time to generate shapes: {time.time() - shape_timer}s")
            whiteboard.apply_patches_from_ai(patches)
            final_whiteboard_dict = whiteboard.to_excalidraw_dict()

            response_json = json.dumps(
                {
                    "text": step1_response.text,
                    "appState": final_whiteboard_dict["appState"],
                    "elements": final_whiteboard_dict["elements"],
                }
            )

            logger.info(f"response json: {response_json}")

            requests.post(
                receive_dto.receiving_url,
                json={"response": response_json},
                headers={"Content-Type": "application/json"},
            )
            logger.info(f"Total time: {time.time() - start_time}s")
            return jsonify({"status": "sent", "reply": response_json}), 200

        else:
            if whiteboard:
                response_json = json.dumps(
                    {
                        "text": step1_response.text,
                        "appState": final_whiteboard_dict["appState"],
                        "elements": final_whiteboard_dict["elements"],
                    }
                )

                input_untouched_whiteboard = {
                    "appState": final_whiteboard_dict["appState"],
                    "elements": final_whiteboard_dict["elements"],
                }
            else:
                response_json = json.dumps(
                    {
                        "text": step1_response.text,
                        "appState": {},
                        "elements": {},
                    }
                )

                input_untouched_whiteboard = {
                    "appState": {},
                    "elements": {},
                }

            # Try to get preview image, but don't fail if it errors
            try:
                get_whiteboard_image_preview(
                    root_url=receive_dto.get_root_url_with_scheme(),
                    whiteboard_json=input_untouched_whiteboard,
                    save_name="no-draw-vision.jpg",
                )
            except Exception as e:
                logger.warning(f"[STEP2] Failed to get whiteboard preview image: {e}")
                # Continue without preview image

            print("No draw response complete!")

            with open("output.json", "w") as f:
                json.dump(input_untouched_whiteboard, f, indent=4)
            try:
                print("RECEIVING URL:", receive_dto.receiving_url, flush=True)
                requests.post(
                    receive_dto.receiving_url,
                    json={"response": response_json},
                    headers={"Content-Type": "application/json"},
                )
            except Exception as e:
                logger.error("Exception found: ", e)
                raise

        logger.info(f"response json: {response_json}")
        logger.info(f"Total time: {time.time() - start_time}s")
        return jsonify({"status": "sent", "reply": response_json}), 200

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        logger.info(f"Total time: {time.time() - start_time}s")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route("/receive2", methods=["POST"])
def receive2():
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("[WEBHOOK] Received new request at /receive endpoint")
    logger.info("=" * 80)

    log_trustcall_event(
        "webhook_call",
        {
            "endpoint": "/receive",
            "method": "POST",
            "timestamp": datetime.now().isoformat(),
        },
        success=True,
    )

    try:
        data = request.get_json()  # Get the payload from the end user
        logger.info("[WEBHOOK] Payload received, starting processing")

        # TrustCall: Validate webhook payload
        is_valid, validation_error = validate_webhook_payload(data)
        if not is_valid:
            log_trustcall_event(
                "payload_validation_error",
                {
                    "error": validation_error,
                    "payload_keys": list(data.keys()) if data else [],
                },
                success=False,
            )
            return jsonify({"error": f"Invalid payload: {validation_error}"}), 400

        user_message = data.get("message")  # Latest message that triggered the AI
        history = data.get("history")  # The complete conversation history
        whiteboard_state = data.get("whiteboard_state")  # The whiteboard state in JSON

        session_id = data.get(
            "session_id"
        )  # Session ID (which is the same as the whiteboard ID)
        receiving_url = data.get(
            "receiving_url"
        )  # For now, parse student ID and AI ID from URL
        topic = data.get(
            "topic"
        )  # Topic, which will be useful in case we need to build a hard-coded AI per topic

        logger.info(f"[WEBHOOK] Session ID: {session_id}")
        logger.info(f"[WEBHOOK] Topic: {topic}")
        logger.info(
            f"[WEBHOOK] User message: {user_message[:100] if user_message else 'None'}..."
        )
        logger.info(
            f"[WEBHOOK] History length: {len(history) if history else 0} messages"
        )
        logger.info(
            f"[WEBHOOK] Whiteboard has {len(whiteboard_state['elements']) if whiteboard_state else 0} elements"
        )

        # Convert whiteboard to sympy JSON and store in DB
        sympy_json = None
        sympy_objects = []
        try:
            if whiteboard_state:
                sympy_json = convert_whiteboard_to_sympy_json(whiteboard_state)
                logger.info(
                    f"[SYMPY] Converted whiteboard to sympy JSON: {sympy_json.get('metadata', {}).get('total_shapes', 0)} shapes"
                )

                if sympy_json:
                    sympy_objects = sympy_json_to_objects(sympy_json)
                    logger.info(
                        f"[SYMPY] Loaded {len(sympy_objects)} sympy objects for operations"
                    )
        except Exception as e:
            logger.warning(f"[SYMPY] Error converting whiteboard to sympy JSON: {e}")

        # Operation detection will be done by LLM in Step 1
        operation = None
        operation_result = None

        # TODO: Remove this once Musa adds the AI_ID and Student_ID as payload attributes
        parsed_url = urlparse(receiving_url)
        query_params = parse_qs(parsed_url.query)
        root_url_with_scheme = f"{parsed_url.scheme}://{parsed_url.netloc}"  # Useful for calling the other API functions
        ai_id = query_params["ai_tutor_id"][0]
        try:
            student_id = list(
                set([x["user_id"] for x in history if x["user_id"] != ai_id])
            )[0]
        except IndexError:
            student_id = None

        diarized_history = diarize_history(history, student_id=student_id, ai_id=ai_id)

        # TODO: Consider whether to pass history timestamps in context?
        history_context = "\n".join(
            [
                x["user_id"] + ": " + x["text_message"]
                for x in diarized_history[-LOOKBACK_LEN:-1]
            ]
        )
        print(history_context)

        # ERROR CHECKS
        if not receiving_url:
            log_trustcall_event(
                "webhook_call", {"error": "receiving_url is required"}, success=False
            )
            return jsonify({"error": "receiving_url is required"}), 400

        if not any([user_message, whiteboard_state]):
            log_trustcall_event(
                "webhook_call",
                {"error": "message or whiteboard content is required"},
                success=False,
            )
            return jsonify({"error": "message or whiteboard content is required"}), 400

        # INPUT WHITEBOARD CONVERSION
        input_whiteboard_image = "input.jpg"
        try:
            input_whiteboard_image = "input.jpg"
            logger.info(f"[WEBHOOK] root_url_with_scheme: {root_url_with_scheme}")
            logger.info(f"[WEBHOOK] receiving_url: {receiving_url}")
            logger.info(f"[WEBHOOK] About to call get_whiteboard_image_preview")
            get_whiteboard_image_preview(
                root_url_with_scheme, whiteboard_state, input_whiteboard_image
            )
            input_wb_base64 = encode_image_to_base64(input_whiteboard_image)
            logger.info("[WEBHOOK] Whiteboard preview image captured successfully")
        except Exception as e:
            logger.warning(f"[WEBHOOK] Could not get whiteboard preview image: {e}")

        # STEP 1: Check if whiteboard change is needed
        sympy_json_section = ""

        if sympy_json and isinstance(sympy_json, dict):
            shapes_count = len(sympy_json.get("shapes", []))
            metadata = sympy_json.get("metadata", {})
            conversion_errors = metadata.get("conversion_errors", [])
            llm_required_shapes = metadata.get("llm_required_shapes", [])

            # Build information about shapes that couldn't be converted
            unconverted_shapes_info = ""
            if llm_required_shapes:
                unconverted_shapes_info = f"""
        
        SHAPES THAT REQUIRE LLM ANALYSIS (Could not be converted to SymPy):
        The following {len(llm_required_shapes)} shape(s) on the whiteboard could not be automatically converted to geometric objects:
        {json.dumps(llm_required_shapes, indent=2)}
        
        These shapes may be:
        - Complex or irregular freedraw shapes
        - Random shapes that don't form recognizable geometry
        - Shapes that are too abstract to analyze mathematically
        
        CRITICAL: If the student asks ANY question about these shapes (e.g., "what is the area?", "is this a circle?", "what shape is this?", "calculate the perimeter"):
        - These shapes CANNOT be analyzed using SymPy mathematical operations
        - You MUST handle the query yourself using visual analysis from the whiteboard image
        - Analyze the shape(s) visually and provide helpful, educational responses
        - If the shape is too random/abstract, politely explain the limitation and suggest drawing recognizable geometric shapes
        - Always respond in a friendly, helpful manner - never say "I can't" or "error"
        - For mathematical operations (area, perimeter, distance, etc.), provide your best estimate or explanation based on visual analysis
        """

            conversion_errors_info = ""
            if conversion_errors:
                conversion_errors_info = f"""
        
        CONVERSION NOTES:
        Some shapes on the whiteboard could not be converted to SymPy format:
        {json.dumps(conversion_errors[:5], indent=2)}  # Show first 5 errors
        
        These shapes are still visible on the whiteboard and can be analyzed visually.
        """

            if shapes_count > 0:
                sympy_json_section = f"""
        
        GEOMETRIC SHAPES INFORMATION (SymPy JSON):
        The whiteboard contains {shapes_count} geometric shape(s) that have been converted to SymPy format:
        {json.dumps(sympy_json.get("shapes", [])[:10], indent=2)}  # Show first 10 shapes
        
        This information can help you understand the geometric properties of the shapes on the whiteboard.
        Use this data to provide accurate mathematical answers when needed.
        {unconverted_shapes_info}
        {conversion_errors_info}
        
        AVAILABLE MATHEMATICAL OPERATIONS:
        If the student is asking about relationships or properties of these shapes, detect the operation type:
        - "intersection": Finding where shapes intersect/cross (e.g., "where do these lines meet?", "find the intersection")
        - "parallel": Checking if lines are parallel (e.g., "are these lines parallel?", "do these lines run parallel?")
        - "perpendicular": Checking if lines are perpendicular (e.g., "are these lines perpendicular?", "right angle")
        - "distance": Calculating distance between points/shapes (e.g., "what is the distance?", "how far apart?")
        - "area": Calculating area of a shape (e.g., "what is the area?", "find the area")
        - "perimeter": Calculating perimeter/circumference (e.g., "what is the perimeter?", "circumference")
        - "angle": Finding angle between lines (e.g., "what is the angle?", "degrees")
        - "tangent": Checking if shapes are tangent (e.g., "are these tangent?", "touches")
        - "contains": Checking if a shape contains a point (e.g., "is this point inside?", "contains")
        - "midpoint": Finding midpoint (e.g., "what is the midpoint?", "middle point")
        
        Set "mathematical_operation" to the appropriate operation name, or null if not a mathematical operation query.
        """
            elif llm_required_shapes or conversion_errors:
                # No converted shapes, but there are shapes that need LLM analysis
                sympy_json_section = f"""
        
        WHITEBOARD SHAPES INFORMATION:
        The whiteboard contains shapes that could not be automatically converted to geometric objects.
        {unconverted_shapes_info}
        {conversion_errors_info}
        
        IMPORTANT: These shapes are still visible on the whiteboard. You can:
        - Analyze them visually from the whiteboard image
        - Provide helpful responses about what you see
        - If shapes are too random/abstract, politely explain and suggest drawing recognizable shapes
        - Always be helpful and educational - never say "I can't process this" or "error"
        """
            else:
                sympy_json_section = ""

        # sympy_result_section will be built after Step 1 (when operation_result is available)
        sympy_result_section = ""

        PROMPT_SCAFFOLD = build_main_scaffold_prompt(
            topic=topic,
            history_context=history_context,
            user_message=user_message,
            whiteboard_state=(
                json.dumps(whiteboard_state)
                if isinstance(whiteboard_state, dict)
                else str(whiteboard_state)
            ),
            sympy_json_section=sympy_json_section,
            sympy_result_section=sympy_result_section,
        )
        VISION_SCAFFOLD = build_vision_scaffold(input_wb_base64)

        # Check if this is a calculation-only query (distance, area, etc. that succeeded)
        calculation_only = False
        if operation_result and operation_result.get("success") and operation:
            # For distance, area, parallel checks - if user didn't explicitly ask to draw, just answer
            calculation_operations = [
                "distance",
                "area",
                "parallel",
                "perpendicular",
                "angle",
            ]
            if operation in calculation_operations:
                user_msg_lower = (user_message or "").lower()
                explicit_draw_keywords = [
                    "draw",
                    "add",
                    "create",
                    "show",
                    "put",
                    "make",
                    "build",
                    "mark",
                    "label",
                ]
                has_explicit_draw_request = any(
                    keyword in user_msg_lower for keyword in explicit_draw_keywords
                )
                if not has_explicit_draw_request:
                    calculation_only = True
                    logger.info(
                        f"[STEP1] Calculation-only query detected for operation: {operation}"
                    )

        calculation_hint = ""
        if calculation_only:
            calculation_hint = build_calculation_hint(operation, operation_result)

        STEP1_PROMPT_START = build_step1_decision_prompt_start(
            prompt_scaffold=PROMPT_SCAFFOLD, calculation_hint=calculation_hint
        )

        STEP1_PROMPT_END = build_step1_decision_prompt_end()

        step1_content = (
            [{"type": "text", "text": STEP1_PROMPT_START}]
            + VISION_SCAFFOLD
            + [{"type": "text", "text": STEP1_PROMPT_END}]
        )
        # WE CAN NOW RUN STEP 1
        # Load OpenAI configuration (used in both try and else blocks)
        openai_model_step1 = os.getenv("OPENAI_MODEL_STEP1")
        if not openai_model_step1:
            raise ValueError("OPENAI_MODEL_STEP1 must be set in .env file")
        openai_temperature_str = os.getenv("OPENAI_TEMPERATURE")
        if not openai_temperature_str:
            raise ValueError("OPENAI_TEMPERATURE must be set in .env file")
        openai_temperature = float(openai_temperature_str)

        try:
            # TrustCall: Monitor AI API call
            log_trustcall_event(
                "ai_api_call",
                {
                    "model": openai_model_step1,
                    "step": "step1_decision",
                    "session_id": session_id,
                },
                success=True,
            )

            # log_openai_prompt(logger, "STEP1", step1_content, max_chars=20000)

            step1_resp = client.chat.completions.create(
                model=openai_model_step1,
                messages=[{"role": "user", "content": step1_content}],
                temperature=openai_temperature,
            )
            step1_str = step1_resp.choices[0].message.content.strip()
            print("Step 1 response:", step1_str)
            step1_json = json.loads(step1_str)
            # Parse the outputs
            draw_on_whiteboard = bool(step1_json.get("update_decision", False))
            what_to_draw = step1_json.get("update_description", "")

            # Get mathematical operation from LLM decision
            operation = step1_json.get("mathematical_operation")
            operation_result = None  # Initialize to ensure it's always defined
            if operation and operation.lower() in ["null", "none", ""]:
                operation = None
            elif operation:
                operation = operation.lower().strip()
                logger.info(f"[SYMPY] LLM detected operation: {operation}")

                # Check if there are unconvertible shapes that require LLM handling
                llm_required_shapes = (
                    sympy_json.get("metadata", {}).get("llm_required_shapes", [])
                    if sympy_json
                    else []
                )

                # If user is asking about unconvertible shapes, skip SymPy and use LLM
                if llm_required_shapes:
                    logger.info(
                        f"[SYMPY] Found {len(llm_required_shapes)} unconvertible shape(s) - using LLM for operation '{operation}'"
                    )
                    operation_result = {
                        "success": False,
                        "operation": operation,
                        "use_llm": True,
                        "message": f"Operation '{operation}' requested on unconvertible freedraw shape(s) - using LLM analysis",
                    }
                elif sympy_objects:
                    logger.info(
                        f"[SYMPY] Attempting operation '{operation}' with {len(sympy_objects)} sympy objects"
                    )
                    operation_result = perform_operation(operation, sympy_objects)
                    if operation_result.get("success"):
                        logger.info(
                            f"[SYMPY] Operation '{operation}' succeeded: {operation_result.get('message', '')}"
                        )
                        logger.info(
                            f"[SYMPY] Result: {operation_result.get('result', 'N/A')}"
                        )
                    elif operation_result.get("use_llm"):
                        logger.info(
                            f"[SYMPY] Operation '{operation}' not in sympy, will use LLM"
                        )
                    else:
                        logger.warning(
                            f"[SYMPY] Operation '{operation}' failed: {operation_result.get('message', '')}"
                        )
                else:
                    logger.warning(
                        f"[SYMPY] Operation '{operation}' detected but no sympy objects available"
                    )
                    operation_result = {
                        "success": False,
                        "operation": operation,
                        "use_llm": True,
                        "message": f"No SymPy objects available for operation '{operation}' - using LLM",
                    }

            # Fallback check: If Step 1 says NO DRAW but user explicitly requested drawing, override it
            if not draw_on_whiteboard:
                explicit_draw_keywords = [
                    "draw",
                    "add",
                    "create",
                    "show",
                    "put",
                    "make",
                    "build",
                    "generate",
                ]
                user_msg_lower = user_message.lower() if user_message else ""
                has_explicit_request = any(
                    keyword in user_msg_lower for keyword in explicit_draw_keywords
                )

                if has_explicit_request:
                    logger.warning(
                        f"[STEP1] Override: Step 1 returned NO DRAW but user message contains explicit drawing request"
                    )
                    logger.warning(f"[STEP1] User message: '{user_message[:100]}'")
                    draw_on_whiteboard = True
                    if not what_to_draw:
                        what_to_draw = f"Add the requested shape/object from the user's message: {user_message}"
                    logger.info(
                        f"[STEP1] Overridden to DRAW with description: {what_to_draw[:200]}..."
                    )

            logger.info(
                f"[STEP1] Decision: {'DRAW' if draw_on_whiteboard else 'NO DRAW'}"
            )
            logger.info(f"[STEP1] Update description: {what_to_draw[:200]}...")

            # Build sympy_result_section after Step 1 (now that we have operation_result)
            sympy_result_section = ""
            if operation_result and operation_result.get("success"):
                sympy_result_section = build_sympy_result_section_success(
                    operation, operation_result
                )
            elif operation and operation_result and operation_result.get("use_llm"):
                # Check if this is due to unconvertible shapes
                llm_required_shapes = (
                    sympy_json.get("metadata", {}).get("llm_required_shapes", [])
                    if sympy_json
                    else []
                )
                sympy_result_section = build_sympy_result_section_llm_fallback(
                    operation, llm_required_shapes
                )

            # Rebuild PROMPT_SCAFFOLD with updated sympy_result_section
            PROMPT_SCAFFOLD = build_main_scaffold_prompt(
                topic=topic,
                history_context=history_context,
                user_message=user_message,
                whiteboard_state=(
                    json.dumps(whiteboard_state)
                    if isinstance(whiteboard_state, dict)
                    else str(whiteboard_state)
                ),
                sympy_json_section=sympy_json_section,
                sympy_result_section=sympy_result_section,
            )

            # TrustCall: Log successful AI response
            log_trustcall_event(
                "ai_api_call",
                {
                    "model": openai_model_step1,
                    "step": "step1_decision",
                    "response_length": len(step1_str),
                    "decision": draw_on_whiteboard,
                },
                success=True,
            )

        except Exception as e:
            print("Step 1 error:", e)
            log_trustcall_event(
                "ai_api_call",
                {
                    "model": openai_model_step1,
                    "step": "step1_decision",
                    "error": str(e),
                },
                success=False,
            )
            return jsonify({"error": f"Step 1 error: {e}"}), 500

        if draw_on_whiteboard:
            logger.info(
                "[WEBHOOK] Whiteboard update needed - proceeding to Step 1.5 (Shape Identification)"
            )

            # STEP 1.5: Identify exact shape needed and check if template exists
            shape_template = None
            shape_name = None
            use_template = False

            try:
                logger.info(
                    "[STEP1.5] Identifying exact shape needed from user request"
                )

                # Get list of available shapes for the prompt
                shapes_info = get_available_shapes(use_cache=True)
                available_shape_names = list(shapes_info.keys())

                STEP1_5_PROMPT = build_step1_5_shape_identification_prompt(
                    user_message=user_message,
                    update_description=what_to_draw,
                    available_shape_names=available_shape_names,
                )

                # log_openai_prompt(logger, "STEP1", STEP1_5_PROMPT, max_chars=4000)

                step1_5_response = client.chat.completions.create(
                    model=openai_model_step1,
                    messages=[{"role": "user", "content": STEP1_5_PROMPT}],
                    temperature=0.3,
                )

                step1_5_str = step1_5_response.choices[0].message.content.strip()
                step1_5_json = json.loads(step1_5_str)
                shape_name = step1_5_json.get("shape_name", "").lower().strip()
                shape_exists = step1_5_json.get("shape_exists", False)
                position_hint = step1_5_json.get("position_hint", "")

                logger.info(
                    f"[STEP1.5] Identified shape: '{shape_name}', exists: {shape_exists}, confidence: {step1_5_json.get('confidence', 'unknown')}"
                )

                if (
                    shape_exists
                    and shape_name
                    and shape_name != "custom"
                    and shape_name != "none"
                ):
                    shape_template = load_shape_template(shape_name)
                    if shape_template and shape_template.get("elements"):
                        use_template = True
                        logger.info(
                            f"[STEP1.5] ✅ Template found for '{shape_name}' with {len(shape_template['elements'])} elements"
                        )
                        logger.info(f"[STEP1.5] Position hint: {position_hint}")
                    else:
                        logger.warning(
                            f"[STEP1.5] ⚠️ Shape '{shape_name}' was identified but template not found, will generate from scratch"
                        )
                        use_template = False
                else:
                    logger.info(
                        f"[STEP1.5] Shape '{shape_name}' not in library or is custom, will generate from scratch"
                    )
                    use_template = False

            except Exception as e:
                logger.warning(
                    f"[STEP1.5] Error in shape identification: {e}, will proceed with normal flow"
                )
                use_template = False
                import traceback

                logger.debug(f"[STEP1.5] Traceback: {traceback.format_exc()}")

            use_template = False
            shape_template = None

            if use_template and shape_template:
                logger.info(
                    "[STEP1.5] Using pre-built template - skipping LLM generation"
                )

                existing_elements = (
                    whiteboard_state.get("elements", [])
                    if isinstance(whiteboard_state, dict)
                    else []
                )

                # Create new elements from template
                # Follow the same approach as Step 2: preserve template's original positions
                # The template already has positions - we'll use them as-is (same as how Step 2 LLM would use template positions)
                # Only apply minimal offset if needed to avoid overlap with existing elements
                new_elements = []
                template_elements = shape_template["elements"]

                # Calculate simple offset only if template would overlap with existing elements
                offset_x = 0
                offset_y = 0
                if existing_elements and template_elements:
                    valid_existing = [
                        e for e in existing_elements if isinstance(e, dict)
                    ]
                    if valid_existing:
                        # Find rightmost edge of existing elements
                        max_existing_x = max(
                            (e.get("x", 0) + e.get("width", 0)) for e in valid_existing
                        )
                        # Find leftmost edge of template
                        min_template_x = min(
                            e.get("x", 0)
                            for e in template_elements
                            if isinstance(e, dict)
                        )
                        # Simple check: if template starts before existing elements end + padding, shift it right
                        padding = 100
                        if min_template_x < max_existing_x + padding:
                            offset_x = max_existing_x + padding - min_template_x
                            logger.info(
                                f"[STEP1.5] Applying horizontal offset {offset_x:.1f} to avoid overlap with existing elements"
                            )

                for template_elem in template_elements:
                    new_elem = template_elem.copy()

                    # Generate new IDs
                    new_elem["id"] = str(uuid.uuid4()).replace("-", "")[:20]
                    new_elem["versionNonce"] = random.randint(100000000, 999999999)
                    new_elem["updated"] = int(time.time() * 1000)

                    # Ensure required fields
                    if "version" not in new_elem:
                        new_elem["version"] = 1
                    if "seed" not in new_elem:
                        new_elem["seed"] = random.randint(1000000, 9999999)
                    if "index" not in new_elem:
                        new_elem["index"] = f"a{random.randint(1, 1000)}"
                    if "opacity" not in new_elem:
                        new_elem["opacity"] = 100
                    if "locked" not in new_elem:
                        new_elem["locked"] = False
                    if "isDeleted" not in new_elem:
                        new_elem["isDeleted"] = False
                    if "groupIds" not in new_elem:
                        new_elem["groupIds"] = []
                    if "boundElements" not in new_elem:
                        new_elem["boundElements"] = []
                    if "frameId" not in new_elem:
                        new_elem["frameId"] = None
                    if "link" not in new_elem:
                        new_elem["link"] = None
                    if "angle" not in new_elem:
                        new_elem["angle"] = 0

                    # Apply offset only if needed (preserves template's relative positions)
                    if offset_x != 0 or offset_y != 0:
                        original_x = new_elem.get("x", 0)
                        original_y = new_elem.get("y", 0)
                        new_elem["x"] = original_x + offset_x
                        new_elem["y"] = original_y + offset_y
                        logger.debug(
                            f"[STEP1.5] Applied offset: ({original_x:.1f}, {original_y:.1f}) -> ({new_elem['x']:.1f}, {new_elem['y']:.1f})"
                        )
                    # Otherwise, keep template's original positions (same as Step 2 - LLM would preserve these)

                    new_elements.append(new_elem)

                all_elements = existing_elements + new_elements
                wb_obj = {
                    "appState": (
                        whiteboard_state.get("appState", {})
                        if isinstance(whiteboard_state, dict)
                        else {}
                    ),
                    "elements": all_elements,
                }

                logger.info(f"[STEP1.5] Generating chat message for student")
                shape_display_name = (
                    shape_name.replace("-", " ").replace("_", " ").title()
                )

                intersection_analysis_text = ""
                try:
                    logger.info(
                        f"[STEP1.5] Checking for intersection analysis needed (user message: '{user_message[:50]}...')"
                    )
                    intersection_section = get_intersection_analysis_prompt_section(
                        whiteboard_state,
                        user_message,
                        check_specific_shape=None,
                        openai_client=client,
                    )
                    if intersection_section:
                        if "GEOMETRIC ANALYSIS" in intersection_section:
                            parts = intersection_section.split("IMPORTANT GUIDELINES")
                            if parts:
                                intersection_analysis_text = parts[0].strip()
                                logger.info(
                                    f"[STEP1.5] ✅ Intersection analysis available: {len(intersection_analysis_text)} chars"
                                )
                                logger.debug(
                                    f"[STEP1.5] Analysis preview: {intersection_analysis_text[:200]}..."
                                )
                            else:
                                intersection_analysis_text = intersection_section
                                logger.info(
                                    f"[STEP1.5] ✅ Using full intersection section: {len(intersection_analysis_text)} chars"
                                )
                        else:
                            intersection_analysis_text = intersection_section
                    else:
                        logger.info(
                            f"[STEP1.5] No intersection analysis generated (may not be needed)"
                        )
                except Exception as e:
                    logger.warning(
                        f"[STEP1.5] Error getting intersection analysis: {e}"
                    )
                    import traceback

                    logger.debug(f"[STEP1.5] Traceback: {traceback.format_exc()}")

                step1_5_chat_prompt = build_step1_5_chat_response_prompt(
                    prompt_scaffold=PROMPT_SCAFFOLD,
                    sympy_result_section=sympy_result_section,
                    user_message=user_message,
                    shape_display_name=shape_display_name,
                    topic=topic,
                    intersection_analysis_text=intersection_analysis_text,
                )

                try:
                    step1_5_chat_response = client.chat.completions.create(
                        model=openai_model_step1,
                        messages=[{"role": "user", "content": step1_5_chat_prompt}],
                        temperature=openai_temperature,
                    )
                    step1_5_chat_str = step1_5_chat_response.choices[
                        0
                    ].message.content.strip()
                    logger.debug(
                        f"[STEP1.5] Raw chat response: {step1_5_chat_str[:200]}..."
                    )

                    cleaned_response = step1_5_chat_str
                    if cleaned_response.startswith("```"):
                        # Remove markdown code blocks
                        lines = cleaned_response.split("\n")
                        cleaned_response = (
                            "\n".join(lines[1:-1])
                            if len(lines) > 2
                            else cleaned_response
                        )
                        cleaned_response = cleaned_response.strip()

                    step1_5_chat_json = json.loads(cleaned_response)
                    ai_response = step1_5_chat_json.get("text", "")

                    # Validate that we got an actual message, not placeholder text
                    placeholder_phrases = [
                        "A friendly, instructional reply",
                        "Your actual personalized message here",
                        "be specific and engaging",
                    ]
                    if not ai_response or any(
                        phrase in ai_response for phrase in placeholder_phrases
                    ):
                        logger.warning(
                            f"[STEP1.5] Received placeholder text, generating fallback message"
                        )
                        ai_response = f"Great! I've added a {shape_display_name} shape to the whiteboard as you requested. This {shape_display_name.lower()} can help us explore {topic} together. Would you like me to add anything else or explain more about this shape?"
                    else:
                        logger.info(
                            f"[STEP1.5] Generated chat message: {ai_response[:100]}..."
                        )
                except Exception as e:
                    logger.warning(
                        f"[STEP1.5] Error generating chat message: {e}, using fallback message"
                    )
                    ai_response = f"I've added a {shape_display_name} shape to the whiteboard as you requested."

                logger.info(
                    f"[STEP1.5] ✅ Successfully added template shape. Total elements: {len(all_elements)}"
                )

                response_json = json.dumps(
                    {
                        "text": ai_response,
                        "appState": wb_obj.get("appState", {}),
                        "elements": wb_obj.get("elements", []),
                    }
                )

                logger.info(
                    f"[STEP1.5] Response JSON length: {len(response_json)} chars"
                )
                logger.info(
                    f"[STEP1.5] Elements in response: {len(wb_obj.get('elements', []))}"
                )

                try:
                    logger.info(f"[STEP1.5] Sending response to: {receiving_url}")
                    response = requests.post(
                        receiving_url,
                        json={"response": response_json},
                        headers={"Content-Type": "application/json"},
                    )
                    logger.info(
                        f"[STEP1.5] Response sent with status: {response.status_code}"
                    )

                    log_trustcall_event(
                        "webhook_call",
                        {
                            "step": "send_response",
                            "status_code": response.status_code,
                            "whiteboard_updated": True,
                            "success": True,
                        },
                        success=True,
                    )
                except Exception as e:
                    logger.error(f"[STEP1.5] Error sending response: {e}")
                    log_trustcall_event(
                        "webhook_call",
                        {"step": "send_response", "error": str(e), "success": False},
                        success=False,
                    )
                    raise

                total_time = time.time() - start_time
                log_trustcall_event(
                    "webhook_call",
                    {
                        "step": "complete",
                        "total_time": total_time,
                        "whiteboard_updated": True,
                        "success": True,
                    },
                    success=True,
                )

                return jsonify({"status": "sent", "reply": response_json}), 200

            # If no template, proceed with normal LLM generation flow
            logger.info(
                "[WEBHOOK] No template found or template not usable - proceeding to Step 2 (LLM generation)"
            )
            max_attempts_str = os.getenv("MAX_ATTEMPTS")
            if not max_attempts_str:
                raise ValueError("MAX_ATTEMPTS must be set in .env file")
            max_attempts = int(max_attempts_str)  # Set up max attempts
            logger.info(f"[WEBHOOK] Max attempts configured: {max_attempts}")
            attempt_counter = 0  # Attempt counter
            best_attempt = ""  # String describing the best attempt so far
            best_score = -1  # A max counter to keep track of score quality
            best_name = "best.jpg"
            best_b64 = None
            best_whiteboard = whiteboard_state
            best_response = ""

            while attempt_counter < max_attempts:
                attempt_counter += 1
                print("Attempt " + str(attempt_counter))
                try:
                    logger.info(
                        f"[STEP2] Starting whiteboard generation attempt {attempt_counter}"
                    )
                    logger.info(f"[STEP2] Update description: {what_to_draw[:200]}...")

                    step2_prompt_start = build_step2_generation_prompt_start(
                        prompt_scaffold=PROMPT_SCAFFOLD,
                        sympy_result_section=sympy_result_section,
                        update_description=what_to_draw,
                        best_attempt=best_attempt,
                    )
                    # Get shapes optimization section with actual templates
                    logger.info(
                        "[STEP2] Generating shapes prompt section with templates"
                    )
                    shapes_section = get_shapes_prompt_section(
                        user_message, what_to_draw
                    )
                    if shapes_section:
                        logger.info(
                            f"[STEP2] Shapes section generated ({len(shapes_section)} chars)"
                        )
                    else:
                        logger.warning("[STEP2] No shapes section generated")

                    # Get intersection analysis section for geometric relationships
                    logger.info("[STEP2] Generating intersection analysis section")
                    intersection_section = ""
                    try:
                        intersection_section = get_intersection_analysis_prompt_section(
                            whiteboard_state,
                            user_message,
                            check_specific_shape=None,
                            openai_client=client,  # Pass OpenAI client for LLM relationship identification
                        )
                        if intersection_section:
                            logger.info(
                                f"[STEP2] ✅ Intersection analysis section generated ({len(intersection_section)} chars)"
                            )
                            preview = intersection_section[:300].replace("\n", " ")
                            logger.debug(f"[STEP2] Analysis preview: {preview}...")
                        else:
                            logger.info(
                                "[STEP2] No intersection analysis needed (not relevant to current request)"
                            )
                    except Exception as e:
                        logger.warning(
                            f"[STEP2] Error generating intersection analysis: {e}"
                        )
                        import traceback

                        logger.debug(
                            f"[STEP2] Intersection analysis traceback: {traceback.format_exc()}"
                        )
                        intersection_section = ""  # Ensure it's set even on error

                    step2_prompt_end = build_step2_generation_prompt_end(
                        shapes_section=shapes_section,
                        intersection_section=intersection_section,
                    )
                    if best_b64:
                        step2_content = (
                            [{"type": "text", "text": step2_prompt_start}]
                            + VISION_SCAFFOLD
                            + [
                                {
                                    "type": "text",
                                    "text": "To help you further, here's how your best attempt currently appears: ",
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{best_b64}"
                                    },
                                },
                            ]
                            + [{"type": "text", "text": step2_prompt_end}]
                        )
                    else:
                        step2_content = (
                            [{"type": "text", "text": step2_prompt_start}]
                            + VISION_SCAFFOLD
                            + [{"type": "text", "text": step2_prompt_end}]
                        )

                    log_trustcall_event(
                        "whiteboard_generation",
                        {
                            "attempt": attempt_counter,
                            "session_id": session_id,
                            "description": what_to_draw,
                        },
                        success=True,
                    )

                    openai_model_step2 = os.getenv("OPENAI_MODEL_STEP2")
                    if not openai_model_step2:
                        raise ValueError("OPENAI_MODEL_STEP2 must be set in .env file")
                    logger.info(
                        f"[STEP2] Sending request to OpenAI model: {openai_model_step2}"
                    )
                    logger.info(
                        f"[STEP2] Prompt length: {sum(len(str(c.get('text', ''))) for c in step2_content if isinstance(c, dict))} chars"
                    )

                    # log_openai_prompt(logger, "STEP2", step2_content, max_chars=20000)
                    save_openai_prompt("STEP2", step2_content)

                    step2_resp = client.chat.completions.create(
                        model=openai_model_step2,
                        messages=[{"role": "user", "content": step2_content}],
                        temperature=openai_temperature,
                    )
                    step2_str = step2_resp.choices[0].message.content.strip()
                    logger.info(
                        f"[STEP2] Received response from OpenAI ({len(step2_str)} chars)"
                    )
                    step2_json = json.loads(step2_str)
                    logger.info(
                        f"[STEP2] Parsed JSON - elements count: {len(step2_json.get('elements', []))}"
                    )
                    appState = step2_json.get("appState")
                    elements_raw = step2_json.get("elements")
                    ai_response = step2_json.get("text", "")

                    logger.info(
                        f"[STEP2] Raw elements from LLM: {len(elements_raw) if isinstance(elements_raw, list) else 0}"
                    )

                    # Merge with existing whiteboard elements (keep existing, add/update new)
                    existing_elements = (
                        whiteboard_state.get("elements", [])
                        if isinstance(whiteboard_state, dict)
                        else []
                    )
                    logger.info(
                        f"[STEP2] Existing whiteboard elements: {len(existing_elements)}"
                    )

                    # Start with existing elements
                    elements = (
                        existing_elements.copy()
                        if isinstance(existing_elements, list)
                        else []
                    )

                    # Add/update elements from LLM response
                    if isinstance(elements_raw, list):
                        # Create a map of existing element IDs
                        existing_ids = {
                            elem.get("id")
                            for elem in elements
                            if isinstance(elem, dict) and "id" in elem
                        }

                        for new_elem in elements_raw:
                            if isinstance(new_elem, dict):
                                elem_id = new_elem.get("id")
                                if elem_id and elem_id in existing_ids:
                                    # Update existing element
                                    for i, existing_elem in enumerate(elements):
                                        if existing_elem.get("id") == elem_id:
                                            elements[i] = new_elem
                                            logger.debug(
                                                f"[STEP2] Updated existing element: {elem_id}"
                                            )
                                            break
                                else:
                                    # Add new element
                                    elements.append(new_elem)
                                    if elem_id:
                                        existing_ids.add(elem_id)
                                    logger.debug(
                                        f"[STEP2] Added new element: {elem_id or 'no-id'}"
                                    )

                    logger.info(
                        f"[STEP2] After merging with existing: {len(elements)} elements"
                    )

                    detected_shapes = detect_shapes_needed(user_message, what_to_draw)
                    logger.info(
                        f"[STEP2] Detected shapes for injection: {detected_shapes}"
                    )

                    if detected_shapes:
                        logger.info(
                            f"[STEP2] Injecting library shapes: {detected_shapes}"
                        )
                        logger.info(
                            f"[STEP2] Before injection - elements: {len(elements)}"
                        )
                        elements = inject_library_shapes(
                            elements, detected_shapes, user_message
                        )
                        logger.info(
                            f"[STEP2] After injection - elements: {len(elements)}"
                        )
                        logger.info(f"[STEP2] ✅ Library shapes successfully injected!")
                    else:
                        logger.info(
                            "[STEP2] No shapes detected, using LLM-generated elements as-is"
                        )

                    wb_obj = {
                        "appState": (
                            appState
                            if isinstance(appState, dict)
                            else (
                                whiteboard_state.get("appState", {})
                                if isinstance(whiteboard_state, dict)
                                else {}
                            )
                        ),
                        "elements": elements if isinstance(elements, list) else [],
                    }

                    logger.info(
                        f"[STEP2] Final whiteboard object - elements: {len(wb_obj['elements'])}"
                    )

                    best_whiteboard = wb_obj
                    best_response = ai_response
                    break

                    # old = "old.jpg"
                    # new_preview = "new_preview.jpg"

                    # try:
                    #     get_whiteboard_image_preview(
                    #         root_url=root_url_with_scheme,
                    #         whiteboard_json=whiteboard_state,
                    #         save_name=old,
                    #     )
                    #     log_trustcall_event(
                    #         "whiteboard_generation",
                    #         {
                    #             "step": "preview_old",
                    #             "attempt": attempt_counter,
                    #             "success": True,
                    #         },
                    #         success=True,
                    #     )
                    # except Exception as e:
                    #     log_trustcall_event(
                    #         "whiteboard_generation",
                    #         {
                    #             "step": "preview_old",
                    #             "attempt": attempt_counter,
                    #             "error": str(e),
                    #         },
                    #         success=False,
                    #     )
                    #
                    # try:
                    #     get_whiteboard_image_preview(
                    #         root_url=root_url_with_scheme,
                    #         whiteboard_json=wb_obj,
                    #         save_name=new_preview,
                    #     )
                    #     log_trustcall_event(
                    #         "whiteboard_generation",
                    #         {
                    #             "step": "preview_new",
                    #             "attempt": attempt_counter,
                    #             "success": True,
                    #         },
                    #         success=True,
                    #     )
                    # except Exception as e:
                    #     log_trustcall_event(
                    #         "whiteboard_generation",
                    #         {
                    #             "step": "preview_new",
                    #             "attempt": attempt_counter,
                    #             "error": str(e),
                    #         },
                    #         success=False,
                    #     )

                #     # WE CAN NOW ATTEMPT STEP 3
                #     best_score = -1
                #     old_image_base64 = encode_image_to_base64(old)
                #     new_image_base64 = encode_image_to_base64(new_preview)
                #
                #     openai_model_step3 = os.getenv("OPENAI_MODEL_STEP3")
                #     if not openai_model_step3:
                #         raise ValueError("OPENAI_MODEL_STEP3 must be set in .env file")
                #     step3_content = build_step3_comparison_prompt_with_images(
                #         prompt_scaffold=PROMPT_SCAFFOLD,
                #         update_description=what_to_draw,
                #         old_image_base64=old_image_base64,
                #         new_image_base64=new_image_base64
                #     )
                #
                #     log_openai_prompt(logger, "STEP3", step3_content, max_chars=20000)
                #
                #     step3_response = client.chat.completions.create(
                #         model=openai_model_step3,
                #         messages=[
                #             {
                #                 "role": "user",
                #                 "content": step3_content,
                #             }
                #         ],
                #     )
                #
                #     # print("STEP 3 RESPONSE")
                #     step3_content = clean_openai_response(
                #         step3_response.choices[0].message.content.strip()
                #     )  # For some reason getting it as JSON with backticks here but not anywhere else
                #     try:
                #         parsed_output = json.loads(
                #             step3_content
                #         )  # Read the OpenAI Step 3 check
                #         reliable = parsed_output.get("reliable")  # Check if it passes
                #         message = parsed_output.get("message")
                #         grade = int(parsed_output.get("grade"))
                #         print(
                #             f"Reliable: {reliable}, Message: {message}, Score: {grade}"
                #         )
                #
                #         if (
                #                 grade > best_score
                #         ):  # If current attempt is perceived as the best, save its image, code, and score
                #             # Assumption. Best whiteboard corresponds to best text, so text response is taken too.
                #             best_score = grade
                #             best_attempt = f"""
                #             Your best whiteboard attempt so far (Score '{best_score}'/10):
                #
                #             '{wb_obj}'
                #             """
                #             best_whiteboard = wb_obj
                #             best_response = ai_response
                #             get_whiteboard_image_preview(
                #                 root_url=root_url_with_scheme,
                #                 whiteboard_json=wb_obj,
                #                 save_name=best_name,
                #             )
                #             best_b64 = encode_image_to_base64(best_name)
                #
                #         if reliable:
                #             break  # No need to keep iterating. We're done
                #     except json.JSONDecodeError:
                #         print("Failed to parse Step 3 JSON response")
                #         print("Raw response:", step3_content)
                #
                except Exception as e:
                    print(f"Step 2 error on attempt {attempt_counter}:", e)

            response_json = json.dumps(
                {
                    "text": best_response,
                    "appState": best_whiteboard["appState"],
                    "elements": best_whiteboard["elements"],
                    # "end_session": True,
                }
            )

            logger.info(f"response json: {response_json}")

            # print("Steps 2 and 3 complete!")
            try:
                print("RECEIVING URL:", receiving_url, flush=True)
                response = requests.post(
                    receiving_url,
                    json={"response": response_json},
                    headers={"Content-Type": "application/json"},
                )
                log_trustcall_event(
                    "webhook_call",
                    {
                        "step": "send_response",
                        "status_code": response.status_code,
                        "success": True,
                    },
                    success=True,
                )
            except Exception as e:
                log_trustcall_event(
                    "webhook_call",
                    {"step": "send_response", "error": str(e), "success": False},
                    success=False,
                )
                raise

            total_time = time.time() - start_time
            log_trustcall_event(
                "webhook_call",
                {
                    "step": "complete",
                    "total_time": total_time,
                    "whiteboard_updated": True,
                    "success": True,
                },
                success=True,
            )

            return jsonify({"status": "sent", "reply": response_json}), 200
        else:
            # No drawing needed
            nodraw_step2_prompt = build_no_draw_response_prompt(PROMPT_SCAFFOLD)
            nd_step2_resp = client.chat.completions.create(
                model=openai_model_step1,
                messages=[{"role": "user", "content": nodraw_step2_prompt}],
                temperature=openai_temperature,
            )
            nd_step2_str = nd_step2_resp.choices[0].message.content.strip()
            print(f"Step 2 response (No draw):", nd_step2_str)

            # Clean JSON if wrapped in markdown code blocks
            cleaned_response = nd_step2_str
            if cleaned_response.startswith("```"):
                # Extract JSON from markdown code block
                parts = cleaned_response.split("```")
                if len(parts) >= 3:
                    # Find the JSON part (could be after "json" or just the content)
                    for part in parts:
                        part = part.strip()
                        if part.startswith("json"):
                            part = part[4:].strip()
                        if part.startswith("{") and part.endswith("}"):
                            cleaned_response = part
                            break

            try:
                nd_step2_json = json.loads(cleaned_response)
                nd_ai_response = nd_step2_json.get("text", "")
            except json.JSONDecodeError as e:
                logger.error(f"[STEP2] Failed to parse JSON response: {e}")
                logger.error(f"[STEP2] Response content: {nd_step2_str[:500]}")
                # Fallback: try to extract text from the response
                if '"text"' in nd_step2_str:
                    # Try to extract text value manually
                    text_match = re.search(r'"text"\s*:\s*"([^"]*)"', nd_step2_str)
                    if text_match:
                        nd_ai_response = text_match.group(1)
                    else:
                        # Last resort: use the whole response as text
                        nd_ai_response = nd_step2_str
                else:
                    nd_ai_response = nd_step2_str
                logger.warning(
                    f"[STEP2] Using fallback text extraction: {nd_ai_response[:100]}..."
                )

            # Safely access whiteboard_state
            app_state = whiteboard_state.get("appState") if whiteboard_state else {}
            elements = whiteboard_state.get("elements", []) if whiteboard_state else []

            response_json = json.dumps(
                {
                    "text": nd_ai_response,
                    "appState": app_state,
                    "elements": elements,
                    # "end_session": True,
                }
            )

            input_untouched_whiteboard = {
                "appState": app_state,
                "elements": elements,
            }

            # Try to get preview image, but don't fail if it errors
            try:
                get_whiteboard_image_preview(
                    root_url=root_url_with_scheme,
                    whiteboard_json=input_untouched_whiteboard,
                    save_name="no-draw-vision.jpg",
                )
            except Exception as e:
                logger.warning(f"[STEP2] Failed to get whiteboard preview image: {e}")
                # Continue without preview image

            print("No draw response complete!")

            with open("output.json", "w") as f:
                json.dump(input_untouched_whiteboard, f, indent=4)
            try:
                print("RECEIVING URL:", receiving_url, flush=True)
                response = requests.post(
                    receiving_url,
                    json={"response": response_json},
                    headers={"Content-Type": "application/json"},
                )
                log_trustcall_event(
                    "webhook_call",
                    {
                        "step": "send_response",
                        "status_code": response.status_code,
                        "whiteboard_updated": False,
                        "success": True,
                    },
                    success=True,
                )
            except Exception as e:
                log_trustcall_event(
                    "webhook_call",
                    {"step": "send_response", "error": str(e), "success": False},
                    success=False,
                )
                raise

            print("RESPONSE SENT")

            total_time = time.time() - start_time
            log_trustcall_event(
                "webhook_call",
                {
                    "step": "complete",
                    "total_time": total_time,
                    "whiteboard_updated": False,
                    "success": True,
                },
                success=True,
            )

            return jsonify({"status": "sent", "reply": response_json}), 200

    except Exception as e:
        total_time = time.time() - start_time
        log_trustcall_event(
            "webhook_call",
            {
                "step": "error",
                "total_time": total_time,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            success=False,
        )

        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route("/health_check", methods=["GET"])
def webhook_check():
    return jsonify({"status": "alive"}), 200


@app.route("/trustcall/metrics", methods=["GET"])
def trustcall_metrics_endpoint():
    """TrustCall metrics endpoint for monitoring dashboard"""
    try:
        webhook_success_rate = (
            trustcall_metrics["webhook_successes"]
            / max(trustcall_metrics["webhook_calls"], 1)
        ) * 100
        ai_success_rate = (
            trustcall_metrics["ai_api_successes"]
            / max(trustcall_metrics["ai_api_calls"], 1)
        ) * 100
        whiteboard_success_rate = (
            trustcall_metrics["whiteboard_successes"]
            / max(trustcall_metrics["whiteboard_generations"], 1)
        ) * 100
        avg_response_time = (
            (
                sum(trustcall_metrics["response_times"])
                / len(trustcall_metrics["response_times"])
            )
            if trustcall_metrics["response_times"]
            else 0
        )
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "webhook_metrics": {
                "total_calls": trustcall_metrics["webhook_calls"],
                "successes": trustcall_metrics["webhook_successes"],
                "failures": trustcall_metrics["webhook_failures"],
                "success_rate": round(webhook_success_rate, 2),
            },
            "ai_api_metrics": {
                "total_calls": trustcall_metrics["ai_api_calls"],
                "successes": trustcall_metrics["ai_api_successes"],
                "failures": trustcall_metrics["ai_api_failures"],
                "success_rate": round(ai_success_rate, 2),
            },
            "whiteboard_metrics": {
                "total_generations": trustcall_metrics["whiteboard_generations"],
                "successes": trustcall_metrics["whiteboard_successes"],
                "failures": trustcall_metrics["whiteboard_failures"],
                "success_rate": round(whiteboard_success_rate, 2),
            },
            "performance_metrics": {
                "avg_response_time": round(avg_response_time, 3),
                "payload_validation_errors": trustcall_metrics[
                    "payload_validation_errors"
                ],
            },
        }
        return jsonify(metrics), 200

    except Exception as e:
        log_trustcall_event("metrics_error", {"error": str(e)}, success=False)
        return jsonify({"error": f"Failed to get metrics: {str(e)}"}), 500


@app.errorhandler(Exception)
def handle_trustcall_errors(e):
    """Global error handler for TrustCall monitoring"""
    log_trustcall_event(
        "webhook_call", {"error": str(e), "error_type": type(e).__name__}, success=False
    )

    return jsonify({"error": "Internal server error", "message": str(e)}), 500


if __name__ == "__main__":
    flask_port_str = os.getenv("FLASK_PORT")
    flask_host_str = os.getenv("FLASK_HOST_PORT")
    if not flask_port_str:
        raise ValueError("FLASK_PORT must be set in .env file")
    flask_port = int(flask_port_str)

    flask_debug_str = os.getenv("FLASK_DEBUG")
    if not flask_debug_str:
        raise ValueError("FLASK_DEBUG must be set in .env file")
    flask_debug = flask_debug_str.lower() == "true"
    app.run(host=flask_host_str, debug=flask_debug, port=flask_port)
