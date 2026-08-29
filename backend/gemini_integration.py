"""
Real LLM generation using Google Gemini with dynamic interactive input.
"""
import os
import json
import urllib.request
import urllib.error

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "Set the GEMINI_API_KEY environment variable before running this.\n"
        "Windows (CMD):        set GEMINI_API_KEY=your_key_here\n"
        "Windows (PowerShell): $env:GEMINI_API_KEY=\"your_key_here\"\n"
        "Linux/Mac:            export GEMINI_API_KEY=\"your_key_here\""
    )

def gemini_call(prompt: str) -> str:
    """Calls Gemini via direct REST API using the recommended gemini-3.6-flash model."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
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
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            return text
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        raise RuntimeError(f"Gemini API Error ({e.code}): {err_msg}")


if __name__ == "__main__":
    from advisory_assistant import advise

    print("Rural Business Advisory Assistant (Interactive Gemini Mode)")
    print("Available Talukas in Mehsana: Kheralu, Vadnagar, Becharaji, Satlasana, Visnagar, Unjha, Vijapur, Kadi, Mahesana")
    print("=" * 75 + "\n")

    while True:
        try:
            user_idea = input("Enter your business idea (e.g. 'organic fertilizer unit', 'dairy processing'): ").strip()
            if not user_idea:
                print("Please enter a valid business idea.")
                continue
            if user_idea.lower() in ("exit", "quit"):
                print("Exiting. Goodbye!")
                break
                
            user_taluka = input("Enter Mehsana taluka (e.g. Visnagar, Kheralu, Kadi, Unjha): ").strip()
            if not user_taluka:
                print("Please enter a valid taluka.")
                continue

            print("\nGenerating advisory report with Gemini... Please wait.\n")
            report = advise(
                user_idea,
                taluka=user_taluka,
                use_llm=True,
                api_call_fn=gemini_call,
            )
            print("-" * 75)
            print(report)
            print("-" * 75 + "\n")
            
            cont = input("Would you like to try another query? (y/n): ").strip().lower()
            if cont != 'y':
                print("Exiting. Goodbye!")
                break
                
        except KeyboardInterrupt:
            print("\nExiting. Goodbye!")
            break
        except Exception as e:
            print(f"Error: {e}\n")