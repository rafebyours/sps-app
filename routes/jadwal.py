from flask import Blueprint, request, jsonify, make_response, current_app
import pymysql
from config import DB_CONFIG
from datetime import datetime, date, timedelta
import json

jadwal_bp = Blueprint('jadwal', __name__, url_prefix='/api/jadwal')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

def send_jadwal_notification_safe(jadwal_id, action='created'):
    """Safe wrapper to send jadwal notification"""
    try:
        from app import send_jadwal_notification
        
        conn = get_connection()
        with conn.cursor() as cursor:
            # Get complete jadwal data
            sql = """
                SELECT j.*, 
                       GROUP_CONCAT(DISTINCT p.nama_lengkap SEPARATOR ', ') as nama_petugas,
                       GROUP_CONCAT(DISTINCT jp.petugas_id) as petugas_ids
                FROM jadwal j
                LEFT JOIN jadwal_petugas jp ON j.id = jp.jadwal_id
                LEFT JOIN petugas p ON jp.petugas_id = p.id
                WHERE j.id = %s
                GROUP BY j.id
            """
            cursor.execute(sql, (jadwal_id,))
            jadwal_data = cursor.fetchone()
            
            if jadwal_data:
                # Format petugas_ids
                if jadwal_data['petugas_ids']:
                    jadwal_data['petugas_ids'] = [int(pid) for pid in jadwal_data['petugas_ids'].split(',') if pid]
                else:
                    jadwal_data['petugas_ids'] = []
                
                # Format tanggal
                if 'tanggal' in jadwal_data and jadwal_data['tanggal']:
                    if isinstance(jadwal_data['tanggal'], date):
                        jadwal_data['tanggal'] = jadwal_data['tanggal'].strftime('%Y-%m-%d')
                
                # Send notification
                send_jadwal_notification(jadwal_data, action)
                print(f"✅ Notification sent for jadwal {jadwal_id} ({action})")
        
        conn.close()
        
    except Exception as e:
        print(f"⚠️ Failed to send notification for jadwal {jadwal_id}: {e}")
        # Don't fail the main operation if notification fails

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

# ==================== JADWAL ENDPOINTS WITH NOTIFICATIONS ====================
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
                    DATE_FORMAT(j.tanggal, '%%Y-%%m-%%d') as tanggal,
                    TIME_FORMAT(j.jam_mulai, '%%H:%%i:%%s') as jam_mulai,
                    TIME_FORMAT(j.jam_selesai, '%%H:%%i:%%s') as jam_selesai,
                    j.wilayah, j.status,
                    GROUP_CONCAT(p.nama_lengkap SEPARATOR ', ') AS nama_petugas
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
                    DATE_FORMAT(j.tanggal, '%%Y-%%m-%%d') as tanggal,
                    TIME_FORMAT(j.jam_mulai, '%%H:%%i:%%s') as jam_mulai,
                    TIME_FORMAT(j.jam_selesai, '%%H:%%i:%%s') as jam_selesai,
                    j.wilayah, j.status,
                    GROUP_CONCAT(p.nama_lengkap SEPARATOR ', ') AS nama_petugas
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
    """Create jadwal with multiple petugas - WITH NOTIFICATION"""
    data = request.json or {}

    tanggal = data.get('tanggal')
    jam_mulai = data.get('jam_mulai')
    jam_selesai = data.get('jam_selesai')
    wilayah = data.get('wilayah')
    keterangan = data.get('keterangan', '')
    petugas_ids = data.get('petugas_ids', [])
    status = data.get('status', 'aktif')

    # Validasi
    if not all([tanggal, jam_mulai, jam_selesai, wilayah]):
        return jsonify({
            "success": False,
            "message": "tanggal, jam_mulai, jam_selesai, dan wilayah wajib diisi"
        }), 400

    if not petugas_ids:
        return jsonify({
            "success": False,
            "message": "Minimal pilih 1 petugas"
        }), 400

    try:
        datetime.strptime(tanggal, "%Y-%m-%d")
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal harus YYYY-MM-DD"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Validasi petugas
            placeholders = ','.join(['%s'] * len(petugas_ids))
            sql = f"SELECT id FROM petugas WHERE id IN ({placeholders})"
            cursor.execute(sql, petugas_ids)
            existing_petugas = [row['id'] for row in cursor.fetchall()]

            if len(existing_petugas) != len(petugas_ids):
                return jsonify({
                    "success": False,
                    "message": "Beberapa petugas tidak ditemukan"
                }), 400

            # Insert jadwal
            sql_insert_jadwal = """
                INSERT INTO jadwal 
                (tanggal, jam_mulai, jam_selesai, wilayah, keterangan, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            jam_mulai_norm = jam_mulai + ":00" if len(jam_mulai) == 5 else jam_mulai
            jam_selesai_norm = jam_selesai + ":00" if len(jam_selesai) == 5 else jam_selesai
            
            cursor.execute(sql_insert_jadwal, (
                tanggal, jam_mulai_norm, jam_selesai_norm, 
                wilayah, keterangan, status
            ))
            jadwal_id = cursor.lastrowid

            # Insert petugas
            for pid in petugas_ids:
                cursor.execute(
                    "INSERT INTO jadwal_petugas (jadwal_id, petugas_id) VALUES (%s, %s)",
                    (jadwal_id, pid)
                )

            conn.commit()

            # SEND NOTIFICATION
            send_jadwal_notification_safe(jadwal_id, 'created')

        return jsonify({
            "success": True,
            "message": f"Jadwal berhasil dibuat untuk {len(petugas_ids)} petugas",
            "jadwal_id": jadwal_id,
            "notification_sent": True
        }), 201

    except Exception as e:
        conn.rollback()
        print(f"create_jadwal_multi error: {e}")
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
    """Update jadwal - WITH NOTIFICATION"""
    data = request.json or {}

    tanggal = data.get('tanggal')
    jam_mulai = data.get('jam_mulai')
    jam_selesai = data.get('jam_selesai')
    wilayah = data.get('wilayah')
    keterangan = data.get('keterangan')
    status = data.get('status')
    petugas_ids = data.get('petugas_ids')
    
    # Validasi minimal satu field diupdate
    if not any([tanggal, jam_mulai, jam_selesai, wilayah, keterangan, status, petugas_ids]):
        return jsonify({"success": False, "message": "Tidak ada data yang diupdate"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Cek jadwal exist
            cursor.execute("SELECT id FROM jadwal WHERE id = %s", (jadwal_id,))
            if not cursor.fetchone():
                return jsonify({"success": False, "message": "Jadwal tidak ditemukan"}), 404

            # Update jadwal
            update_fields = []
            params = []
            
            if tanggal:
                try:
                    datetime.strptime(tanggal, "%Y-%m-%d")
                    update_fields.append("tanggal = %s")
                    params.append(tanggal)
                except ValueError:
                    return jsonify({"success": False, "message": "Format tanggal harus YYYY-MM-DD"}), 400
            
            if jam_mulai:
                jam_mulai_norm = jam_mulai + ":00" if len(jam_mulai) == 5 else jam_mulai
                update_fields.append("jam_mulai = %s")
                params.append(jam_mulai_norm)
            
            if jam_selesai:
                jam_selesai_norm = jam_selesai + ":00" if len(jam_selesai) == 5 else jam_selesai
                update_fields.append("jam_selesai = %s")
                params.append(jam_selesai_norm)
            
            if wilayah:
                update_fields.append("wilayah = %s")
                params.append(wilayah)
            
            if keterangan is not None:
                update_fields.append("keterangan = %s")
                params.append(keterangan)
            
            if status:
                update_fields.append("status = %s")
                params.append(status)
            
            params.append(jadwal_id)
            
            if update_fields:
                sql_update = f"UPDATE jadwal SET {', '.join(update_fields)} WHERE id = %s"
                cursor.execute(sql_update, params)

            # Update petugas jika diberikan
            if petugas_ids is not None:
                if not petugas_ids:
                    return jsonify({"success": False, "message": "Minimal pilih 1 petugas"}), 400
                
                # Validasi petugas
                placeholders = ','.join(['%s'] * len(petugas_ids))
                sql = f"SELECT id FROM petugas WHERE id IN ({placeholders})"
                cursor.execute(sql, petugas_ids)
                existing_petugas = [row['id'] for row in cursor.fetchall()]

                if len(existing_petugas) != len(petugas_ids):
                    return jsonify({
                        "success": False,
                        "message": "Beberapa petugas tidak ditemukan"
                    }), 400
                
                # Hapus petugas lama
                cursor.execute("DELETE FROM jadwal_petugas WHERE jadwal_id = %s", (jadwal_id,))
                
                # Insert petugas baru
                for pid in petugas_ids:
                    cursor.execute(
                        "INSERT INTO jadwal_petugas (jadwal_id, petugas_id) VALUES (%s, %s)",
                        (jadwal_id, pid)
                    )

            conn.commit()

            # SEND NOTIFICATION
            send_jadwal_notification_safe(jadwal_id, 'updated')

        return jsonify({
            "success": True,
            "message": "Jadwal berhasil diperbarui",
            "notification_sent": True
        }), 200
        
    except Exception as e:
        conn.rollback()
        print(f"update_jadwal error: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# PATCH /api/jadwal/<id>/toggle-status - Toggle status
@jadwal_bp.route('/<int:jadwal_id>/toggle-status', methods=['PATCH'])
def toggle_jadwal_status(jadwal_id):
    """Toggle jadwal status - WITH NOTIFICATION"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Cek jadwal
            cursor.execute("SELECT status FROM jadwal WHERE id = %s", (jadwal_id,))
            jadwal = cursor.fetchone()
            
            if not jadwal:
                return jsonify({"success": False, "message": "Jadwal tidak ditemukan"}), 404
            
            # Toggle status
            new_status = 'nonaktif' if jadwal['status'] == 'aktif' else 'aktif'
            action = 'cancelled' if new_status == 'nonaktif' else 'updated'
            
            cursor.execute("UPDATE jadwal SET status = %s WHERE id = %s", (new_status, jadwal_id))
            conn.commit()
            
            # SEND NOTIFICATION
            send_jadwal_notification_safe(jadwal_id, action)

        return jsonify({
            "success": True,
            "message": f"Status jadwal berhasil diubah menjadi {new_status}",
            "new_status": new_status,
            "notification_sent": True
        }), 200
        
    except Exception as e:
        conn.rollback()
        print(f"toggle_jadwal_status error: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# DELETE /api/jadwal/<id>
@jadwal_bp.route('/<int:jadwal_id>', methods=['DELETE'])
def delete_jadwal(jadwal_id):
    """Delete jadwal - WITH NOTIFICATION"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Get jadwal data before deletion (for notification)
            cursor.execute("""
                SELECT j.*, 
                       GROUP_CONCAT(DISTINCT jp.petugas_id) as petugas_ids
                FROM jadwal j
                LEFT JOIN jadwal_petugas jp ON j.id = jp.jadwal_id
                WHERE j.id = %s
                GROUP BY j.id
            """, (jadwal_id,))
            jadwal_data = cursor.fetchone()
            
            if not jadwal_data:
                return jsonify({"success": False, "message": "Jadwal tidak ditemukan"}), 404
            
            # Format data for notification
            if jadwal_data['petugas_ids']:
                jadwal_data['petugas_ids'] = [int(pid) for pid in jadwal_data['petugas_ids'].split(',') if pid]
            
            # Delete jadwal
            cursor.execute("DELETE FROM jadwal WHERE id = %s", (jadwal_id,))
            conn.commit()
            
            # SEND NOTIFICATION
            try:
                from app import send_jadwal_notification
                send_jadwal_notification(jadwal_data, 'cancelled')
                print(f"✅ Deletion notification sent for jadwal {jadwal_id}")
            except Exception as notify_error:
                print(f"⚠️ Failed to send deletion notification: {notify_error}")

        return jsonify({
            "success": True,
            "message": "Jadwal berhasil dihapus",
            "notification_sent": True
        }), 200
        
    except Exception as e:
        conn.rollback()
        print(f"delete_jadwal error: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# routes/jadwal.py - Tambah endpoint baru
@jadwal_bp.route('/upcoming/warga/<int:warga_id>', methods=['GET'])
def get_upcoming_jadwal_warga(warga_id):
    """Get upcoming schedules for specific warga (based on wilayah)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Get wilayah warga
            cursor.execute("SELECT alamat, wilayah FROM warga WHERE id = %s", (warga_id,))
            warga = cursor.fetchone()
            
            if not warga:
                return jsonify({"success": False, "message": "Warga tidak ditemukan"}), 404
            
            # 2. Get jadwal untuk wilayah warga (7 hari ke depan)
            cursor.execute("""
                SELECT 
                    j.id,
                    j.wilayah,
                    j.tanggal,
                    DATE_FORMAT(j.jam_mulai, '%%H:%%i') as jam_mulai,
                    DATE_FORMAT(j.jam_selesai, '%%H:%%i') as jam_selesai,
                    j.keterangan,
                    j.status,
                    p.nama_lengkap as nama_petugas,
                    COUNT(l.id) as jumlah_pengajuan
                FROM jadwal j
                LEFT JOIN petugas p ON j.petugas_id = p.id
                LEFT JOIN laporan l ON j.id = l.id_jadwal 
                    AND l.id_warga = %s
                    AND l.status IN ('menunggu', 'diproses')
                WHERE j.wilayah = %s
                AND j.tanggal >= CURDATE()
                AND j.tanggal <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
                AND (j.status = 'aktif' OR j.status IS NULL)
                GROUP BY j.id
                ORDER BY j.tanggal ASC, j.jam_mulai ASC
            """, (warga_id, warga['wilayah']))
            
            jadwal_list = cursor.fetchall()
            
            # Format tanggal
            for jadwal in jadwal_list:
                jadwal['tanggal_formatted'] = format_date_display(jadwal['tanggal'])
                jadwal['is_today'] = str(jadwal['tanggal']) == datetime.now().strftime('%Y-%m-%d')
                jadwal['is_tomorrow'] = str(jadwal['tanggal']) == (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                
            return jsonify({
                "success": True,
                "data": jadwal_list,
                "message": f"Found {len(jadwal_list)} upcoming schedules"
            }), 200
            
    except Exception as e:
        print(f"Error in get_upcoming_jadwal_warga: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()

def format_date_display(date_str):
    """Format date untuk display"""
    if not date_str:
        return ""
    try:
        date_obj = datetime.strptime(str(date_str), '%Y-%m-%d')
        
        # Hari ini
        if date_obj.date() == datetime.now().date():
            return "Hari Ini"
        # Besok
        elif date_obj.date() == (datetime.now() + timedelta(days=1)).date():
            return "Besok"
        # Lainnya
        else:
            days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
            day_name = days[date_obj.weekday()]
            return f"{day_name}, {date_obj.strftime('%d %B')}"
    except:
        return str(date_str)
    
# routes/jadwal.py - Tambah endpoint baru
@jadwal_bp.route('/petugas/<int:petugas_id>', methods=['GET'])
def get_jadwal_by_petugas(petugas_id):
    """Get jadwal berdasarkan petugas"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Parameter untuk filtering
            tanggal = request.args.get('tanggal', '')
            status = request.args.get('status', 'aktif')
            
            print(f"Fetching jadwal for petugas_id: {petugas_id}, tanggal: {tanggal}, status: {status}")
            
            # Base query - UBAH QUERY INI
            sql = """
                SELECT DISTINCT
                    j.id,
                    DATE_FORMAT(j.tanggal, '%%Y-%%m-%%d') as tanggal,
                    TIME_FORMAT(j.jam_mulai, '%%H:%%i') as jam_mulai,
                    TIME_FORMAT(j.jam_selesai, '%%H:%%i') as jam_selesai,
                    j.wilayah,
                    j.keterangan,
                    j.status,
                    GROUP_CONCAT(DISTINCT p.nama_lengkap SEPARATOR ', ') as nama_petugas
                FROM jadwal j
                INNER JOIN jadwal_petugas jp ON j.id = jp.jadwal_id
                LEFT JOIN petugas p ON jp.petugas_id = p.id
                WHERE jp.petugas_id = %s
            """
            
            params = [petugas_id]
            
            # Filter tanggal
            if tanggal:
                sql += " AND DATE(j.tanggal) = %s"
                params.append(tanggal)
            else:
                # Default: jadwal hari ini dan yang akan datang
                sql += " AND DATE(j.tanggal) >= CURDATE()"
            
            # Filter status
            if status:
                sql += " AND j.status = %s"
                params.append(status)
            
            sql += """
                GROUP BY j.id, j.tanggal, j.jam_mulai, j.jam_selesai, j.wilayah, j.keterangan, j.status
                ORDER BY j.tanggal ASC, j.jam_mulai ASC
                LIMIT 10
            """
            
            print(f"SQL Query: {sql}")
            print(f"Params: {params}")
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            print(f"Found {len(rows)} jadwal records")
            
            # Format untuk frontend
            today_str = datetime.now().strftime('%Y-%m-%d')
            tomorrow_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            
            for row in rows:
                row['is_today'] = row['tanggal'] == today_str
                row['is_tomorrow'] = row['tanggal'] == tomorrow_str
                
                # Format display date
                try:
                    date_obj = datetime.strptime(row['tanggal'], '%Y-%m-%d')
                    days = ['Minggu', 'Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu']
                    day_name = days[date_obj.weekday()]
                    
                    if row['is_today']:
                        row['tanggal_display'] = f"Hari Ini ({day_name})"
                    elif row['is_tomorrow']:
                        row['tanggal_display'] = f"Besok ({day_name})"
                    else:
                        row['tanggal_display'] = f"{day_name}, {date_obj.strftime('%d %b %Y')}"
                except:
                    row['tanggal_display'] = row['tanggal']
            
            return jsonify({
                "success": True,
                "message": f"Found {len(rows)} jadwal",
                "data": rows,
                "debug": {
                    "petugas_id": petugas_id,
                    "tanggal_param": tanggal,
                    "status_param": status
                }
            }), 200
            
    except Exception as e:
        print(f"Error in get_jadwal_by_petugas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False, 
            "message": f"Server error: {str(e)}",
            "data": []
        }), 500
    finally:
        conn.close()