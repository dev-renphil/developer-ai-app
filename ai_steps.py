import base64

from google.genai import types
import re

from .ai_clients import AIClients

clients = AIClients()


def clean_json_response(text: str) -> str:
    """Strip markdown fences and extract the first JSON array or object."""
    text = re.sub(r"^```json\s*|^```\s*|\s*```$", "", text.strip())

    match = re.search(r"\[[\s\S]*\]|\{[\s\S]*\}", text)
    return match.group(0).strip() if match else text

def bytes_to_base64(image_bytes: bytes, media_type: str = "image/png") -> tuple[str, str]:
    """Convert raw bytes to base64 string. Excalidraw exports as PNG by default."""
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    return b64, media_type


def call_openai(prompt: str, model: str, temperature: float) -> str:
    resp = clients.openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return clean_json_response(resp.choices[0].message.content)


def call_claude(prompt: str, model: str, temperature: float) -> str:
    resp = clients.claude.messages.create(
        model=model,
        max_tokens=1024,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return clean_json_response(resp.content[0].text)


def call_gemini(prompt: str, model: str, temperature: float, thinking: bool = False) -> str:
    config = types.GenerateContentConfig(
        temperature=temperature,
        thinking_config=types.ThinkingConfig(thinking_budget=0) if not thinking else None,
    )
    resp = clients.google.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    return clean_json_response(resp.text)



def call_claude_with_image_bytes(prompt: str, image_bytes: bytes, model: str, temperature: float, media_type: str = "image/png") -> str:
    b64, media_type = bytes_to_base64(image_bytes, media_type)
    resp = clients.claude.messages.create(
        model=model,
        max_tokens=1024,
        temperature=temperature,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return clean_json_response(resp.content[0].text)


def call_openai_with_image_bytes(prompt: str, image_bytes: bytes, model: str, temperature: float, media_type: str = "image/png") -> str:
    b64, media_type = bytes_to_base64(image_bytes, media_type)
    data_url = f"data:{media_type};base64,{b64}"
    resp = clients.openai.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return clean_json_response(resp.choices[0].message.content)


def call_gemini_with_image_bytes(prompt: str, image_bytes: bytes, model: str, temperature: float, media_type: str = "image/png") -> str:
    _, media_type = bytes_to_base64(image_bytes, media_type)  # just for consistency
    resp = clients.google.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=media_type),  # Gemini takes raw bytes directly
            prompt,
        ],
        config=types.GenerateContentConfig(
            temperature=temperature,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return clean_json_response(resp.text)
