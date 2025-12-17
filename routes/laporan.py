from flask import Blueprint, request, jsonify, make_response
import pymysql
from config import DB_CONFIG
from datetime import datetime

laporan_bp = Blueprint('laporan', __name__, url_prefix='/api/laporan')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# ====== Handle CORS untuk semua request ======
@laporan_bp.before_request
def handle_options():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,PATCH,DELETE,OPTIONS'
        return response

@laporan_bp.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,PATCH,DELETE,OPTIONS'
    return response

# ================== GET ALL ==================
@laporan_bp.route('/', methods=['GET'])
def get_all_laporan():
    status = request.args.get('status')
    id_warga = request.args.get('id_warga')

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT l.id, l.id_warga, w.nama_warga,
                       l.alamat, l.sudah_dipilah,
                       l.jumlah_karung, l.jenis_sampah, l.jenis_pembayaran,
                       l.jadwal_pengambilan, l.status,
                       l.created_at
                FROM laporan_sampah l
                JOIN warga w ON l.id_warga = w.id
                WHERE 1=1
            """
            params = []
            if status:
                sql += " AND l.status = %s"
                params.append(status)
            if id_warga:
                sql += " AND l.id_warga = %s"
                params.append(id_warga)
            sql += " ORDER BY l.created_at DESC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

        return jsonify({"success": True, "data": rows}), 200
    except Exception as e:
        print("get_all_laporan error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# ================== GET BY ID ==================
@laporan_bp.route('/<int:laporan_id>', methods=['GET'])
def get_laporan_by_id(laporan_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT l.id, l.id_warga, w.nama_warga,
                       l.alamat, l.sudah_dipilah,
                       l.jumlah_karung, l.jenis_sampah, l.jenis_pembayaran,
                       l.jadwal_pengambilan, l.status,
                       l.created_at
                FROM laporan_sampah l
                JOIN warga w ON l.id_warga = w.id
                WHERE l.id = %s
            """
            cursor.execute(sql, (laporan_id,))
            row = cursor.fetchone()

        if not row:
            return jsonify({"success": False, "message": "Data laporan tidak ditemukan"}), 404

        return jsonify({"success": True, "data": row}), 200
    except Exception as e:
        print("get_laporan_by_id error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# ================== CREATE ==================
@laporan_bp.route('/', methods=['POST'])
def create_laporan():
    data = request.json or {}
    id_warga = data.get('id_warga')
    alamat = data.get('alamat')
    sudah_dipilah = data.get('sudah_dipilah', 0)
    jumlah_karung = data.get('jumlah_karung')
    jenis_pembayaran = data.get('jenis_pembayaran')
    tanggal_pengambilan = data.get('tanggal_pengambilan')
    jam_pengambilan = data.get('jam_pengambilan')
    jenis_sampah = data.get('jenis_sampah')

    # Validasi
    if not id_warga:
        return jsonify({"success": False, "message": "id_warga wajib diisi"}), 400
    if jumlah_karung is None:
        return jsonify({"success": False, "message": "jumlah_karung wajib diisi"}), 400
    if not jenis_pembayaran:
        return jsonify({"success": False, "message": "jenis_pembayaran wajib diisi"}), 400
    if not tanggal_pengambilan:
        return jsonify({"success": False, "message": "tanggal_pengambilan wajib diisi"}), 400
    if not jenis_sampah:
        return jsonify({"success": False, "message": "jenis_sampah wajib diisi"}), 400

    # Boolean to int
    sudah_dipilah_val = 1 if sudah_dipilah else 0

    # Parse jadwal
    try:
        if jam_pengambilan:
            if len(jam_pengambilan) == 5:
                jam_pengambilan += ":00"
            jadwal_dt = datetime.strptime(f"{tanggal_pengambilan} {jam_pengambilan}", "%Y-%m-%d %H:%M:%S")
        else:
            jadwal_dt = datetime.strptime(f"{tanggal_pengambilan} 08:00:00", "%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        return jsonify({"success": False, "message": f"Format tanggal/jam tidak valid: {str(e)}"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Ambil alamat dari warga jika tidak ada
            if not alamat:
                cursor.execute("SELECT alamat FROM warga WHERE id = %s", (id_warga,))
                warga = cursor.fetchone()
                if not warga:
                    return jsonify({"success": False, "message": "Data warga tidak ditemukan"}), 404
                alamat = warga['alamat']

            sql = """
                INSERT INTO laporan_sampah
                (id_warga, alamat, sudah_dipilah, jumlah_karung,
                 jenis_pembayaran, jadwal_pengambilan, jenis_sampah, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'menunggu')
            """
            cursor.execute(sql, (id_warga, alamat, sudah_dipilah_val, jumlah_karung,
                                 jenis_pembayaran, jadwal_dt, jenis_sampah))
            conn.commit()
            new_id = cursor.lastrowid

        return jsonify({"success": True, "message": "Laporan sampah berhasil dibuat", "laporan_id": new_id}), 201
    except Exception as e:
        print("create_laporan error:", e)
        conn.rollback()
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    finally:
        conn.close()

# ================== UPDATE STATUS ==================
@laporan_bp.route('/<int:laporan_id>/status', methods=['PATCH'])
def update_laporan_status(laporan_id):
    data = request.json or {}
    new_status = data.get('status')
    id_petugas = data.get('id_petugas')

    if not new_status:
        return jsonify({"success": False, "message": "status wajib diisi"}), 400

    new_status = new_status.lower()
    allowed_status = ['menunggu', 'dijemput', 'selesai']
    if new_status not in allowed_status:
        return jsonify({"success": False, "message": "Status tidak valid"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, id_warga, jumlah_karung, status FROM laporan_sampah WHERE id=%s", (laporan_id,))
            laporan = cursor.fetchone()
            if not laporan:
                return jsonify({"success": False, "message": "Data laporan tidak ditemukan"}), 404

            if laporan['status'] == 'selesai' and new_status != 'selesai':
                return jsonify({"success": False, "message": "Laporan yang sudah selesai tidak bisa diubah"}), 400

            cursor.execute("UPDATE laporan_sampah SET status=%s WHERE id=%s", (new_status, laporan_id))

            # Tambah ke riwayat_aktivitas jika perlu
            riwayat_status = None
            if new_status == 'dijemput':
                riwayat_status = 'diambil'
            elif new_status == 'selesai':
                riwayat_status = 'selesai'

            if riwayat_status:
                petugas_id_val = int(id_petugas) if id_petugas not in (None, '', 0, '0') else None
                sql_riwayat = """
                    INSERT INTO riwayat_aktivitas
                    (id_warga, id_petugas, jumlah_karung, status)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql_riwayat, (laporan['id_warga'], petugas_id_val, laporan['jumlah_karung'], riwayat_status))

            conn.commit()
        return jsonify({"success": True, "message": f"Status laporan berhasil diubah menjadi '{new_status}'"}), 200
    except Exception as e:
        print("update_laporan_status error:", e)
        conn.rollback()
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()
