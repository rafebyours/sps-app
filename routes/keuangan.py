# routes/keuangan.py
from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG
from datetime import datetime
import random

keuangan_bp = Blueprint('keuangan', __name__, url_prefix='/api/keuangan')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

@keuangan_bp.route('/pemasukan', methods=['GET'])
def get_pemasukan():
    """Get all pemasukan (jenis = 'pemasukan')"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT 
                    id,
                    kode_transaksi,
                    'pemasukan' as tipe,
                    kategori,
                    jumlah,
                    keterangan,
                    DATE(tanggal) as tanggal,
                    DATE_FORMAT(tanggal, '%%Y-%%m-%%d') as tanggal_iso,
                    DATE_FORMAT(tanggal, '%%W') as hari_en,
                    status_bayar,
                    metode_bayar
                FROM transaksi 
                WHERE jenis = 'pemasukan'
                ORDER BY tanggal DESC
            """
            
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            # Convert English day names to Indonesian
            days_map = {
                'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
                'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu',
                'Sunday': 'Minggu'
            }
            
            for row in rows:
                # Format hari
                if row.get('hari_en'):
                    row['hari'] = days_map.get(row['hari_en'], row['hari_en'])
                else:
                    row['hari'] = ''
                
                # Remove hari_en
                if 'hari_en' in row:
                    del row['hari_en']
                
                # Ensure tanggal is string
                if 'tanggal' in row and row['tanggal']:
                    row['tanggal'] = str(row['tanggal'])
            
            return jsonify({
                "success": True,
                "data": rows,
                "message": f"Found {len(rows)} pemasukan records"
            }), 200
            
    except Exception as e:
        print(f"Error in get_pemasukan: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal mengambil data pemasukan",
            "error": str(e)
        }), 500
    finally:
        conn.close()

@keuangan_bp.route('/pengeluaran', methods=['GET'])
def get_pengeluaran():
    """Get all pengeluaran (jenis = 'pengeluaran' OR 'gaji')"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT 
                    id,
                    kode_transaksi,
                    jenis as tipe,
                    kategori,
                    jumlah,
                    keterangan,
                    DATE(tanggal) as tanggal,
                    DATE_FORMAT(tanggal, '%%Y-%%m-%%d') as tanggal_iso,
                    DATE_FORMAT(tanggal, '%%W') as hari_en,
                    status_bayar,
                    metode_bayar
                FROM transaksi 
                WHERE jenis IN ('pengeluaran', 'gaji')
                ORDER BY tanggal DESC
            """
            
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            # Convert English day names to Indonesian
            days_map = {
                'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
                'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu',
                'Sunday': 'Minggu'
            }
            
            for row in rows:
                # Format hari
                if row.get('hari_en'):
                    row['hari'] = days_map.get(row['hari_en'], row['hari_en'])
                else:
                    row['hari'] = ''
                
                # Remove hari_en
                if 'hari_en' in row:
                    del row['hari_en']
                
                # Ensure tanggal is string
                if 'tanggal' in row and row['tanggal']:
                    row['tanggal'] = str(row['tanggal'])
            
            return jsonify({
                "success": True,
                "data": rows,
                "message": f"Found {len(rows)} pengeluaran records"
            }), 200
            
    except Exception as e:
        print(f"Error in get_pengeluaran: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal mengambil data pengeluaran",
            "error": str(e)
        }), 500
    finally:
        conn.close()

@keuangan_bp.route('/pemasukan', methods=['POST'])
def create_pemasukan():
    """Create new pemasukan"""
    data = request.get_json()
    
    required_fields = ['tanggal', 'jumlah', 'kategori', 'keterangan']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                "success": False,
                "message": f"Field '{field}' wajib diisi"
            }), 400
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Generate kode transaksi untuk PEMASUKAN
            kode = f"PM-{datetime.now().strftime('%y%m%d')}-{random.randint(1000, 9999)}"
            
            # Insert into transaksi table
            sql = """
                INSERT INTO transaksi (
                    kode_transaksi,
                    jenis,
                    kategori,
                    jumlah,
                    keterangan,
                    tanggal,
                    status_bayar,
                    metode_bayar,
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(sql, (
                kode,
                'pemasukan',
                data['kategori'],
                float(data['jumlah']),
                data['keterangan'],
                data['tanggal'],
                data.get('status_bayar', 'lunas'),
                data.get('metode_bayar', 'cash'),
            ))
            
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": "Pemasukan berhasil ditambahkan",
                "data": {
                    "id": cursor.lastrowid,
                    "kode_transaksi": kode
                }
            }), 201
            
    except Exception as e:
        conn.rollback()
        print(f"Error in create_pemasukan: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal menambah pemasukan",
            "error": str(e)
        }), 500
    finally:
        conn.close()

@keuangan_bp.route('/pengeluaran', methods=['POST'])
def create_pengeluaran():
    """Create new pengeluaran"""
    data = request.get_json()
    
    required_fields = ['tanggal', 'jumlah', 'kategori', 'keterangan']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                "success": False,
                "message": f"Field '{field}' wajib diisi"
            }), 400
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Generate kode transaksi untuk PENGELUARAN
            kode = f"PL-{datetime.now().strftime('%y%m%d')}-{random.randint(1000, 9999)}"
            
            # Determine jenis based on kategori
            jenis = 'gaji' if data['kategori'] == 'Gaji Petugas' else 'pengeluaran'
            
            # Insert into transaksi table
            sql = """
                INSERT INTO transaksi (
                    kode_transaksi,
                    jenis,
                    kategori,
                    jumlah,
                    keterangan,
                    tanggal,
                    status_bayar,
                    metode_bayar,
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(sql, (
                kode,
                jenis,
                data['kategori'],
                float(data['jumlah']),
                data['keterangan'],
                data['tanggal'],
                data.get('status_bayar', 'lunas'),
                data.get('metode_bayar', 'cash'),
            ))
            
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": "Pengeluaran berhasil ditambahkan",
                "data": {
                    "id": cursor.lastrowid,
                    "kode_transaksi": kode
                }
            }), 201
            
    except Exception as e:
        conn.rollback()
        print(f"Error in create_pengeluaran: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal menambah pengeluaran",
            "error": str(e)
        }), 500
    finally:
        conn.close()

@keuangan_bp.route('/pemasukan/<int:id>', methods=['PUT'])
def update_pemasukan(id):
    """Update pemasukan"""
    data = request.get_json()
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                UPDATE transaksi 
                SET kategori = %s,
                    jumlah = %s,
                    keterangan = %s,
                    tanggal = %s,
                    status_bayar = %s,
                    metode_bayar = %s
                WHERE id = %s AND jenis = 'pemasukan'
            """
            
            cursor.execute(sql, (
                data['kategori'],
                float(data['jumlah']),
                data['keterangan'],
                data['tanggal'],
                data.get('status_bayar', 'lunas'),
                data.get('metode_bayar', 'cash'),
                id
            ))
            
            conn.commit()
            
            if cursor.rowcount == 0:
                return jsonify({
                    "success": False,
                    "message": "Pemasukan tidak ditemukan"
                }), 404
            
            return jsonify({
                "success": True,
                "message": "Pemasukan berhasil diperbarui"
            }), 200
            
    except Exception as e:
        conn.rollback()
        print(f"Error in update_pemasukan: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal memperbarui pemasukan",
            "error": str(e)
        }), 500
    finally:
        conn.close()

@keuangan_bp.route('/pengeluaran/<int:id>', methods=['PUT'])
def update_pengeluaran(id):
    """Update pengeluaran"""
    data = request.get_json()
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Determine jenis based on kategori
            jenis = 'gaji' if data['kategori'] == 'Gaji Petugas' else 'pengeluaran'
            
            sql = """
                UPDATE transaksi 
                SET kategori = %s,
                    jumlah = %s,
                    keterangan = %s,
                    tanggal = %s,
                    jenis = %s,
                    status_bayar = %s,
                    metode_bayar = %s
                WHERE id = %s AND jenis IN ('pengeluaran', 'gaji')
            """
            
            cursor.execute(sql, (
                data['kategori'],
                float(data['jumlah']),
                data['keterangan'],
                data['tanggal'],
                jenis,
                data.get('status_bayar', 'lunas'),
                data.get('metode_bayar', 'cash'),
                id
            ))
            
            conn.commit()
            
            if cursor.rowcount == 0:
                return jsonify({
                    "success": False,
                    "message": "Pengeluaran tidak ditemukan"
                }), 404
            
            return jsonify({
                "success": True,
                "message": "Pengeluaran berhasil diperbarui"
            }), 200
            
    except Exception as e:
        conn.rollback()
        print(f"Error in update_pengeluaran: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal memperbarui pengeluaran",
            "error": str(e)
        }), 500
    finally:
        conn.close()

@keuangan_bp.route('/pemasukan/<int:id>', methods=['DELETE'])
def delete_pemasukan(id):
    """Delete pemasukan"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "DELETE FROM transaksi WHERE id = %s AND jenis = 'pemasukan'"
            cursor.execute(sql, (id,))
            conn.commit()
            
            if cursor.rowcount == 0:
                return jsonify({
                    "success": False,
                    "message": "Pemasukan tidak ditemukan"
                }), 404
            
            return jsonify({
                "success": True,
                "message": "Pemasukan berhasil dihapus"
            }), 200
            
    except Exception as e:
        conn.rollback()
        print(f"Error in delete_pemasukan: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal menghapus pemasukan",
            "error": str(e)
        }), 500
    finally:
        conn.close()

@keuangan_bp.route('/pengeluaran/<int:id>', methods=['DELETE'])
def delete_pengeluaran(id):
    """Delete pengeluaran"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "DELETE FROM transaksi WHERE id = %s AND jenis IN ('pengeluaran', 'gaji')"
            cursor.execute(sql, (id,))
            conn.commit()
            
            if cursor.rowcount == 0:
                return jsonify({
                    "success": False,
                    "message": "Pengeluaran tidak ditemukan"
                }), 404
            
            return jsonify({
                "success": True,
                "message": "Pengeluaran berhasil dihapus"
            }), 200
            
    except Exception as e:
        conn.rollback()
        print(f"Error in delete_pengeluaran: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal menghapus pengeluaran",
            "error": str(e)
        }), 500
    finally:
        conn.close()

@keuangan_bp.route('/summary', methods=['GET'])
def get_keuangan_summary():
    """Get financial summary"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Total pemasukan
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_transaksi,
                    SUM(jumlah) as total_jumlah
                FROM transaksi 
                WHERE jenis = 'pemasukan'
            """)
            pemasukan = cursor.fetchone()
            
            # Total pengeluaran
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_transaksi,
                    SUM(jumlah) as total_jumlah
                FROM transaksi 
                WHERE jenis IN ('pengeluaran', 'gaji')
            """)
            pengeluaran = cursor.fetchone()
            
            # This month
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN jenis = 'pemasukan' THEN jumlah ELSE 0 END) as pemasukan_bulan_ini,
                    SUM(CASE WHEN jenis IN ('pengeluaran', 'gaji') THEN jumlah ELSE 0 END) as pengeluaran_bulan_ini
                FROM transaksi 
                WHERE MONTH(tanggal) = MONTH(CURDATE())
                AND YEAR(tanggal) = YEAR(CURDATE())
            """)
            bulan_ini = cursor.fetchone()
            
            # Today
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN jenis = 'pemasukan' THEN jumlah ELSE 0 END) as pemasukan_hari_ini,
                    SUM(CASE WHEN jenis IN ('pengeluaran', 'gaji') THEN jumlah ELSE 0 END) as pengeluaran_hari_ini
                FROM transaksi 
                WHERE DATE(tanggal) = CURDATE()
            """)
            hari_ini = cursor.fetchone()
            
            # Categories summary
            cursor.execute("""
                SELECT 
                    kategori,
                    COUNT(*) as jumlah,
                    SUM(jumlah) as total
                FROM transaksi 
                WHERE jenis IN ('pengeluaran', 'gaji')
                GROUP BY kategori
                ORDER BY total DESC
                LIMIT 5
            """)
            kategori_pengeluaran = cursor.fetchall()
            
            return jsonify({
                "success": True,
                "data": {
                    "pemasukan": pemasukan or {"total_transaksi": 0, "total_jumlah": 0},
                    "pengeluaran": pengeluaran or {"total_transaksi": 0, "total_jumlah": 0},
                    "bulan_ini": bulan_ini or {"pemasukan_bulan_ini": 0, "pengeluaran_bulan_ini": 0},
                    "hari_ini": hari_ini or {"pemasukan_hari_ini": 0, "pengeluaran_hari_ini": 0},
                    "kategori_pengeluaran": kategori_pengeluaran
                }
            }), 200
            
    except Exception as e:
        print(f"Error in get_keuangan_summary: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal mengambil summary keuangan"
        }), 500
    finally:
        conn.close()