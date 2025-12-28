# routes/keuangan.py (buat file baru)
from flask import Blueprint, request, jsonify, make_response
import pymysql
from config import DB_CONFIG
from datetime import datetime, date, timedelta

keuangan_bp = Blueprint('keuangan', __name__, url_prefix='/api')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

@keuangan_bp.before_request
def handle_options():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        return response

@keuangan_bp.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response

# Pemasukan Endpoints
@keuangan_bp.route('/pemasukan', methods=['GET'])
def get_all_pemasukan():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT id, 
                       DATE_FORMAT(tanggal, '%%Y-%%m-%%d') as tanggal,
                       jumlah, kategori, keterangan,
                       DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:%%i:%%s') as created_at
                FROM pemasukan
                ORDER BY tanggal DESC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            
        return jsonify({"success": True, "data": rows}), 200
    except Exception as e:
        print("get_all_pemasukan error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

@keuangan_bp.route('/pemasukan', methods=['POST'])
def create_pemasukan():
    data = request.json or {}
    
    tanggal = data.get('tanggal')
    jumlah = data.get('jumlah')
    kategori = data.get('kategori')
    keterangan = data.get('keterangan', '')
    
    if not all([tanggal, jumlah, kategori, keterangan]):
        return jsonify({"success": False, "message": "Semua field wajib diisi"}), 400
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO pemasukan (tanggal, jumlah, kategori, keterangan)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (tanggal, jumlah, kategori, keterangan))
            conn.commit()
            
            pemasukan_id = cursor.lastrowid
            
        return jsonify({
            "success": True,
            "message": "Pemasukan berhasil ditambahkan",
            "id": pemasukan_id
        }), 201
    except Exception as e:
        conn.rollback()
        print("create_pemasukan error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

@keuangan_bp.route('/pemasukan/<int:id>', methods=['PUT'])
def update_pemasukan(id):
    data = request.json or {}
    
    tanggal = data.get('tanggal')
    jumlah = data.get('jumlah')
    kategori = data.get('kategori')
    keterangan = data.get('keterangan', '')
    
    if not all([tanggal, jumlah, kategori, keterangan]):
        return jsonify({"success": False, "message": "Semua field wajib diisi"}), 400
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Cek apakah data ada
            cursor.execute("SELECT id FROM pemasukan WHERE id = %s", (id,))
            if not cursor.fetchone():
                return jsonify({"success": False, "message": "Data tidak ditemukan"}), 404
            
            sql = """
                UPDATE pemasukan 
                SET tanggal = %s, jumlah = %s, kategori = %s, keterangan = %s
                WHERE id = %s
            """
            cursor.execute(sql, (tanggal, jumlah, kategori, keterangan, id))
            conn.commit()
            
        return jsonify({
            "success": True,
            "message": "Pemasukan berhasil diperbarui"
        }), 200
    except Exception as e:
        conn.rollback()
        print("update_pemasukan error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

@keuangan_bp.route('/pemasukan/<int:id>', methods=['DELETE'])
def delete_pemasukan(id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Cek apakah data ada
            cursor.execute("SELECT id FROM pemasukan WHERE id = %s", (id,))
            if not cursor.fetchone():
                return jsonify({"success": False, "message": "Data tidak ditemukan"}), 404
            
            cursor.execute("DELETE FROM pemasukan WHERE id = %s", (id,))
            conn.commit()
            
        return jsonify({
            "success": True,
            "message": "Pemasukan berhasil dihapus"
        }), 200
    except Exception as e:
        conn.rollback()
        print("delete_pemasukan error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# Pengeluaran Endpoints (sama seperti pemasukan, tinggal copy dan modifikasi tabelnya)
# Pengeluaran Endpoints (sama seperti pemasukan)
@keuangan_bp.route('/pengeluaran', methods=['POST'])
def create_pengeluaran():
    data = request.json or {}
    
    tanggal = data.get('tanggal')
    jumlah = data.get('jumlah')
    kategori = data.get('kategori')
    keterangan = data.get('keterangan', '')
    
    if not all([tanggal, jumlah, kategori, keterangan]):
        return jsonify({"success": False, "message": "Semua field wajib diisi"}), 400
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO pengeluaran (tanggal, jumlah, kategori, keterangan)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (tanggal, jumlah, kategori, keterangan))
            conn.commit()
            
            pengeluaran_id = cursor.lastrowid
            
        return jsonify({
            "success": True,
            "message": "Pengeluaran berhasil ditambahkan",
            "id": pengeluaran_id
        }), 201
    except Exception as e:
        conn.rollback()
        print("create_pengeluaran error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

@keuangan_bp.route('/pengeluaran', methods=['GET'])
def get_all_pengeluaran():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT id, 
                       DATE_FORMAT(tanggal, '%%Y-%%m-%%d') as tanggal,
                       jumlah, kategori, keterangan,
                       DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:%%i:%%s') as created_at
                FROM pengeluaran
                ORDER BY tanggal DESC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            
        return jsonify({"success": True, "data": rows}), 200
    except Exception as e:
        print("get_all_pengeluaran error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()
        
@keuangan_bp.route('/pengeluaran/<int:id>', methods=['PUT'])
def update_pengeluaran(id):
    data = request.json or {}
    
    tanggal = data.get('tanggal')
    jumlah = data.get('jumlah')
    kategori = data.get('kategori')
    keterangan = data.get('keterangan', '')
    
    if not all([tanggal, jumlah, kategori, keterangan]):
        return jsonify({"success": False, "message": "Semua field wajib diisi"}), 400
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Cek apakah data ada
            cursor.execute("SELECT id FROM pengeluaran WHERE id = %s", (id,))
            if not cursor.fetchone():
                return jsonify({"success": False, "message": "Data tidak ditemukan"}), 404
            
            sql = """
                UPDATE pengeluaran 
                SET tanggal = %s, jumlah = %s, kategori = %s, keterangan = %s
                WHERE id = %s
            """
            cursor.execute(sql, (tanggal, jumlah, kategori, keterangan, id))
            conn.commit()
            
        return jsonify({
            "success": True,
            "message": "Pengeluaran berhasil diperbarui"
        }), 200
    except Exception as e:
        conn.rollback()
        print("update_pengeluaran error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

@keuangan_bp.route('/pengeluaran/<int:id>', methods=['DELETE'])
def delete_pengeluaran(id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Cek apakah data ada
            cursor.execute("SELECT id FROM pengeluaran WHERE id = %s", (id,))
            if not cursor.fetchone():
                return jsonify({"success": False, "message": "Data tidak ditemukan"}), 404
            
            cursor.execute("DELETE FROM pengeluaran WHERE id = %s", (id,))
            conn.commit()
            
        return jsonify({
            "success": True,
            "message": "Pengeluaran berhasil dihapus"
        }), 200
    except Exception as e:
        conn.rollback()
        print("delete_pengeluaran error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# Stats Endpoint
@keuangan_bp.route('/keuangan/stats', methods=['GET'])
def get_keuangan_stats():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Total pemasukan bulan ini
            current_month = date.today().strftime('%Y-%m')
            sql_pemasukan = """
                SELECT COALESCE(SUM(jumlah), 0) as total
                FROM pemasukan
                WHERE DATE_FORMAT(tanggal, '%%Y-%%m') = %s
            """
            cursor.execute(sql_pemasukan, (current_month,))
            total_pemasukan = cursor.fetchone()['total']
            
            # Total pengeluaran bulan ini
            sql_pengeluaran = """
                SELECT COALESCE(SUM(jumlah), 0) as total
                FROM pengeluaran
                WHERE DATE_FORMAT(tanggal, '%%Y-%%m') = %s
            """
            cursor.execute(sql_pengeluaran, (current_month,))
            total_pengeluaran = cursor.fetchone()['total']
            
            # Saldo
            saldo = total_pemasukan - total_pengeluaran
            
            # 5 pemasukan terbaru
            sql_recent_pemasukan = """
                SELECT id, tanggal, jumlah, kategori, keterangan
                FROM pemasukan
                ORDER BY tanggal DESC
                LIMIT 5
            """
            cursor.execute(sql_recent_pemasukan)
            recent_pemasukan = cursor.fetchall()
            
            # 5 pengeluaran terbaru
            sql_recent_pengeluaran = """
                SELECT id, tanggal, jumlah, kategori, keterangan
                FROM pengeluaran
                ORDER BY tanggal DESC
                LIMIT 5
            """
            cursor.execute(sql_recent_pengeluaran)
            recent_pengeluaran = cursor.fetchall()
            
        return jsonify({
            "success": True,
            "data": {
                "total_pemasukan": float(total_pemasukan),
                "total_pengeluaran": float(total_pengeluaran),
                "saldo": float(saldo),
                "recent_pemasukan": recent_pemasukan,
                "recent_pengeluaran": recent_pengeluaran
            }
        }), 200
    except Exception as e:
        print("get_keuangan_stats error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()