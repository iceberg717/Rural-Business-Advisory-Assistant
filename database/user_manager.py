"""
User Manager for RuralBiz Advisor
Stores and manages user accounts in database/users.json with secure password hashing.
"""
import os
import json
import hashlib
import secrets
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(CURRENT_DIR, "users.json")


def _init_users_file():
    """Ensure database/users.json exists with valid JSON array."""
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)


def get_all_users() -> list:
    """Read all users from database/users.json."""
    _init_users_file()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []


def save_all_users(users: list) -> bool:
    """Save all users to database/users.json."""
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving users to {USERS_FILE}: {e}")
        return False


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Hash password using SHA-256 with cryptographic salt."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hashed, salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify password against stored hash and salt."""
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, hashed)


def find_user_by_email(email: str):
    """Find user by email address (case-insensitive)."""
    clean_email = (email or "").strip().lower()
    if not clean_email:
        return None
    users = get_all_users()
    for user in users:
        if user.get("email", "").strip().lower() == clean_email:
            return user
    return None


def find_user_by_username(username: str):
    """Find user by username (case-insensitive)."""
    clean_user = (username or "").strip().lower()
    if not clean_user:
        return None
    users = get_all_users()
    for user in users:
        if user.get("username", "").strip().lower() == clean_user:
            return user
    return None


def find_user_by_identifier(identifier: str):
    """Find user by either username or email."""
    clean_id = (identifier or "").strip().lower()
    if not clean_id:
        return None
    users = get_all_users()
    for user in users:
        if (user.get("username", "").strip().lower() == clean_id or 
            user.get("email", "").strip().lower() == clean_id):
            return user
    return None


def register_user(username: str, email: str, password: str) -> tuple[bool, str, dict | None]:
    """
    Register a new user account.
    Returns: (success: bool, message: str, user_dict: dict | None)
    """
    clean_user = (username or "").strip()
    clean_email = (email or "").strip().lower()
    clean_pass = (password or "").strip()

    if not clean_user:
        return False, "Please enter a valid username.", None
    if not clean_email or "@" not in clean_email:
        return False, "Please enter a valid email address.", None
    if len(clean_pass) < 4:
        return False, "Password must be at least 4 characters long.", None

    # Check if email is already registered
    if find_user_by_email(clean_email):
        return False, "Email already used, try using login", None

    # Check if username is already registered
    if find_user_by_username(clean_user):
        return False, "Username already taken, please choose another username.", None

    users = get_all_users()
    pwd_hash, salt = hash_password(clean_pass)

    new_user = {
        "id": len(users) + 1,
        "username": clean_user,
        "email": clean_email,
        "password_hash": pwd_hash,
        "salt": salt,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

    users.append(new_user)
    if save_all_users(users):
        return True, "Account created successfully.", new_user
    else:
        return False, "Failed to save account. Please try again.", None


def authenticate_user(identifier: str, password: str) -> tuple[bool, str, dict | None]:
    """
    Authenticate user by username/email and password.
    Returns: (success: bool, message: str, user_dict: dict | None)
    """
    user = find_user_by_identifier(identifier)
    if not user:
        return False, "Invalid username or password. Please try again.", None

    pwd_hash = user.get("password_hash", "")
    salt = user.get("salt", "")

    if verify_password(password, pwd_hash, salt):
        return True, "Login successful.", user
    else:
        return False, "Invalid username or password. Please try again.", None
