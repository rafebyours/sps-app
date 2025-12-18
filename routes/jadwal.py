# routes/jadwal.py
from flask import Blueprint, request, jsonify, make_response
import pymysql
from config import DB_CONFIG
from datetime import datetime, date, timedelta


jadwal_bp = Blueprint('jadwal', __name__, url_prefix='/api/jadwal')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)
@jadwal_bp.before_request
def handle_options():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,PATCH,DELETE,OPTIONS'
        return response

@jadwal_bp.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,PATCH,DELETE,OPTIONS'
    return response

# GET /api/jadwal?status=aktif&id_petugas=1
@jadwal_bp.route('/', methods=['GET']) 
def get_all_jadwal():
    status = request.args.get('status')      
    id_petugas = request.args.get('id_petugas') 

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

        # 🔹 convert jam_mulai & jam_selesai ke string biar bisa di-jsonify
        for r in rows:
            if 'jam_mulai' in r and r['jam_mulai'] is not None:
                r['jam_mulai'] = str(r['jam_mulai'])
            if 'jam_selesai' in r and r['jam_selesai'] is not None:
                r['jam_selesai'] = str(r['jam_selesai'])

        return jsonify({"success": True, "data": rows}), 200
    except Exception as e:
        print("get_all_jadwal error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()


# GET /api/jadwal/<id

@jadwal_bp.route('/today', methods=['GET'])
def get_today_jadwal_user():
    today = date.today().strftime("%Y-%m-%d")  # 'YYYY-MM-DD'

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT j.id, j.tanggal, j.jam_mulai, j.jam_selesai,
                       j.wilayah, j.status,
                       p.nama_petugas
                FROM jadwal j
                LEFT JOIN petugas p ON j.id_petugas = p.id
                WHERE j.tanggal = %s
                  AND j.status = 'aktif'
                ORDER BY j.jam_mulai ASC
            """
            cursor.execute(sql, (today,))
            rows = cursor.fetchall()

            # Convert jam ke string supaya bisa di-jsonify
            for r in rows:
                if r.get('jam_mulai'):
                    r['jam_mulai'] = str(r['jam_mulai'])
                if r.get('jam_selesai'):
                    r['jam_selesai'] = str(r['jam_selesai'])

        return jsonify({
            "success": True,
            "tanggal": today,
            "data": rows
        }), 200
    except Exception as e:
        print("get_today_jadwal_user error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()


@jadwal_bp.route('/', methods=['POST'])
def create_jadwal():
    data = request.json or {}

    tanggal = data.get('tanggal')
    jam_mulai = data.get('jam_mulai')
    jam_selesai = data.get('jam_selesai')
    wilayah = data.get('wilayah')
    id_petugas = data.get('id_petugas')   # boleh None
    status = data.get('status', 'aktif')

    # ===== Validasi dasar =====
    if not tanggal or not jam_mulai or not jam_selesai or not wilayah:
        return jsonify({
            "success": False,
            "message": "tanggal, jam_mulai, jam_selesai, dan wilayah wajib diisi"
        }), 400

    # Validasi tanggal
    try:
        datetime.strptime(tanggal, "%Y-%m-%d")
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal harus YYYY-MM-DD"}), 400

    # Normalisasi jam
    def normalize_time(t):
        return t + ":00" if len(t) == 5 else t

    jam_mulai_norm = normalize_time(jam_mulai)
    jam_selesai_norm = normalize_time(jam_selesai)

    try:
        datetime.strptime(jam_mulai_norm, "%H:%M:%S")
        datetime.strptime(jam_selesai_norm, "%H:%M:%S")
    except ValueError:
        return jsonify({"success": False, "message": "Format jam harus HH:MM atau HH:MM:SS"}), 400

    # Validasi status
    if status not in ['aktif', 'nonaktif']:
        return jsonify({"success": False, "message": "Status harus 'aktif' atau 'nonaktif'"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:

            # ===== VALIDASI id_petugas =====
            petugas_id_val = None
            if id_petugas not in (None, "", 0, "0"):
                try:
                    petugas_id_val = int(id_petugas)
                except ValueError:
                    return jsonify({"success": False, "message": "id_petugas harus angka"}), 400

                cursor.execute("SELECT id FROM petugas WHERE id = %s", (petugas_id_val,))
                petugas = cursor.fetchone()

                if not petugas:
                    return jsonify({"success": False, "message": "Petugas tidak ditemukan"}), 400

            # ===== INSERT jadwal =====
            sql = """
                INSERT INTO jadwal (tanggal, jam_mulai, jam_selesai,
                                    wilayah, id_petugas, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """

            cursor.execute(sql, (
                tanggal,
                jam_mulai_norm,
                jam_selesai_norm,
                wilayah,
                petugas_id_val,   # none atau id valid
                status
            ))
            conn.commit()
            new_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "message": "Jadwal penjemputan berhasil dibuat",
            "jadwal_id": new_id
        }), 201

    except Exception as e:
        print("create_jadwal error:", e)
        conn.rollback()
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()


@jadwal_bp.route('/week', methods=['GET'])
def get_next_week_jadwal():
    today = date.today()
    week_ahead = today + timedelta(days=7)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                    SELECT j.id, j.tanggal, j.jam_mulai, j.jam_selesai,
                        j.wilayah, j.status,
                        p.nama_petugas
                    FROM jadwal j
                    LEFT JOIN petugas p ON j.id_petugas = p.id
                    WHERE j.tanggal BETWEEN %s AND %s
                    ORDER BY j.tanggal ASC, j.jam_mulai ASC
                """

            # urutan parameter harus sesuai: start_date, end_date
            cursor.execute(sql, (today, week_ahead))
            rows = cursor.fetchall()

            # convert jam_mulai & jam_selesai ke string agar bisa JSON
            for r in rows:
                if r.get('jam_mulai'):
                    r['jam_mulai'] = str(r['jam_mulai'])
                if r.get('jam_selesai'):
                    r['jam_selesai'] = str(r['jam_selesai'])

        return jsonify({"success": True, "data": rows}), 200

    except Exception as e:
        print("get_next_week_jadwal error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()
        
@jadwal_bp.route('/multi', methods=['POST'])
def create_jadwal_multi():
    data = request.json or {}

    tanggal = data.get('tanggal')
    jam_mulai = data.get('jam_mulai')
    jam_selesai = data.get('jam_selesai')
    wilayah = data.get('wilayah')
    petugas_ids = data.get('petugas_ids', [])  # array of petugas IDs
    status = data.get('status', 'aktif')

    # Validasi
    if not tanggal or not jam_mulai or not jam_selesai or not wilayah:
        return jsonify({
            "success": False,
            "message": "tanggal, jam_mulai, jam_selesai, dan wilayah wajib diisi"
        }), 400

    if not petugas_ids or len(petugas_ids) == 0:
        return jsonify({
            "success": False,
            "message": "Minimal pilih 1 petugas"
        }), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Validasi semua petugas ada
            placeholders = ','.join(['%s'] * len(petugas_ids))
            sql = f"SELECT id FROM petugas WHERE id IN ({placeholders})"
            cursor.execute(sql, petugas_ids)
            existing_petugas = [row['id'] for row in cursor.fetchall()]

            if len(existing_petugas) != len(petugas_ids):
                return jsonify({
                    "success": False,
                    "message": "Beberapa petugas tidak ditemukan"
                }), 400

            # ===== INSERT jadwal =====
            sql_insert_jadwal = """
                INSERT INTO jadwal 
                (tanggal, jam_mulai, jam_selesai, wilayah, status)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql_insert_jadwal, (
                tanggal,
                jam_mulai + ":00" if len(jam_mulai) == 5 else jam_mulai,
                jam_selesai + ":00" if len(jam_selesai) == 5 else jam_selesai,
                wilayah,
                status
            ))
            jadwal_id = cursor.lastrowid

            # ===== INSERT ke jadwal_petugas =====
            for pid in petugas_ids:
                cursor.execute(
                    "INSERT INTO jadwal_petugas (jadwal_id, petugas_id) VALUES (%s, %s)",
                    (jadwal_id, pid)
                )

            conn.commit()

        return jsonify({
            "success": True,
            "message": f"Jadwal berhasil dibuat untuk {len(petugas_ids)} petugas",
            "jadwal_id": jadwal_id
        }), 201

    except Exception as e:
        conn.rollback()
        print("create_jadwal_multi error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()


@jadwal_bp.route('/list', methods=['GET'])
def list_jadwal():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT j.id, 
                       DATE_FORMAT(j.tanggal, '%Y-%m-%d') as tanggal,  # Format tanggal
                       TIME_FORMAT(j.jam_mulai, '%H:%i:%s') as jam_mulai,
                       TIME_FORMAT(j.jam_selesai, '%H:%i:%s') as jam_selesai,
                       j.wilayah, j.status, 
                       GROUP_CONCAT(p.nama_petugas SEPARATOR ', ') AS nama_petugas
                FROM jadwal j
                LEFT JOIN jadwal_petugas jp ON j.id = jp.jadwal_id
                LEFT JOIN petugas p ON jp.petugas_id = p.id
                GROUP BY j.id
                ORDER BY j.tanggal DESC, j.jam_mulai ASC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()

        return jsonify({"success": True, "data": rows}), 200
    except Exception as e:
        print("list_jadwal error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()
@jadwal_bp.route('/<int:jadwal_id>', methods=['GET'])
def get_jadwal_by_id(jadwal_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Ambil data jadwal
            sql = """
                SELECT j.id, j.tanggal, j.jam_mulai, j.jam_selesai,
                       j.wilayah, j.status
                FROM jadwal j
                WHERE j.id = %s
            """
            cursor.execute(sql, (jadwal_id,))
            jadwal = cursor.fetchone()

            if not jadwal:
                return jsonify({"success": False, "message": "Data jadwal tidak ditemukan"}), 404

            # Convert jam ke string
            if jadwal.get('jam_mulai'):
                jadwal['jam_mulai'] = str(jadwal['jam_mulai'])
            if jadwal.get('jam_selesai'):
                jadwal['jam_selesai'] = str(jadwal['jam_selesai'])

            # Ambil daftar petugas dari jadwal_petugas
            cursor.execute("SELECT petugas_id FROM jadwal_petugas WHERE jadwal_id = %s", (jadwal_id,))
            petugas_rows = cursor.fetchall()
            jadwal['petugas_ids'] = [r['petugas_id'] for r in petugas_rows]

        return jsonify({"success": True, "data": jadwal}), 200
    except Exception as e:
        print("get_jadwal_by_id error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()


@jadwal_bp.route('/<int:jadwal_id>', methods=['PATCH'])
def update_jadwal(jadwal_id):
    data = request.json or {}

    tanggal = data.get('tanggal')
    jam_mulai = data.get('jam_mulai')
    jam_selesai = data.get('jam_selesai')
    wilayah = data.get('wilayah')
    status = data.get('status', 'aktif')
    petugas_ids = data.get('petugas_ids', [])
    
     # Validasi tanggal
    try:
        datetime.strptime(tanggal, "%Y-%m-%d")
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal harus YYYY-MM-DD"}), 400

    if not tanggal or not jam_mulai or not jam_selesai or not wilayah:
        return jsonify({"success": False, "message": "tanggal, jam_mulai, jam_selesai, dan wilayah wajib diisi"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Update data jadwal
            sql_update = """
                UPDATE jadwal
                SET tanggal=%s, jam_mulai=%s, jam_selesai=%s, wilayah=%s, status=%s
                WHERE id=%s
            """
            cursor.execute(sql_update, (
                tanggal,
                jam_mulai,
                jam_selesai,
                wilayah,
                status,
                jadwal_id
            ))

            # Hapus petugas lama di jadwal_petugas
            cursor.execute("DELETE FROM jadwal_petugas WHERE jadwal_id=%s", (jadwal_id,))

            # Insert petugas baru
            for pid in petugas_ids:
                cursor.execute("INSERT INTO jadwal_petugas (jadwal_id, petugas_id) VALUES (%s,%s)", (jadwal_id, pid))

            conn.commit()

        return jsonify({"success": True, "message": "Jadwal berhasil diperbarui"}), 200
    except Exception as e:
        conn.rollback()
        print("update_jadwal error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

@jadwal_bp.route('/<int:jadwal_id>/toggle-status', methods=['PATCH'])
def toggle_jadwal_status(jadwal_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Cek jadwal ada
            cursor.execute("SELECT status FROM jadwal WHERE id = %s", (jadwal_id,))
            jadwal = cursor.fetchone()
            
            if not jadwal:
                return jsonify({"success": False, "message": "Jadwal tidak ditemukan"}), 404
            
            # Toggle status
            new_status = 'nonaktif' if jadwal['status'] == 'aktif' else 'aktif'
            
            cursor.execute("UPDATE jadwal SET status = %s WHERE id = %s", (new_status, jadwal_id))
            conn.commit()
            
        return jsonify({
            "success": True,
            "message": f"Status jadwal berhasil diubah menjadi {new_status}",
            "new_status": new_status
        }), 200
        
    except Exception as e:
        conn.rollback()
        print("toggle_jadwal_status error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()