from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG
from werkzeug.security import generate_password_hash

petugas_bp = Blueprint('petugas', __name__, url_prefix='/api/petugas')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

@petugas_bp.route('/', methods=['GET'])
def get_petugas():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM petugas ORDER BY id DESC")
            rows = cursor.fetchall()
        return jsonify({"success": True, "data": rows}), 200
    except Exception as e:
        print("get_petugas error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

@petugas_bp.route('/', methods=['POST'])
def add_petugas():
    data = request.json
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO petugas (user_id, nama_petugas, no_telp, status, longitude, latitude)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data['user_id'],
                data['nama_petugas'],
                data['no_telp'],
                data['status'],
                data.get('longitude', 0),
                data.get('latitude', 0)
            ))
            conn.commit()
        return jsonify({"success": True, "message": "Petugas berhasil ditambahkan"}), 201
    except Exception as e:
        print("add_petugas error:", e)
        return jsonify({"success": False, "message": "Gagal menambah data"}), 500
    finally:
        conn.close()

@petugas_bp.route('/<int:id>', methods=['DELETE'])
def delete_petugas(id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM petugas WHERE id = %s", (id,))
            conn.commit()
        return jsonify({"success": True, "message": "Petugas dihapus"}), 200
    except Exception as e:
        print("delete_petugas error:", e)
        return jsonify({"success": False, "message": "Gagal menghapus"}), 500
    finally:
        conn.close()

@petugas_bp.route('/create', methods=['POST'])
def create_petugas():
    data = request.json
    required = ['username', 'password', 'name', 'phone', 'address']

    # Validasi
    for field in required:
        if field not in data or data[field] == '':
            return jsonify({"success": False, "message": f"{field} wajib diisi"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1️⃣ Buat akun di users
            hashed_pass = generate_password_hash(data['password'])
            sql_user = "INSERT INTO users (username, password, role, status) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql_user, (data['username'], hashed_pass, 'petugas', 'active'))
            user_id = cursor.lastrowid

            # 2️⃣ Masukkan data petugas
            sql_petugas = "INSERT INTO petugas (user_id, name, phone, address) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql_petugas, (user_id, data['name'], data['phone'], data['address']))

        conn.commit()
        return jsonify({"success": True, "message": "Petugas berhasil dibuat"}), 201
    except Exception as e:
        conn.rollback()
        print("create_petugas error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()