import os
import json
import re
from typing import Any, Dict, List, Union
from mistralai import Mistral


def _load_env_file():
    """Load .env from the backend root if present.
    Prefer python-dotenv when available; otherwise parse manually.
    """
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    if not os.path.exists(env_path):
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
        return
    except Exception:
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            return


# Load .env at import time so os.getenv picks up MISTRAL_API_KEY
_load_env_file()


def extract_text_content(message_content) -> str:
    """
    Normalize Mistral message content into a string.
    Handles SDKs that return string or a list of text blocks.
    """
    if isinstance(message_content, str):
        return message_content

    if isinstance(message_content, list):
        texts = []
        for block in message_content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
            elif isinstance(block, str):
                texts.append(block)
        return "\n".join(texts)

    return str(message_content)


def _get_mistral_client():
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return None
    return Mistral(api_key=api_key)


def _format_exception(exc: Exception) -> str:
    """Try to extract useful HTTP/status/body info from exceptions."""
    try:
        info = {"error": str(exc)}
        resp = getattr(exc, "response", None) or getattr(exc, "res", None)
        if resp is not None:
            try:
                info["status_code"] = getattr(resp, "status_code", None)
                body = getattr(resp, "text", None) or getattr(resp, "body", None) or str(resp)
                info["body"] = body
            except Exception:
                info["response_repr"] = str(resp)
        return json.dumps(info)
    except Exception:
        return str(exc)


def _normalize_brands(brands) -> Union[List[str], None]:
    if not brands:
        return None
    if isinstance(brands, list):
        return [str(b).strip() for b in brands if str(b).strip()]
    if isinstance(brands, str):
        parts = re.split(r"[;,|/\\]+", brands)
        return [p.strip() for p in parts if p.strip()]
    return [str(brands)]


def _format_budget(budget) -> Union[str, None]:
    if budget is None:
        return None
    s = str(budget)
    cleaned = s.replace(',', '').replace('₹', '')
    nums = re.findall(r"\d+", cleaned)
    if not nums:
        return s
    if len(nums) >= 2:
        low = int(nums[0])
        high = int(nums[1])
        return f"₹{low:,} - ₹{high:,}"
    amt = int(nums[0])
    return f"₹{amt:,}"


def build_direct_prompt(user_input: dict) -> str:
    """Builds a strict prompt that sends the raw user input to Mistral and requests
    exactly three complete PC builds in JSON format with no confidence scores.
    """
    # Prefer dedicated form fields when available
    usage = user_input.get("usage")
    preferred_brands_raw = user_input.get("preferred_brands") or user_input.get("brands")
    preferred_brands = _normalize_brands(preferred_brands_raw)
    speed = user_input.get("speed")
    storage_capacity = user_input.get("storage_capacity")
    graphics_power = user_input.get("graphics_power")
    quiet_cooling = user_input.get("quiet_cooling")
    budget_raw = user_input.get("budget")
    budget = _format_budget(budget_raw)

    form_block = {
        "usage": usage,
        "preferred_brands": preferred_brands,
        "speed": speed,
        "storage_capacity": storage_capacity,
        "graphics_power": graphics_power,
        "quiet_cooling": quiet_cooling,
        "budget": budget,
        "budget_raw": budget_raw,
    }

    return f"""
You are an expert professional PC builder with deep knowledge of modern computer hardware and Indian market pricing.

TASK:
Return the BEST 3 complete PC builds based DIRECTLY on the user's FORM INPUTS below.

PRIORITY RULES:
- Use `usage` as primary driver.
- Respect `preferred_brands` when possible.
- Honor `budget` and use Indian pricing (₹) in `estimated_price`.
- Optimize for `speed`, `storage_capacity`, `graphics_power`, and `quiet_cooling` as specified.
- Do NOT include any confidence scores, metadata, or extra natural-language outside the JSON.

USER FORM INPUT:
{json.dumps(form_block, indent=2)}

OUTPUT (STRICT JSON ONLY):
[
    {{
        "build_name": "Short descriptive name",
        "cpu": "CPU model",
        "gpu": "GPU model",
        "ram": "RAM configuration",
        "storage": "SSD / HDD configuration",
        "motherboard": "Motherboard suggestion",
        "psu": "Power supply suggestion",
        "cabinet": "Cabinet type",
        "estimated_price": "Approximate total price in INR (₹)",
        "why_this_build": "2–3 line explanation tailored to the user"
    }}
]

Return EXACTLY 3 builds as a JSON array. Return ONLY valid JSON.
"""


def get_direct_recommendations(user_input: dict) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Call Mistral with the direct prompt and return a list of three recommendation dicts
    or an error dict.
    """
    client = _get_mistral_client()
    if client is None:
        return {"error": "missing_api_key", "details": "Set MISTRAL_API_KEY environment variable"}

    prompt = build_direct_prompt(user_input)
    try:
        response = client.chat.complete(
            model="mistral-large",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=900,
        )
    except Exception as e:
        return {"error": "llm_request_failed", "details": _format_exception(e)}

    # Extract content depending on SDK response shape and normalize
    try:
        raw_content = response.choices[0].message.content
    except Exception:
        raw_content = getattr(response, "content", None) or str(response)

    content = extract_text_content(raw_content)

    if not content or not content.strip():
        debug = None
        if os.getenv("RECOMMENDER_DEBUG") == "1":
            debug = {"raw_response": str(response)}
        return {"error": "empty_llm_response", "details": "LLM returned empty content", "debug": debug}

    # Parse JSON strictly; fall back to extracting first JSON array
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"(\[[\s\S]*\])", content)
        if m:
            try:
                parsed = json.loads(m.group(1))
            except Exception:
                return {"error": "invalid_json_extracted", "raw": content}
        else:
            return {"error": "invalid_json", "raw": content}

    if not isinstance(parsed, list):
        return {"error": "unexpected_llm_output", "raw": parsed}

    if len(parsed) != 3:
        # Accept >=3 but prefer exactly 3; trim if more, error if fewer
        if len(parsed) < 3:
            return {"error": "insufficient_builds", "details": "LLM returned fewer than 3 builds", "raw": parsed}
        parsed = parsed[:3]

    # Ensure each item is an object
    cleaned = [p for p in parsed if isinstance(p, dict)]
    if len(cleaned) != 3:
        return {"error": "invalid_build_items", "raw": parsed}

    return cleaned
