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


# routes/jadwal.py
# Di endpoint /list
@jadwal_bp.route('/list', methods=['GET'])
def list_jadwal():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT j.id, 
                       DATE_FORMAT(j.tanggal, '%Y-%m-%d') as tanggal,
                       TIME_FORMAT(j.jam_mulai, '%H:%i:%s') as jam_mulai,
                       TIME_FORMAT(j.jam_selesai, '%H:%i:%s') as jam_selesai,
                       j.wilayah, j.keterangan, j.status, 
                       GROUP_CONCAT(p.nama_lengkap SEPARATOR ', ') AS nama_petugas  # <-- PERUBAHAN DI SINI
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

# Di endpoint /today
@jadwal_bp.route('/today', methods=['GET'])
def get_today_jadwal_user():
    today = date.today().strftime("%Y-%m-%d")

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT j.id, 
                       DATE_FORMAT(j.tanggal, '%Y-%m-%d') as tanggal,
                       TIME_FORMAT(j.jam_mulai, '%H:%i:%s') as jam_mulai,
                       TIME_FORMAT(j.jam_selesai, '%H:%i:%s') as jam_selesai,
                       j.wilayah, j.status,
                       GROUP_CONCAT(p.nama_lengkap SEPARATOR ', ') AS nama_petugas  # <-- PERUBAHAN DI SINI
                FROM jadwal j
                LEFT JOIN jadwal_petugas jp ON j.id = jp.jadwal_id
                LEFT JOIN petugas p ON jp.petugas_id = p.id
                WHERE j.tanggal = %s
                  AND j.status = 'aktif'
                GROUP BY j.id
                ORDER BY j.jam_mulai ASC
            """
            cursor.execute(sql, (today,))
            rows = cursor.fetchall()

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

# Di endpoint /next
@jadwal_bp.route('/next', methods=['GET'])
def get_next_jadwal():
    today = date.today()

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT j.id, 
                       DATE_FORMAT(j.tanggal, '%Y-%m-%d') as tanggal,
                       TIME_FORMAT(j.jam_mulai, '%H:%i:%s') as jam_mulai,
                       TIME_FORMAT(j.jam_selesai, '%H:%i:%s') as jam_selesai,
                       j.wilayah, j.status,
                       GROUP_CONCAT(p.nama_lengkap SEPARATOR ', ') AS nama_petugas  # <-- PERUBAHAN DI SINI
                FROM jadwal j
                LEFT JOIN jadwal_petugas jp ON j.id = jp.jadwal_id
                LEFT JOIN petugas p ON jp.petugas_id = p.id
                WHERE j.tanggal >= %s
                  AND j.status = 'aktif'
                GROUP BY j.id
                ORDER BY j.tanggal ASC, j.jam_mulai ASC
                LIMIT 1
            """
            cursor.execute(sql, (today,))
            row = cursor.fetchone()

        return jsonify({
            "success": True,
            "data": row
        }), 200

    except Exception as e:
        print("get_next_jadwal error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# Di endpoint /week
@jadwal_bp.route('/week', methods=['GET'])
def get_next_week_jadwal():
    today = date.today()
    week_ahead = today + timedelta(days=7)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT j.id, 
                       DATE_FORMAT(j.tanggal, '%Y-%m-%d') as tanggal,
                       TIME_FORMAT(j.jam_mulai, '%H:%i:%s') as jam_mulai,
                       TIME_FORMAT(j.jam_selesai, '%H:%i:%s') as jam_selesai,
                       j.wilayah, j.status,
                       GROUP_CONCAT(p.nama_lengkap SEPARATOR ', ') AS nama_petugas  # <-- PERUBAHAN DI SINI
                FROM jadwal j
                LEFT JOIN jadwal_petugas jp ON j.id = jp.jadwal_id
                LEFT JOIN petugas p ON jp.petugas_id = p.id
                WHERE j.tanggal BETWEEN %s AND %s
                GROUP BY j.id
                ORDER BY j.tanggal ASC, j.jam_mulai ASC
            """

            cursor.execute(sql, (today, week_ahead))
            rows = cursor.fetchall()

        return jsonify({"success": True, "data": rows}), 200

    except Exception as e:
        print("get_next_week_jadwal error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()
        
@jadwal_bp.route('/', methods=['GET']) 
def get_all_jadwal():
    status = request.args.get('status')      
    id_petugas = request.args.get('id_petugas') 

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            base_sql = """
                SELECT j.id, 
                       DATE_FORMAT(j.tanggal, '%Y-%m-%d') as tanggal,
                       TIME_FORMAT(j.jam_mulai, '%H:%i:%s') as jam_mulai,
                       TIME_FORMAT(j.jam_selesai, '%H:%i:%s') as jam_selesai,
                       j.wilayah, j.status
                FROM jadwal j
                WHERE 1=1
            """
            params = []

            if status:
                base_sql += " AND j.status = %s"
                params.append(status)
            if id_petugas:
                # Karena sekarang multiple petugas, filter perlu diubah
                # atau bisa dihapus dulu jika tidak diperlukan
                pass  # Hapus filter id_petugas karena tidak relevan lagi

            base_sql += " ORDER BY j.tanggal DESC, j.jam_mulai ASC"

            cursor.execute(base_sql, params)
            rows = cursor.fetchall()

        return jsonify({"success": True, "data": rows}), 200
    except Exception as e:
        print("get_all_jadwal error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()
        
# POST /api/jadwal/multi - Create dengan multiple petugas
@jadwal_bp.route('/multi', methods=['POST'])
def create_jadwal_multi():
    data = request.json or {}

    tanggal = data.get('tanggal')
    jam_mulai = data.get('jam_mulai')
    jam_selesai = data.get('jam_selesai')
    wilayah = data.get('wilayah')
    keterangan = data.get('keterangan', '')
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

    # Validasi tanggal
    try:
        datetime.strptime(tanggal, "%Y-%m-%d")
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal harus YYYY-MM-DD"}), 400

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
                (tanggal, jam_mulai, jam_selesai, wilayah, keterangan, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            # Normalize time format
            jam_mulai_norm = jam_mulai + ":00" if len(jam_mulai) == 5 else jam_mulai
            jam_selesai_norm = jam_selesai + ":00" if len(jam_selesai) == 5 else jam_selesai
            
            cursor.execute(sql_insert_jadwal, (
                tanggal,
                jam_mulai_norm,
                jam_selesai_norm,
                wilayah,
                keterangan,
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

# GET /api/jadwal/<id> - Get detail jadwal dengan petugas_ids
# routes/jadwal.py - di fungsi get_jadwal_by_id
@jadwal_bp.route('/<int:jadwal_id>', methods=['GET'])
def get_jadwal_by_id(jadwal_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT j.id, 
                       DATE_FORMAT(j.tanggal, '%%Y-%%m-%%d') as tanggal,
                       TIME_FORMAT(j.jam_mulai, '%%H:%%i:%%s') as jam_mulai,
                       TIME_FORMAT(j.jam_selesai, '%%H:%%i:%%s') as jam_selesai,
                       j.wilayah, j.keterangan, j.status
                FROM jadwal j
                WHERE j.id = %s
            """
            cursor.execute(sql, (jadwal_id,))
            jadwal = cursor.fetchone()

            if not jadwal:
                return jsonify({"success": False, "message": "Data jadwal tidak ditemukan"}), 404

            # Ambil daftar petugas dari jadwal_petugas
            cursor.execute("SELECT petugas_id FROM jadwal_petugas WHERE jadwal_id = %s", (jadwal_id,))
            petugas_rows = cursor.fetchall()
            petugas_ids = [r['petugas_id'] for r in petugas_rows]
            
            # Debug logging
            print(f"Jadwal ID {jadwal_id} - Petugas IDs: {petugas_ids}")
            
            jadwal['petugas_ids'] = petugas_ids

        return jsonify({
            "success": True, 
            "data": jadwal,
            "debug": {
                "petugas_ids_count": len(petugas_ids),
                "petugas_ids": petugas_ids
            }
        }), 200
    except Exception as e:
        print(f"get_jadwal_by_id error for id {jadwal_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    finally:
        conn.close()

# PATCH /api/jadwal/<id> - Update jadwal dengan multiple petugas
@jadwal_bp.route('/<int:jadwal_id>', methods=['PATCH'])
def update_jadwal(jadwal_id):
    data = request.json or {}

    tanggal = data.get('tanggal')
    jam_mulai = data.get('jam_mulai')
    jam_selesai = data.get('jam_selesai')
    wilayah = data.get('wilayah')
    keterangan = data.get('keterangan', '')
    status = data.get('status', 'aktif')
    petugas_ids = data.get('petugas_ids', [])
    
    # Validasi
    if not tanggal or not jam_mulai or not jam_selesai or not wilayah:
        return jsonify({"success": False, "message": "tanggal, jam_mulai, jam_selesai, dan wilayah wajib diisi"}), 400

    # Validasi tanggal
    try:
        datetime.strptime(tanggal, "%Y-%m-%d")
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal harus YYYY-MM-DD"}), 400

    # Validasi petugas
    if not petugas_ids or len(petugas_ids) == 0:
        return jsonify({"success": False, "message": "Minimal pilih 1 petugas"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Update data jadwal
            sql_update = """
                UPDATE jadwal
                SET tanggal=%s, 
                    jam_mulai=%s, 
                    jam_selesai=%s, 
                    wilayah=%s, 
                    keterangan=%s,
                    status=%s
                WHERE id=%s
            """
            
            # Normalize time format
            jam_mulai_norm = jam_mulai + ":00" if len(jam_mulai) == 5 else jam_mulai
            jam_selesai_norm = jam_selesai + ":00" if len(jam_selesai) == 5 else jam_selesai
            
            cursor.execute(sql_update, (
                tanggal,
                jam_mulai_norm,
                jam_selesai_norm,
                wilayah,
                keterangan,
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

# PATCH /api/jadwal/<id>/toggle-status - Toggle status
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

# DELETE /api/jadwal/<id>
@jadwal_bp.route('/<int:jadwal_id>', methods=['DELETE'])
def delete_jadwal(jadwal_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Cek jadwal ada
            cursor.execute("SELECT id FROM jadwal WHERE id = %s", (jadwal_id,))
            jadwal = cursor.fetchone()
            
            if not jadwal:
                return jsonify({"success": False, "message": "Jadwal tidak ditemukan"}), 404
            
            # Hapus (cascade akan menghapus relasi di jadwal_petugas)
            cursor.execute("DELETE FROM jadwal WHERE id = %s", (jadwal_id,))
            conn.commit()
            
        return jsonify({
            "success": True,
            "message": "Jadwal berhasil dihapus"
        }), 200
        
    except Exception as e:
        conn.rollback()
        print("delete_jadwal error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# TIDAK PERLU FUNGSI INI LAGI KARENA SUDAH ADA DI ATAS:
# @jadwal_bp.route('/today', methods=['GET'])
# def get_today_jadwal_user():
#     # HAPUS SEMUA KODE INI

