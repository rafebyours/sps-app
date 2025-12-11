from flask import Blueprint, jsonify
from config import DB_CONFIG
from routes.auth import get_connection

lokasi_bp = Blueprint('lokasi_bp', __name__, url_prefix='/api/lokasi')


@lokasi_bp.route('/petugas', methods=['GET'])
def get_lokasi_petugas():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT 
                p.id,
                p.nama_petugas,
                p.latitude,
                p.longitude,
                u.username
            FROM petugas p
            LEFT JOIN users u ON u.id = p.user_id
            """
            cursor.execute(sql)
            data = cursor.fetchall()

        return jsonify({
            "success": True,
            "message": "Lokasi petugas ditemukan",
            "data": data
        }), 200

    except Exception as e:
        print("Error get_lokasi_petugas:", e)
        return jsonify({"success": False, "message": "Server error"}), 500

    finally:
        conn.close()
