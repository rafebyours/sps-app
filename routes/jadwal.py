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

        # 🔹 convert jam ke string
        if 'jam_mulai' in row and row['jam_mulai'] is not None:
            row['jam_mulai'] = str(row['jam_mulai'])
        if 'jam_selesai' in row and row['jam_selesai'] is not None:
            row['jam_selesai'] = str(row['jam_selesai'])

        return jsonify({"success": True, "data": row}), 200
    except Exception as e:
        print("get_jadwal_by_id error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

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

            # Insert jadwal untuk setiap petugas
            jadwal_ids = []
            for petugas_id in petugas_ids:
                sql_insert = """
                    INSERT INTO jadwal 
                    (tanggal, jam_mulai, jam_selesai, wilayah, id_petugas, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_insert, (
                    tanggal,
                    jam_mulai + ":00" if len(jam_mulai) == 5 else jam_mulai,
                    jam_selesai + ":00" if len(jam_selesai) == 5 else jam_selesai,
                    wilayah,
                    petugas_id,
                    status
                ))
                jadwal_ids.append(cursor.lastrowid)

            conn.commit()

        return jsonify({
            "success": True,
            "message": f"Jadwal berhasil dibuat untuk {len(petugas_ids)} petugas",
            "jadwal_ids": jadwal_ids
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
                SELECT j.id, j.tanggal, j.jam_mulai, j.jam_selesai, j.wilayah,
                       j.status, p.nama_petugas
                FROM jadwal j
                LEFT JOIN petugas p ON j.id_petugas = p.id
                ORDER BY j.tanggal DESC, j.jam_mulai ASC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()

            # convert jam ke string supaya JSON friendly
            for r in rows:
                if r.get('jam_mulai'):
                    r['jam_mulai'] = str(r['jam_mulai'])
                if r.get('jam_selesai'):
                    r['jam_selesai'] = str(r['jam_selesai'])

        return jsonify({"success": True, "data": rows}), 200
    except Exception as e:
        print("list_jadwal error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()
