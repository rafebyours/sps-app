# routes/pemasukan.py
from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG

pemasukan_bp = Blueprint('pemasukan', __name__, url_prefix='/api/pemasukan')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)


# =========================================
# GET /api/pemasukan
# Opsional filter:
#   - ?id_warga=3
#   - ?id_laporan=4
# =========================================
@pemasukan_bp.route('/', methods=['GET'])
def get_all_pemasukan():
    id_warga = request.args.get('id_warga')
    id_laporan = request.args.get('id_laporan')

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT p.id, p.tanggal, p.jumlah_karung,
                       p.jumlah_pembayaran, p.kekurangan, p.kelebihan,
                       w.nama_warga,
                       ls.id AS id_laporan
                FROM pemasukan p
                LEFT JOIN warga w ON p.id_warga = w.id
                LEFT JOIN laporan_sampah ls ON p.id_laporan = ls.id
                WHERE 1=1
            """
            params = []

            if id_warga:
                sql += " AND p.id_warga = %s"
                params.append(id_warga)
            if id_laporan:
                sql += " AND p.id_laporan = %s"
                params.append(id_laporan)

            sql += " ORDER BY p.tanggal DESC, p.id DESC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

        return jsonify({"success": True, "data": rows}), 200
    except Exception as e:
        print("get_all_pemasukan error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()


# =========================================
# GET /api/pemasukan/<id>
# Detail satu pemasukan
# =========================================
@pemasukan_bp.route('/<int:pemasukan_id>', methods=['GET'])
def get_pemasukan_by_id(pemasukan_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT p.id, p.tanggal, p.jumlah_karung,
                       p.jumlah_pembayaran, p.kekurangan, p.kelebihan,
                       p.id_warga, w.nama_warga,
                       p.id_laporan
                FROM pemasukan p
                LEFT JOIN warga w ON p.id_warga = w.id
                WHERE p.id = %s
            """
            cursor.execute(sql, (pemasukan_id,))
            row = cursor.fetchone()

        if not row:
            return jsonify({"success": False, "message": "Data pemasukan tidak ditemukan"}), 404

        return jsonify({"success": True, "data": row}), 200
    except Exception as e:
        print("get_pemasukan_by_id error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()


# =========================================
# POST /api/pemasukan
# Catat pembayaran dari warga
# Body contoh:
# {
#   "id_warga": 3,
#   "id_laporan": 4,
#   "jumlah_karung": 5,
#   "jumlah_pembayaran": 50000,
#   "kekurangan": 0,
#   "kelebihan": 0
# }
# =========================================
@pemasukan_bp.route('/', methods=['POST'])
def create_pemasukan():
    data = request.json or {}

    id_warga = data.get('id_warga')
    id_laporan = data.get('id_laporan')
    jumlah_karung = data.get('jumlah_karung')
    jumlah_pembayaran = data.get('jumlah_pembayaran')
    kekurangan = data.get('kekurangan', 0)
    kelebihan = data.get('kelebihan', 0)

    # ===== Validasi dasar =====
    if not id_warga or not id_laporan:
        return jsonify({"success": False, "message": "id_warga dan id_laporan wajib diisi"}), 400
    if jumlah_karung is None:
        return jsonify({"success": False, "message": "jumlah_karung wajib diisi"}), 400
    if jumlah_pembayaran is None:
        return jsonify({"success": False, "message": "jumlah_pembayaran wajib diisi"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Cek warga
            cursor.execute("SELECT id FROM warga WHERE id = %s", (id_warga,))
            warga = cursor.fetchone()
            if not warga:
                return jsonify({"success": False, "message": "Data warga tidak ditemukan"}), 404

            # Cek laporan & konsistensi
            cursor.execute(
                "SELECT id, id_warga, status, jumlah_karung FROM laporan_sampah WHERE id = %s",
                (id_laporan,)
            )
            laporan = cursor.fetchone()
            if not laporan:
                return jsonify({"success": False, "message": "Data laporan tidak ditemukan"}), 404

            if laporan['id_warga'] != int(id_warga):
                return jsonify({
                    "success": False,
                    "message": "id_warga pada pemasukan tidak sesuai dengan id_warga di laporan"
                }), 400

            # (Opsional tapi rapi) hanya izinkan pemasukan jika laporan sudah selesai
            if laporan['status'] != 'selesai':
                return jsonify({
                    "success": False,
                    "message": "Pemasukan hanya bisa dicatat untuk laporan yang sudah berstatus 'selesai'"
                }), 400

            # Kalau jumlah_karung tidak diisi → pakai dari laporan
            if not jumlah_karung:
                jumlah_karung = laporan['jumlah_karung']

            sql = """
                INSERT INTO pemasukan
                    (id_warga, id_laporan, jumlah_karung,
                     jumlah_pembayaran, kekurangan, kelebihan)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                id_warga,
                id_laporan,
                jumlah_karung,
                jumlah_pembayaran,
                kekurangan,
                kelebihan
            ))
            conn.commit()
            new_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "message": "Data pemasukan berhasil dicatat",
            "pemasukan_id": new_id
        }), 201

    except Exception as e:
        print("create_pemasukan error:", e)
        conn.rollback()
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()
