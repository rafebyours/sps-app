from flask import Blueprint, jsonify, request
import pymysql
from config import DB_CONFIG

warga_bp = Blueprint('warga', __name__, url_prefix='/api/warga')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# API key sederhana
API_KEY = "sps_app_key_12345"

def api_key_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-KEY")
        if api_key != API_KEY:
            return jsonify({"message": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# GET semua warga
@warga_bp.route('/', methods=['GET'])
@api_key_required
def get_all_warga():
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM warga")
        result = cursor.fetchall()
    conn.close()
    return jsonify(result)
