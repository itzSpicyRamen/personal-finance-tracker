from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from database import get_db_connection
from datetime import datetime, timedelta
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
import secrets
import bcrypt
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError, PyJWTError
import os
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("debug.log")
    ]
)

logger = logging.getLogger(__name__)

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"))

oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    authorize_params={"scope": "email profile"},
    access_token_url="https://oauth2.googleapis.com/token",
    client_kwargs={"scope": "openid email profile"},
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

class UserSignup(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

################################################
#            HELPER FUNCTIONS                  #
################################################


# Hash password
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed_password.decode("utf-8")

# Password verification
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# Generates JSON Web Token
def generate_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expiration_time = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expiration_time})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_google_user_info(access_token: str):
    url = "https://www.googleapis.com/oauth2/v3/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Error retrieving user info: {response.status_code} - {response.text}")
        return None


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        if user_email is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s;", (user_email,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return user

def check_admin_priv(user: dict = Depends(get_current_user)):
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Ths role does not have admin privileges.")

################################################
#                ENDPOINTS                     #
################################################


# Route to user signup
@router.post("/signup")
def user_signup(user: UserSignup):
    logger.info(f"Sign up request received for email: {user.email}")
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email = %s;", (user.email,))
    user_exists = cur.fetchone()
    if user_exists:
        logger.warning(f"User with email {user.email} already exists")
        raise HTTPException(status_code=400, detail="This email is already registered")
    
    hashed_user_password = hash_password(user.password)
    cur.execute("INSERT INTO users (email, password) VALUES (%s, %s) RETURNING id;", 
                (user.email, hashed_user_password, 'user'))
    user_id = cur.fetchone()["id"]

    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Account created for user with ID {user_id}")
    return {"message": "Account created", "user_id": user_id}

# Route to user login
@router.post("/login")
def login(user: UserLogin):
    logger.info(f"Login attempt for email: {user.email}")
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email = %s;", (user.email,))
    user_exists = cur.fetchone()

    if not user_exists or not verify_password(user.password, user_exists["password"]):
        logger.warning(f"Failed login attempt for email: {user.email}")
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_DAYS)
    access_token = generate_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    refresh_token = generate_access_token(data={"sub": user.email}, expires_delta=refresh_token_expires)

    cur.close()
    conn.close()
    logger.info(f"Login successful for email: {user.email}")
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

# Google login redirect
@router.get("/auth/google")
async def google_login(request: Request):
    logger.info("Redirecting to Google OAuth for authentication")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    return await oauth.google.authorize_redirect(request, redirect_uri, state=state)

# Google callback
@router.get("/auth/google/callback")
async def google_callback(request: Request):
    session_state = request.session.get("oauth_state")
    callback_state = request.query_params.get("state")

    logger.info(f"Session state: {session_state}")
    logger.info(f"Callback state: {callback_state}")

    if not session_state or session_state != callback_state:
        raise HTTPException(status_code=400, detail="OAuth state mismatch.")

    token = await oauth.google.authorize_access_token(request)
    logger.info(f"Token received: {token}")

    access_token = token['access_token']
    user_info = await get_google_user_info(access_token)

    if not user_info:
        logger.error("Failed to retrieve user info")
        raise HTTPException(status_code=400, detail="Failed to retrieve user info")

    email = user_info["email"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email = %s;", (email,))
    existing_user = cur.fetchone()

    if not existing_user:
        cur.execute("INSERT INTO users (email, password) VALUES (%s, %s) RETURNING id;",
                    (email, "GOOGLE_SSO", 'user'),)
        conn.commit()

    cur.close()
    conn.close()

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_DAYS)
    access_token = generate_access_token(data={"sub": email}, expires_delta=access_token_expires)
    refresh_token = generate_access_token(data={"sub": email}, expires_delta=refresh_token_expires)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh")
def refresh_access_token(request: RefreshTokenRequest):
    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")

        access_token_expires = timedelta(minutes=30)
        new_access_token = generate_access_token({"sub": email}, access_token_expires)

        return {"access_token": new_access_token, "token_type": "bearer"}

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")