"""
Shared Google Gemini client used by every AI feature (job extraction,
listing summaries, resume tailoring). Uses plain `requests` — no new packages.

Setup:
  1. Get a key at https://aistudio.google.com/apikey
  2. Add to backend/.env:  GEMINI_API_KEY=your_key
     Optional:             GEMINI_MODEL=gemini-2.5-flash

If the key is missing or Gemini fails, generate_json() returns None and
callers fall back to their non-AI behaviour. It never raises.

Privacy: with a free-tier key Google may use submitted text (including
resumes) to improve its models. Use a paid key for real student data.
"""

import json
import logging
import os
import time

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("gemini_client")

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-2.5-flash"
REQUEST_TIMEOUT = 60
MAX_ATTEMPTS = 3


def _api_key():
    return (os.getenv("GEMINI_API_KEY") or "").strip()


def get_model():
    return (os.getenv("GEMINI_MODEL") or DEFAULT_MODEL).strip()


def is_llm_available():
    """True when a Gemini key is configured."""
    return bool(_api_key())


def generate_json(prompt, schema, system_instruction=None, temperature=0.2):
    """
    Sends a prompt to Gemini and asks for JSON matching `schema`
    (Gemini's OpenAPI-style subset: OBJECT, STRING, INTEGER, BOOLEAN, ARRAY).
    Returns the parsed dict, or None on any failure.
    """
    key = _api_key()
    if not key:
        logger.warning("GEMINI_API_KEY is not set — skipping AI step")
        return None

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    url = GEMINI_ENDPOINT.format(model=get_model())
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}

    resp = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            logger.error(f"Gemini request failed: {e}")
            return None

        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == MAX_ATTEMPTS:
                break
            retry_after = resp.headers.get("Retry-After")
            try:
                wait = float(retry_after) if retry_after else 2 ** attempt
            except ValueError:
                wait = 2 ** attempt
            logger.warning(f"Gemini returned {resp.status_code}, retrying in {wait:.0f}s")
            time.sleep(min(wait, 30))
            continue
        break

    if resp is None or resp.status_code != 200:
        status = resp.status_code if resp is not None else "no response"
        text = resp.text[:300] if resp is not None else ""
        logger.error(f"Gemini error {status}: {text}")
        return None

    try:
        data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts)
        parsed = json.loads(text)
    except (KeyError, IndexError, ValueError, TypeError) as e:
        logger.error(f"Couldn't parse Gemini response as JSON: {e}")
        return None

    return parsed if isinstance(parsed, dict) else None
