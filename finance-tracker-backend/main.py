from fastapi import FastAPI
from database import get_db_connection
from authenticate import router as authentication_router
from starlette.middleware.sessions import SessionMiddleware
import os

#Load os variables here
SECRET_KEY = os.getenv("SESSION_SECRET_KEY")

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.include_router(authentication_router)

#Temporary root address route(change later)
@app.get("/")
def read_root():
    return {"message": "Welcome to the Finance Tracker API"}

#Temporary route to dump users(CJL REMOVE)
@app.get("/users")
def get_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users;")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users