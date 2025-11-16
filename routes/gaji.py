# routes/gaji.py
from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG

gaji_bp = Blueprint('gaji', __name__, url_prefix='/api/gaji')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# GET /api/gaji?id_petugas=1
@gaji_bp.route('/', methods=['GET'])
def get_all_gaji():
    id_petugas = request.args.get('id_petugas')

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT g.id, g.id_petugas, p.nama_petugas,
                       g.jumlah_sampah, g.total_gaji, g.tanggal
                FROM gaji_petugas g
                JOIN petugas p ON g.id_petugas = p.id
                WHERE 1=1
            """
            params = []

            if id_petugas:
                sql += " AND g.id_petugas = %s"
                params.append(id_petugas)

            sql += " ORDER BY g.tanggal DESC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

        return jsonify({"success": True, "data": rows}), 200
    except Exception as e:
        print("get_all_gaji error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()
