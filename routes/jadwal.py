# routes/jadwal.py
from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG

jadwal_bp = Blueprint('jadwal', __name__, url_prefix='/api/jadwal')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# GET /api/jadwal?status=aktif&id_petugas=1
@jadwal_bp.route('/', methods=['GET'])
def get_all_jadwal():
    status = request.args.get('status')       # optional
    id_petugas = request.args.get('id_petugas')  # optional

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            base_sql = """
                SELECT j.id, j.tanggal, j.jam_mulai, j.jam_selesai,
                       j.wilayah, j.status,
                       p.nama_petugas
                FROM jadwal j
                LEFT JOIN petugas p ON j.id_petugas = p.id
                WHERE 1=1
            """
            params = []

            if status:
                base_sql += " AND j.status = %s"
                params.append(status)
            if id_petugas:
                base_sql += " AND j.id_petugas = %s"
                params.append(id_petugas)

            base_sql += " ORDER BY j.tanggal DESC, j.jam_mulai ASC"

            cursor.execute(base_sql, params)
            rows = cursor.fetchall()

        return jsonify({"success": True, "data": rows}), 200
    except Exception as e:
        print("get_all_jadwal error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# GET /api/jadwal/<id>
@jadwal_bp.route('/<int:jadwal_id>', methods=['GET'])
def get_jadwal_by_id(jadwal_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT j.id, j.tanggal, j.jam_mulai, j.jam_selesai,
                       j.wilayah, j.status,
                       p.nama_petugas
                FROM jadwal j
                LEFT JOIN petugas p ON j.id_petugas = p.id
                WHERE j.id = %s
            """
            cursor.execute(sql, (jadwal_id,))
            row = cursor.fetchone()

        if not row:
            return jsonify({"success": False, "message": "Data jadwal tidak ditemukan"}), 404

        return jsonify({"success": True, "data": row}), 200
    except Exception as e:
        print("get_jadwal_by_id error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()
