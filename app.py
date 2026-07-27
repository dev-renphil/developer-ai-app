from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import requests
import json
import base64
import time
import logging
import re
import uuid
import random
import math
import concurrent.futures
from datetime import datetime
import hmac
from functools import wraps
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import os
import sys
from pathlib import Path
from . import ai_steps

from .ai_dtos import Step1Reply, ReceiveDTO
from .shape import Whiteboard
from .logging_helpers import log_openai_prompt, save_openai_prompt
from . import sympy_operations as sympy_ops

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
    detect_operation_from_message,
    compute_sector_points,
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
CORS(app)

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

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
            "session_id",
            "receiving_url",
            "topic",
        ]

        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"

        if "whiteboard_state" not in data and "whiteboard" not in data:
            return False, "Missing required field: whiteboard_state"

        # Validate whiteboard state
        wb = data.get("whiteboard_state") or data.get("whiteboard") or {}
        is_valid, error = validate_whiteboard_payload(wb)
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


def get_whiteboard_image_bytes(root_url, whiteboard_json, verbose=True) -> bytes | None:
    preview_url = root_url + WHITEBOARD_PREVIEW_API_SUFFIX
    print("PREVIEW URL:", preview_url, flush=True)

    preview_response = requests.post(
        preview_url, json=whiteboard_json, headers={"Content-Type": "application/json"}
    )

    if preview_response.status_code == 200:
        if verbose:
            print("Image fetched successfully.")
        return preview_response.content
    else:
        if verbose:
            print(f"Failed to get image. Status code: {preview_response.status_code}")
        return None


def diarize_message(msg_tup, student_id, ai_id, tutor_name=None):
    label = tutor_name or "Tutor"
    if msg_tup["user_id"] == student_id:
        return {
            "text_message": msg_tup["text_message"],
            "timestamp": msg_tup["timestamp"],
            "user_id": "Student",
        }
    else:
        return {
            "text_message": msg_tup["text_message"],
            "timestamp": msg_tup["timestamp"],
            "user_id": label,
        }


def diarize_history(api_history, student_id, ai_id, tutor_name=None):
    return [diarize_message(m, student_id, ai_id, tutor_name=tutor_name) for m in api_history]


# LOOKBACK LENGTH (MESSAGES ONLY FOR NOW)
lookback_len_str = os.getenv("LOOKBACK_LEN")
if not lookback_len_str:
    raise ValueError("LOOKBACK_LEN must be set in .env file")
LOOKBACK_LEN = int(lookback_len_str)

INTERNAL_API_SECRET = os.getenv("INTERNAL_API_SECRET", "")
_ALLOWED_CALLBACK_HOSTS = set(
    h.strip()
    for h in os.getenv("ALLOWED_CALLBACK_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
)


def require_internal_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if INTERNAL_API_SECRET:
            token = request.headers.get("X-Internal-Token", "")
            if not hmac.compare_digest(token.encode(), INTERNAL_API_SECRET.encode()):
                return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def validate_receiving_url(url: str) -> Tuple[bool, str]:
    if not url:
        return False, "receiving_url is required"
    try:
        host = urlparse(url).hostname or ""
        if host not in _ALLOWED_CALLBACK_HOSTS:
            return False, f"receiving_url host '{host}' is not in the allowed list"
    except Exception:
        return False, "receiving_url is invalid"
    return True, ""


def describe_user_intent(
        whiteboard,
        receive_dto: ReceiveDTO,
        use_ai: str,
        pre_test_details: dict | None = None,
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
        receive_dto.history, student_id=student_id, ai_id=ai_id, tutor_name=receive_dto.tutor_name
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
        pre_test_details=pre_test_details,
    )

    # WE CAN NOW RUN STEP 1
    model_step1 = os.getenv(f"{use_ai.upper()}_MODEL")
    if not model_step1:
        raise ValueError("OPENAI_MODEL must be set in .env file")
    openai_temperature_str = os.getenv("OPENAI_TEMPERATURE")
    if not openai_temperature_str:
        raise ValueError("OPENAI_TEMPERATURE must be set in .env file")
    openai_temperature = float(openai_temperature_str)

    try:
        step1_resp = getattr(ai_steps, f"call_{use_ai}")(PROMPT_SCAFFOLD, model_step1, openai_temperature)
        print("Step 1 response:", step1_resp)
        logger.info(json.loads(step1_resp))
        result = Step1Reply(**json.loads(step1_resp))

        # Hard guard: force null for obvious greetings regardless of what the LLM returned
        msg = (receive_dto.user_message or "").strip().lower()
        _GREETING_TOKENS = {"hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "got it", "sure", "cool", "great", "nice", "bye", "goodbye"}
        if result.operation is not None and len(msg.split()) <= 4 and all(w in _GREETING_TOKENS for w in msg.split()):
            logger.info(f"[STEP1] Forcing null â€” message looks like a greeting: {msg!r}")
            result.operation = None
            result.instruction = ""

        if result.image_process and result.operation in (None, "basic_draw"):
            logger.info("[STEP1] image_process=true on basic/null op â€” retrying Step 1 with image")
            try:
                image_bytes = get_whiteboard_image_bytes(
                    receive_dto.get_root_url_with_scheme(), whiteboard.model_dump()
                )
                step1_resp2 = getattr(ai_steps, f"call_{use_ai}_with_image_bytes")(
                    PROMPT_SCAFFOLD, image_bytes, model_step1, openai_temperature
                )
                logger.info(f"[STEP1] image retry response: {step1_resp2}")
                result = Step1Reply(**json.loads(step1_resp2))
            except Exception as img_err:
                logger.warning(f"[STEP1] image retry failed, using text-only result: {img_err}")

        return result

    except Exception as e:
        print("Step 1 error:", e)
        return jsonify({"error": f"Step 1 error: {e}"}), 500


def _run_step2_llm(whiteboard: Whiteboard, description: str, receive_dto: ReceiveDTO, use_ai: str, image_process: bool):
    """Call the Step-2 LLM to generate whiteboard patches for basic_draw operations."""
    openai_temperature_str = os.getenv("OPENAI_TEMPERATURE")
    if not openai_temperature_str:
        raise ValueError("OPENAI_TEMPERATURE must be set in .env file")
    openai_temperature = float(openai_temperature_str)

    try:
        PROMPT_SCAFFOLD = step2_build(whiteboard, description)
        model_step2 = os.getenv(f"{use_ai.upper()}_MODEL")
        if not model_step2:
            raise ValueError(f"{use_ai.upper()}_MODEL must be set in .env file")
        logger.info(f"[STEP2] Sending request to {use_ai} model: {model_step2}")

        if image_process:
            image_bytes = get_whiteboard_image_bytes(receive_dto.get_root_url_with_scheme(), whiteboard.model_dump())
            step2_resp = getattr(ai_steps, f"call_{use_ai}_with_image_bytes")(PROMPT_SCAFFOLD, image_bytes, model_step2, openai_temperature)
        else:
            step2_resp = getattr(ai_steps, f"call_{use_ai}")(PROMPT_SCAFFOLD, model_step2, openai_temperature)

        logger.info(f"[STEP2] Received response ({len(step2_resp)} chars)")
        parsed = json.loads(step2_resp)
        # Normalise: AI may return a single patch dict instead of a list
        if isinstance(parsed, dict):
            parsed = [parsed]
        # Extract text if the LLM returned it inside the JSON
        lm_text = ""
        if parsed and isinstance(parsed[0], dict) and "text" in parsed[0]:
            lm_text = parsed[0].pop("text", "")
        return parsed, lm_text

    except Exception as e:
        logger.error(f"Step 2 LLM error: {e}", exc_info=True)
        return [], ""


def generate_shapes(whiteboard: Whiteboard, step1_response, receive_dto: ReceiveDTO, use_ai: str, image_process: bool):
    operation = step1_response.operation
    if not operation:
        return [], step1_response.text

    logger.info(f"[STEP2] operation={operation} element_ids={step1_response.element_ids}")

    # --- SymPy path (everything that is not basic_draw) ---
    if operation != "basic_draw":
        if not step1_response.element_ids:
            logger.warning(f"[SYMPY] '{operation}' requires element_ids but none provided â€” replying with text only")
            return [], step1_response.text

        op_fn = getattr(sympy_ops, operation, None)
        if not op_fn:
            logger.warning(f"[SYMPY] No function found for operation '{operation}' â€” replying with text only")
            return [], step1_response.text

        try:
            op_result = op_fn(whiteboard, step1_response.element_ids, params=step1_response.operation_params)
        except TypeError:
            op_result = op_fn(whiteboard, step1_response.element_ids)

        patches = op_result.get("patches", [])
        sympy_text = op_result.get("text", "")
        text_reply = f"{step1_response.text} {sympy_text}".strip() if sympy_text else step1_response.text
        logger.info(f"[SYMPY] '{operation}' produced {len(patches)} patch(es)")

        if patches:
            whiteboard.apply_patches_from_ai(patches)

        return patches, text_reply

    # --- basic_draw path: step 2 LLM only ---
    lm_patches, lm_text = _run_step2_llm(whiteboard, step1_response.instruction, receive_dto, use_ai, image_process)
    response_text = lm_text or step1_response.text

    if lm_patches:
        whiteboard.apply_patches_from_ai(lm_patches)

    return lm_patches, response_text


def _log_whiteboard_elements(whiteboard: Whiteboard, label: str) -> None:
    active = [el for el in whiteboard.elements if not el.isDeleted]
    lines = [f"  [{i}] id={el.id!r:30s} type={el.type!r:12s} x={el.x:<8.1f} y={el.y:<8.1f} w={el.width:<8.1f} h={el.height:<8.1f} color={el.strokeColor}"
             for i, el in enumerate(active)]
    logger.info(f"[WHITEBOARD {label}] {len(active)} active element(s):\n" + ("\n".join(lines) if lines else "  (empty)"))


@app.route("/draw", methods=["POST"])
@require_internal_auth
def draw():
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("Received new request at /draw endpoint")
    logger.info("=" * 80)

    try:
        data = request.get_json()
        logger.info("Payload received, starting processing")
        logger.info(f"[PRE-TEST] pre_test_details={data}")

        # TrustCall: Validate webhook payload
        is_valid, validation_error = validate_webhook_payload(data)
        if not is_valid:
            return jsonify({"error": f"Invalid payload: {validation_error}"}), 400

        ssrf_ok, ssrf_err = validate_receiving_url(data.get("receiving_url", ""))
        if not ssrf_ok:
            return jsonify({"error": ssrf_err}), 400

        use_ai = os.getenv("USE_AI")
        receive_dto = ReceiveDTO(
            user_message=data.get("message"),
            history=data.get("history"),
            session_id=data.get("session_id"),
            receiving_url=data.get("receiving_url"),
            topic=data.get("topic"),
            pre_test_details=data.get("pre_test_details"),
            tutor_name=data.get("tutor_name"),
        )
        whiteboard_state = data.get("whiteboard_state") or data.get("whiteboard") or {}
        whiteboard = Whiteboard.model_validate(whiteboard_state)
        _log_whiteboard_elements(whiteboard, "BEFORE")
        final_whiteboard_dict = whiteboard.to_excalidraw_dict()
        intent_timer = time.time()
        step1_response = describe_user_intent(whiteboard, receive_dto, use_ai, receive_dto.pre_test_details)
        logger.info(f"Total time to assume describe user intent: {time.time() - intent_timer}s")

        has_draw_ops = step1_response.operation is not None
        if has_draw_ops:
            logger.info(f"Board should be updated! operation={step1_response.operation}")
            shape_timer = time.time()
            patches, response_text = generate_shapes(
                whiteboard=whiteboard,
                step1_response=step1_response,
                use_ai=use_ai,
                receive_dto=receive_dto,
                image_process=step1_response.image_process
            )
            logger.info(f"Total time to generate shapes: {time.time() - shape_timer}s")
            # patches already applied to whiteboard inside generate_shapes
            _log_whiteboard_elements(whiteboard, "AFTER")
            final_whiteboard_dict = whiteboard.to_excalidraw_dict()

            response_json = json.dumps(
                {
                    "text": response_text,
                    "appState": final_whiteboard_dict["appState"],
                    "elements": final_whiteboard_dict["elements"],
                    "tutor_name": receive_dto.tutor_name,
                    "session_id": receive_dto.session_id,
                }
            )

            # logger.info(f"response json: {response_json}")

            requests.post(
                receive_dto.receiving_url,
                json={"response": response_json},
                headers={"Content-Type": "application/json"},
            )
            logger.info(f"Total time: {time.time() - start_time}s")
            return jsonify({"status": "sent", "reply": response_json}), 200

        else:  # no draw operations
            if whiteboard:
                response_json = json.dumps(
                    {
                        "text": step1_response.text,
                        "appState": final_whiteboard_dict["appState"],
                        "elements": final_whiteboard_dict["elements"],
                        "tutor_name": receive_dto.tutor_name,
                        "session_id": receive_dto.session_id,
                    }
                )
            else:
                response_json = json.dumps(
                    {
                        "text": step1_response.text,
                        "appState": {},
                        "elements": {},
                        "tutor_name": receive_dto.tutor_name,
                        "session_id": receive_dto.session_id,
                    }
                )

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

        _log_whiteboard_elements(whiteboard, "AFTER")
        logger.info(f"Total time: {time.time() - start_time}s")
        return jsonify({"status": "sent", "reply": response_json}), 200

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        logger.info(f"Total time: {time.time() - start_time}s")
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
