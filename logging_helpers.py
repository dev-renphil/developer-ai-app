import os
from datetime import datetime


def log_openai_prompt(logger, step: str, content, max_chars: int = 20000):
    """
    Logs the outgoing OpenAI payload's TEXT only.
    - Works for both: string prompt, or multi-part content list [{"type":"text","text":"..."}, ...]
    - Skips image_url/base64 parts to avoid huge logs.
    """
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
            elif isinstance(c, dict) and c.get("type") == "image_url":
                # Avoid logging base64; log a placeholder instead
                parts.append("[[image_url omitted]]")
        text = "\n".join(parts)
    else:
        text = str(content)

    # Trim so logs stay readable
    text_trimmed = text[:max_chars]
    suffix = "" if len(text) <= max_chars else f"... [TRUNCATED {len(text) - max_chars} chars]"

    logger.info("[%s] Outgoing prompt (text-only, %d chars):\n%s%s", step, len(text), text_trimmed, suffix)


def save_openai_prompt(step_name, content, folder="prompt_logs"):
    """
    Save the full OpenAI prompt to a text file for debugging.
    Handles both plain strings and multimodal content (text + images).
    """

    os.makedirs(folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{folder}/{step_name}_{timestamp}.txt"

    text_parts = []

    if isinstance(content, str):
        text_parts.append(content)

    elif isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif part.get("type") == "image_url":
                    text_parts.append("[IMAGE CONTENT REMOVED FOR LOG]")

    else:
        text_parts.append(str(content))

    full_text = "\n\n".join(text_parts)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"[PROMPT SAVED] {filename}")