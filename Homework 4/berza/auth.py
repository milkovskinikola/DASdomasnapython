from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from pydantic import EmailStr
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
from pymongo import MongoClient

class DatabaseManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance.client = MongoClient("mongodb://mongo:27017/")
            cls._instance.db = cls._instance.client["user_db"]
        return cls._instance
    
    def get_collection(self, collection_name):
        return self.db[collection_name]

class SecurityFactory:
    @staticmethod
    def get_password_context():
        return CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    @staticmethod
    def get_serializer(secret_key):
        return URLSafeTimedSerializer(secret_key)
    
class AuthUtils:
    def __init__(self, secret_key):
        self.serializer = SecurityFactory.get_serializer(secret_key)
        self.pwd_context = SecurityFactory.get_password_context()

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def generate_session_token(self, data: dict) -> str:
        return self.serializer.dumps(data)
    
    def validate_session_token(self, token: str, max_age: int = 7200):
        try:
            return self.serializer.loads(token, max_age=max_age)
        except Exception:
            return None
        
auth_router = Blueprint('auth', __name__, template_folder='templates')
db_manager = DatabaseManager()
user_collection = db_manager.get_collection("users")
auth_utils = AuthUtils("DAS-DAS-DAS")

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
            return redirect(url_for('auth.register'))
        
        hashed_password = auth_utils.hash_password(password)
        user_collection.insert_one({
            "email": email,
            "name": name,
            "hashed_password": hashed_password,
            "role": role
        })
        flash("Signup successful! Please login.", "success")
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_router.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        form_data = request.form
        email = form_data.get("email")
        password = form_data.get("password")

        user = user_collection.find_one({"email": email})
        if user and auth_utils.verify_password(password, user["hashed_password"]):
            session['user'] = auth_utils.generate_session_token({"email": email})
            session['name'] = user["name"]
            flash("Login successful", "success")
            return render_template('index.html')
        
        flash("Invalid email or password", "error")
        return redirect(url_for('auth.login'))
    
    return render_template('login.html')

@auth_router.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None) 
    flash("You have been logged out.", "success")
    return redirect(url_for('auth.login')) 
