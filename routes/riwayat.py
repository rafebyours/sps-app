# routes/riwayat.py
from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG

riwayat_bp = Blueprint('riwayat', __name__, url_prefix='/api/riwayat')

def get_connection():
    
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

"""
keterangan : get_riwayat
- Admin → melihat seluruh riwayat aktivitas untuk monitoring
- Petugas → melihat riwayat pekerjaan yang pernah dilakukan
- Warga → melihat riwayat laporan mereka sendiri
"""

@riwayat_bp.route('/', methods=['GET'])
def get_riwayat():
    id_warga = request.args.get('id_warga')
    id_petugas = request.args.get('id_petugas')

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT r.id, r.tanggal, r.jumlah_karung, r.status,
                       w.nama_warga,
                       p.nama_petugas
                FROM riwayat_aktivitas r
                LEFT JOIN warga w ON r.id_warga = w.id
                LEFT JOIN petugas p ON r.id_petugas = p.id
                WHERE 1=1
            """
            params = []

            if id_warga:
                sql += " AND r.id_warga = %s"
                params.append(id_warga)
            if id_petugas:
                sql += " AND r.id_petugas = %s"
                params.append(id_petugas)

            sql += " ORDER BY r.tanggal DESC, r.id DESC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

        return jsonify({"success": True, "data": rows}), 200
    except Exception as e:
        print("get_riwayat error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()
