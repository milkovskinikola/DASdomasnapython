from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from pydantic import EmailStr
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
from pymongo import MongoClient

auth_router = Blueprint('auth', __name__, template_folder='templates')
serializer = URLSafeTimedSerializer("DAS-DAS-DAS")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


client = MongoClient("mongodb://localhost:27017/")
db = client["user_db"]
user_collection = db["users"]

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def generate_session_token(data: dict) -> str:
    return serializer.dumps(data)

def validate_session_token(token: str, max_age: int = 7200):
    try:
        return serializer.loads(token, max_age=max_age)
    except Exception:
        return None
    

@auth_router.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        form_data = request.form
        email = form_data.get("email")
        name = form_data.get("name")
        password = form_data.get("password")
        role = "user"

        if user_collection.find_one({"email": email}):
            flash("User already exists", "error")
            return redirect(url_for('register'))
        
        hashed_password = hash_password(password)
        user_collection.insert_one({
            "email": email,
            "name": name,
            "hashed_password": hashed_password,
            "role": role
        })
        flash("Signup successful! Please login.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@auth_router.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        form_data = request.form
        email = form_data.get("email")
        password = form_data.get("password")

        user = user_collection.find_one({"email": email})
        if user and verify_password(password, user["hashed_password"]):
            session['user'] = generate_session_token({"email": email})
            session['name'] = user["name"]
            flash("Login successfull", "success")
            return render_template('index.html')
        
        flash("Invalid email or password", "error")
        return redirect(url_for('login'))
    
    return render_template('login.html')

@auth_router.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))