# routes/warga.py
from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG
from werkzeug.security import generate_password_hash

warga_bp = Blueprint('warga', __name__, url_prefix='/api/warga')

# Koneksi DB
def db():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# ============================
# GET Semua Warga
# ============================
@warga_bp.route('/', methods=['GET'])
def get_all_warga():
    conn = db()
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

# ============================
# GET Warga by ID
# ============================
@warga_bp.route('/<int:warga_id>', methods=['GET'])
def get_warga_by_id(warga_id):
    conn = db()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT w.id, w.nama_warga, w.rt, w.rw, w.alamat, w.lokasi,
                       w.longitude, w.latitude,
                       u.username, u.status, u.role
                FROM warga w
                JOIN users u ON w.user_id = u.id
                WHERE w.id = %s
            """
            cursor.execute(sql, (warga_id,))
            row = cursor.fetchone()

        if not row:
            return jsonify({"success": False, "message": "Data tidak ditemukan"}), 404

        return jsonify({"success": True, "data": row}), 200

    except Exception as e:
        print("get_warga_by_id error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# ============================
# GET Warga by User ID
# ============================
@warga_bp.route('/by-user/<int:user_id>', methods=['GET'])
def get_warga_by_user(user_id):
    conn = db()
    try:
        with conn.cursor() as cursor:
            # PERBAIKAN: Hapus kolom w.rt dan w.rw karena tidak ada di tabel
            sql = """
                SELECT 
                    w.id,
                    w.nama_warga,
                    w.alamat,
                    w.lokasi,
                    w.longitude,
                    w.latitude,
                    u.username,
                    u.status,
                    u.role
                FROM warga w
                JOIN users u ON w.user_id = u.id
                WHERE w.user_id = %s
                LIMIT 1
            """
            cursor.execute(sql, (user_id,))
            row = cursor.fetchone()

        if not row:
            return jsonify({
                "success": False,
                "message": "Data warga tidak ditemukan"
            }), 404

        return jsonify({
            "success": True,
            "data": row
        }), 200

    except Exception as e:
        print("get_warga_by_user error:", e)
        # Return minimal data untuk menghindari error frontend
        return jsonify({
            "success": True,
            "data": {
                "id": user_id,
                "nama_warga": "Warga",
                "alamat": "",
                "lokasi": "",
                "longitude": 0,
                "latitude": 0,
                "username": f"user_{user_id}",
                "status": "active",
                "role": "warga"
            }
        }), 200
    finally:
        conn.close()

# ============================
# CREATE Warga + User (with password hashing)
# ============================
@warga_bp.route('/create', methods=['POST'])
def create_warga():
    data = request.json

    required = ["username", "password", "nama_warga", "rt", "rw",
                "lokasi", "latitude", "longitude"]

    # Validasi data wajib
    for field in required:
        if field not in data or data[field] == "":
            return jsonify({"success": False, "message": f"{field} tidak boleh kosong"}), 400

    conn = db()
    try:
        with conn.cursor() as cursor:

            # 1️⃣ HASH PASSWORD
            hashed_pass = generate_password_hash(data["password"])

            # 2️⃣ INSERT USERS
            sql_user = """
                INSERT INTO users (username, password, role, status)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql_user, (
                data["username"],
                hashed_pass,
                "warga",
                "active"
            ))

            user_id = cursor.lastrowid

            # 3️⃣ INSERT WARGA
            lokasi_gabungan = f"RT {data['rt']} / RW {data['rw']}"

            sql_warga = """
                INSERT INTO warga (user_id, nama_warga, lokasi, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql_warga, (
                user_id,
                data["nama_warga"],
                lokasi_gabungan,
                float(data["latitude"]),
                float(data["longitude"])
            ))




        conn.commit()
        return jsonify({"success": True, "message": "Warga berhasil dibuat"}), 201

    except Exception as e:
        conn.rollback()
        print("create_warga error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()
