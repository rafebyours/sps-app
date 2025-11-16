# routes/warga.py
from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG

warga_bp = Blueprint('warga', __name__, url_prefix='/api/warga')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# GET /api/warga  → ambil semua warga
@warga_bp.route('/', methods=['GET'])
def get_all_warga():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT w.id, w.nama_warga, w.alamat, w.lokasi,
                       w.longitude, w.latitude,
                       u.username, u.status, u.role
                FROM warga w
                JOIN users u ON w.user_id = u.id
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
        return jsonify({"success": True, "data": rows}), 200
    except Exception as e:
        print("get_all_warga error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# GET /api/warga/<id>  → ambil 1 warga by id
@warga_bp.route('/<int:warga_id>', methods=['GET'])
def get_warga_by_id(warga_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT w.id, w.nama_warga, w.alamat, w.lokasi,
                       w.longitude, w.latitude,
                       u.username, u.status, u.role
                FROM warga w
                JOIN users u ON w.user_id = u.id
                WHERE w.id = %s
            """
            cursor.execute(sql, (warga_id,))
            row = cursor.fetchone()
        if not row:
            return jsonify({"success": False, "message": "Data warga tidak ditemukan"}), 404
        return jsonify({"success": True, "data": row}), 200
    except Exception as e:
        print("get_warga_by_id error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()
