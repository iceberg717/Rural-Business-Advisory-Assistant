import os
import sys
from typing import Optional
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Ensure backend and database folders are in Python path
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
DATABASE_DIR = os.path.join(BASE_DIR, "database")
for path in [BACKEND_DIR, DATABASE_DIR, BASE_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.advisory_assistant import advise, advise_structured, MEHSANA_TALUKAS
from backend.gemini_integration import gemini_call
from database.user_manager import (
    register_user, 
    authenticate_user, 
    find_user_by_username
)

app = FastAPI(
    title="RuralBiz Advisor",
    description="Hyper-local rural business intelligence & advisory assistant for Mehsana district",
    version="1.0.0"
)

# Mount static directory for CSS, JS, images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Jinja2 templates directory
templates = Jinja2Templates(directory="templates")


class ChatPayload(BaseModel):
    message: str
    taluka: Optional[str] = None
    investment: Optional[str] = None

# --- ADDED: MEMORY TRACKER ---
# This dictionary remembers the last business context for each logged-in user
active_sessions = {}


def get_current_user(request: Request) -> Optional[dict]:
    """Helper to retrieve authenticated user from cookie."""
    username = request.cookies.get("ruralbiz_user", "").strip()
    if not username:
        return None
    return find_user_by_username(username)


def classify_intent(user_text: str, api_call_fn) -> str:
    """Classifies if the user wants a NEW business, a FOLLOW-UP, or is asking TRIVIA."""
    
    # 1. AI ROUTER (Much smarter prompt to handle pivots and trivia)
    router_prompt = f"""
    You are an AI assistant for a Rural Business Advisor in Mehsana.
    Analyze the user's input: "{user_text}"

    Classify the input into exactly ONE of these three categories:
    1. NEW_BUSINESS: If the user is proposing a new business idea, category, or industry (e.g. "textile weaving in Visnagar", "start a dairy", "solar farm"). Even if it starts with "Actually" or "How about", if it introduces a new industry, it is NEW_BUSINESS.
    2. FOLLOW_UP: If the user is asking a question about costs, plans, subsidies, or giving a command related to an existing business (e.g. "build me a financial plan", "how do I register", "what about the costs").
    3. TRIVIA: If the user is asking a completely unrelated question (e.g. "who won the world cup", "what is the weather", "tell me a joke").

    Reply ONLY with the category name (NEW_BUSINESS, FOLLOW_UP, or TRIVIA).
    """
    
    try:
        # Note: We pass is_follow_up=True here so it bypasses the dashboard RAG prompt!
        res = api_call_fn(router_prompt, is_follow_up=True).strip().upper()
        if "NEW_BUSINESS" in res:
            return "NEW_BUSINESS"
        elif "TRIVIA" in res:
            return "TRIVIA"
        else:
            return "FOLLOW_UP"
    except Exception as e:
        print(f"Router Error: {e}")
        # Very basic local fallback if API fails
        lower_text = user_text.lower()
        if any(w in lower_text for w in ["plan", "cost", "register", "how"]):
            return "FOLLOW_UP"
        return "NEW_BUSINESS"


# ---------------------------------------------------------------------------
# Frontend Page Routes (HTML Views)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, name="home")
async def serve_home(request: Request):
    """Serve Dashboard / Landing Page"""
    user = get_current_user(request)
    return templates.TemplateResponse(
        request=request, 
        name="dashboard/home.html", 
        context={"request": request, "user": user}
    )


@app.get("/chat", response_class=HTMLResponse, name="chat")
async def serve_chat(request: Request, prompt: Optional[str] = None):
    """
    Serve AI Business Advisor Chat Page.
    Requires user to be logged in; otherwise redirects to /login?next=/chat.
    """
    user = get_current_user(request)
    if not user:
        redirect_url = "/login?next=/chat"
        if prompt:
            redirect_url += f"&prompt={prompt}"
        return RedirectResponse(url=redirect_url, status_code=302)

    return templates.TemplateResponse(
        request=request, 
        name="chatbot/chat.html", 
        context={
            "request": request, 
            "user": user,
            "messages": [],
            "talukas": MEHSANA_TALUKAS,
            "initial_prompt": prompt
        }
    )


@app.get("/login", response_class=HTMLResponse, name="login")
async def serve_login(
    request: Request, 
    next: Optional[str] = Query(None, alias="next")
):
    """Serve Login Page"""
    user = get_current_user(request)
    if user:
        target = next if next and next.startswith("/") else "/"
        return RedirectResponse(url=target, status_code=302)

    return templates.TemplateResponse(
        request=request, 
        name="accounts/login.html", 
        context={
            "request": request, 
            "next_url": next or "",
            "user": None
        }
    )


@app.post("/login", response_class=HTMLResponse, name="login_post")
async def handle_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: Optional[str] = Query(None, alias="next")
):
    """
    Handle Login Form Submission.
    Validates user credentials against database/users.json.
    """
    success, message, user = authenticate_user(username, password)
    
    if not success:
        return templates.TemplateResponse(
            request=request,
            name="accounts/login.html",
            context={
                "request": request,
                "error": message,
                "username": username,
                "next_url": next or "",
                "user": None
            },
            status_code=400
        )
    
    target_url = next if (next and next.startswith("/")) else "/"
    response = RedirectResponse(url=target_url, status_code=303)
    response.set_cookie(
        key="ruralbiz_user", 
        value=user["username"], 
        max_age=86400 * 7, 
        httponly=True, 
        samesite="lax"
    )
    return response


@app.get("/register", response_class=HTMLResponse, name="register")
async def serve_register(
    request: Request,
    next: Optional[str] = Query(None, alias="next")
):
    """Serve Registration Page"""
    user = get_current_user(request)
    if user:
        target = next if next and next.startswith("/") else "/"
        return RedirectResponse(url=target, status_code=302)

    return templates.TemplateResponse(
        request=request, 
        name="accounts/register.html", 
        context={
            "request": request, 
            "next_url": next or "",
            "user": None
        }
    )


@app.post("/register", response_class=HTMLResponse, name="register_post")
async def handle_register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    next: Optional[str] = Query(None, alias="next")
):
    """
    Handle Registration Form Submission.
    Pushes new user to database/users.json after validating duplicate email & username.
    """
    success, message, user = register_user(username, email, password)
    
    if not success:
        return templates.TemplateResponse(
            request=request,
            name="accounts/register.html",
            context={
                "request": request,
                "error": message,
                "username": username,
                "email": email,
                "next_url": next or "",
                "user": None
            },
            status_code=400
        )
    
    target_url = next if (next and next.startswith("/")) else "/"
    response = RedirectResponse(url=target_url, status_code=303)
    response.set_cookie(
        key="ruralbiz_user", 
        value=user["username"], 
        max_age=86400 * 7, 
        httponly=True, 
        samesite="lax"
    )
    return response


@app.get("/logout", name="logout")
async def handle_logout():
    """Clear session cookie and redirect to home"""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("ruralbiz_user")
    return response


# ---------------------------------------------------------------------------
# Backend REST API Routes
# ---------------------------------------------------------------------------

@app.post("/api/chat", name="chat_api")
async def chat_api(request: Request, payload: ChatPayload):
    """
    Main Chat API Endpoint.
    Requires logged in user. Returns structured JSON with status, missing fields, or advisory report.
    """
    user = get_current_user(request)
    if not user:
        return JSONResponse(
            status_code=401,
            content={
                "reply": "🔒 **Authentication Required:** Please log in or register to use the AI Business Advisor.",
                "status": "auth_required"
            }
        )

    user_message = payload.message.strip()
    if not user_message:
        return JSONResponse(
            status_code=400,
            content={"reply": "Please provide a valid question or business idea.", "status": "error"}
        )

    # 1. SMART INTENT ROUTING
    intent = classify_intent(user_message, gemini_call)
    username = user["username"]

    # --- NEW: TRIVIA / OUT-OF-SCOPE CATCHER ---
    if intent == "TRIVIA":
        return {
            "status": "success", 
            "reply": "I specialize strictly in rural business intelligence, MSME subsidies, and supply chain advisory for the Mehsana district. How can I assist you with your enterprise today?"
        }

    # 2. HANDLE CONVERSATIONAL FOLLOW-UP
    if intent == "FOLLOW_UP":
        # Retrieve what the user was previously talking about (or default if it's their first message)
        last_context = active_sessions.get(username, "a generic rural business in Mehsana")
        
        try:
            follow_up_prompt = f"""
            You are an expert rural business advisor in Mehsana, Gujarat.
            The user's current active business context is: "{last_context}"
            
            Based on this context, answer their follow-up question or command: "{user_message}"
            
            Provide a helpful, practical, and highly specific answer based on their exact business. 
            Do not generate a full dashboard. Just answer the question directly.
            """
            answer = gemini_call(follow_up_prompt, is_follow_up=True)
            # Return success with the conversational answer
            return {"status": "success", "reply": answer}
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"reply": f"An error occurred while answering your question: {str(e)}", "status": "error"}
            )

    # 3. HANDLE NEW BUSINESS DASHBOARD GENERATION
    # Save this new business idea to the user's memory session!
    active_sessions[username] = user_message

    try:
        res = advise_structured(
            user_text=user_message,
            taluka=payload.taluka,
            investment=payload.investment,
            use_llm=True,
            api_call_fn=gemini_call
        )
        return res
    except Exception as e:
        print(f"Error in chat_api endpoint: {e}")
        try:
            fallback_res = advise_structured(
                user_text=user_message,
                taluka=payload.taluka,
                investment=payload.investment,
                use_llm=False
            )
            return fallback_res
        except Exception as inner_e:
            return JSONResponse(
                status_code=500,
                content={"reply": f"An error occurred while generating business advice: {str(inner_e)}", "status": "error"}
            )  


@app.get("/api/talukas", name="get_talukas")
async def get_talukas():
    """Return list of supported Mehsana talukas"""
    return {"talukas": MEHSANA_TALUKAS}


@app.get("/api/health", name="health_check")
async def health_check():
    """Application Health Check"""
    return {
        "status": "healthy",
        "app": "RuralBiz Advisor",
        "talukas_covered": len(MEHSANA_TALUKAS)
    }