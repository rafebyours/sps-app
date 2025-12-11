from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG

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
