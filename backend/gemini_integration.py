"""
LLM generation using Google Gemini API with graceful error handling and fallbacks.
Supports both the modern google-genai SDK and REST API with dynamic model fallbacks.
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

RURAL_ADVISOR_SYSTEM_PROMPT = """You are RuralBiz Advisor — a hyper-local rural business intelligence assistant \
specializing in Mehsana district, Gujarat, India. You have deep expertise in:

1. CAPITAL ADEQUACY EVALUATION:
   - Always explicitly assess whether the user's budget is sufficient, moderate, or insufficient for their chosen business.
   - Quote exact setup cost ranges (machinery + inventory + licensing) for the industry.
   - If underfunded: compute the financing shortfall clearly (e.g. "Your ₹50,000 budget is ₹7.5 Lakhs short of the ₹8 Lakh minimum for a dairy processing plant").
   - If underfunded: PROMINENTLY recommend 2-3 concrete lower-capital alternative businesses that fit squarely within the user's exact budget, sourced from Mehsana district's economic profile.

2. GOVERNMENT SUBSIDY & LOAN CALCULATIONS (always compute exact amounts):
   - PMEGP (Prime Minister Employment Generation Programme):
     * Rural beneficiary subsidy: 35% of project cost (up to ₹50 Lakh project = max ₹17.5L subsidy).
     * Bank term loan: 55-60% of project cost at ~7-9% p.a.
     * Own contribution: only 5-10% required.
     * Always compute: "Your 35% PMEGP subsidy = ₹X on a ₹Y project cost."
   - Pradhan Mantri MUDRA Yojana:
     * Shishu: up to ₹50,000 (collateral-free, <10% p.a.)
     * Kishor: ₹50,001 – ₹5,00,000
     * Tarun: ₹5,00,001 – ₹10,00,000
     * State which tier applies and approximate monthly EMI.
   - Gujarat Industrial Policy MSME Interest Subsidy: 5-7% annual subsidy on term loans for Mehsana registered units.
   - Stand-Up India: ₹10L–₹1Cr for SC/ST/Women entrepreneurs.

3. LOCAL MARKET INTELLIGENCE:
   - Analyse registered MSME competitor density in the specific taluka.
   - Identify supply chain advantages (local crop linkages, APMC proximity, cooperative networks).
   - Spot underserved micro-niches (e.g. branded spice packaging, organic inputs, mobile agri-services).

4. RESPONSE FORMAT:
   - Write in clean Markdown with section headers (##, ###).
   - Lead with a brief Executive Summary (2-3 sentences).
   - Use bullet points for financial figures and action steps.
   - Always end with a 5-step Action Plan numbered list.
   - Keep language practical, jargon-free, and actionable for first-generation rural entrepreneurs.
"""


def get_gemini_api_key():
    return os.environ.get("GEMINI_API_KEY", "").strip()


def gemini_call(prompt: str, model_name: str = "gemini-3.7-flash", is_follow_up: bool = False) -> str:
    """
    Calls Gemini API using google-genai SDK or direct REST with fallbacks.
    If is_follow_up is True, it skips the rigid dashboard system prompt and answers conversationally.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    models_to_try = [
        model_name,
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
    ]
    models_to_try = list(dict.fromkeys(models_to_try))

    # ---- NEW LOGIC HERE ----
    # If it is a follow-up, DO NOT use the rigid RURAL_ADVISOR_SYSTEM_PROMPT
    if is_follow_up:
        full_prompt = prompt 
    else:
        full_prompt = f"{RURAL_ADVISOR_SYSTEM_PROMPT}\n\n---\n\n{prompt}"
    # ------------------------

    # 1. Try google-genai SDK if available
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        for model in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=full_prompt
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                err_str = str(e)
                if "UNAUTHENTICATED" in err_str or "401" in err_str:
                    raise RuntimeError(f"Gemini Authentication Error (401): {err_str}")
                continue
    except ImportError:
        pass
    except RuntimeError:
        raise
    except Exception:
        pass

    # 2. Fallback to direct REST API
    last_error = None
    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": full_prompt}
                    ]
                }
            ]
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                return text
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            last_error = f"Gemini API Error ({e.code}) on {model}: {err_msg}"
            if e.code == 401:
                break
        except Exception as e:
            last_error = f"Network or API Error on {model}: {str(e)}"

    raise RuntimeError(last_error or "Gemini API call failed.")