import json
import re
from mistralai import Mistral
import os

MODEL_NAME = "open-mistral-7b"


def get_pc_recommendations(user_input: dict):
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return {"error": "missing_api_key"}

    client = Mistral(api_key=api_key)

    prompt = f"""
You are an expert PC builder in India.

User requirements:
{json.dumps(user_input, indent=2)}

Return EXACTLY 3 PC builds in JSON array format ONLY.
No text, no markdown.

[
  {{
    "build_name": "",
    "cpu": "",
    "gpu": "",
    "ram": "",
    "storage": "",
    "motherboard": "",
    "psu": "",
    "cabinet": "",
    "estimated_price": "",
    "why_this_build": ""
  }}
]
"""

    try:
        response = client.chat.complete(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800,
        )
    except Exception as e:
        return {"error": "llm_request_failed", "details": str(e)}

    # -------- SAFE CONTENT EXTRACTION --------
    try:
        content = response.choices[0].message.content
        if isinstance(content, list):
            content = "\n".join(
                block.get("text", "") for block in content if isinstance(block, dict)
            )
        content = (content or "").strip()
    except Exception as e:
        return {"error": "llm_response_read_failed", "details": str(e)}

    # 🔍 DEBUG (keep for now)
    print("🔎 RAW LLM OUTPUT:\n", content)

    if not content:
        return {"error": "empty_llm_response"}

    # -------- SAFE JSON PARSING --------
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to extract JSON array from text
        match = re.search(r"(\[[\s\S]*\])", content)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

        return {
            "error": "invalid_json_from_llm",
            "raw_output": content
        }
