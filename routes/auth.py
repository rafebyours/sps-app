from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG
import jwt
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # <-- aktifkan CORS


auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
SECRET_KEY = "sps_secret_key"  # bisa diganti, simpan rahasia

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# Register user (optional, biasanya admin yang buat)
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'warga')

    hashed_password = generate_password_hash(password)

    conn = get_connection()
    with conn.cursor() as cursor:
        sql = "INSERT INTO users (username,password,role) VALUES (%s,%s,%s)"
        cursor.execute(sql, (username, hashed_password, role))
        conn.commit()
    conn.close()
    return jsonify({"message": "User registered"}), 201

# Login user
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password'], password):
        payload = {
            "id": user['id'],
            "username": user['username'],
            "role": user['role'],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        return jsonify({"token": token})
    else:
        return jsonify({"message": "Invalid credentials"}), 401

