from flask import Blueprint, jsonify, request
import pymysql
from config import DB_CONFIG
from datetime import datetime, time, timedelta

jadwal_bp = Blueprint('jadwal', __name__, url_prefix='/api/jadwal')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# API Key sederhana
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

def serialize_jadwal(jadwals):
    for jadwal in jadwals:
        # convert datetime / time / timedelta ke string
        for key in jadwal:
            if isinstance(jadwal[key], (datetime, time, timedelta)):
                jadwal[key] = str(jadwal[key])
    return jadwals

# Endpoint untuk semua jadwal
@jadwal_bp.route('/', methods=['GET'])
@api_key_required
def get_all_jadwal():
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM jadwal")
        jadwals = cursor.fetchall()
    conn.close()
    return jsonify(serialize_jadwal(jadwals))

# Endpoint untuk jadwal hari ini
@jadwal_bp.route('/hari-ini', methods=['GET'])
@api_key_required
def get_jadwal_hari_ini():
    today = datetime.now().strftime("%Y-%m-%d")
    
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM jadwal WHERE DATE(tanggal)=%s", (today,))
        jadwals = cursor.fetchall()
    conn.close()
    return jsonify(serialize_jadwal(jadwals))
