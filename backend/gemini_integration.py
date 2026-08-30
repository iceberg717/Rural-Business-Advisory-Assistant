"""
LLM generation using Google Gemini API with graceful error handling and fallbacks.
"""
import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

# Load .env file from project root or current directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv(os.path.join(CURRENT_DIR, ".env"))

def get_gemini_api_key():
    return os.environ.get("GEMINI_API_KEY", "").strip()

def gemini_call(prompt: str, model_name: str = "gemini-1.5-flash") -> str:
    """
    Calls Gemini REST API. If the API call fails or key is missing/invalid,
    raises RuntimeError with details so caller can fall back.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    models_to_try = [model_name, "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    # De-duplicate while preserving order
    models_to_try = list(dict.fromkeys(models_to_try))

    last_error = None
    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                return text
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            last_error = f"Gemini API Error ({e.code}) on {model}: {err_msg}"
            # If 401 unauthorized, trying other models won't help with bad key
            if e.code == 401:
                break
        except Exception as e:
            last_error = f"Network or API Error on {model}: {str(e)}"

    raise RuntimeError(last_error or "Gemini API call failed.")