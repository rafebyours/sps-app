# routes/riwayat_admin.py
from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG
from datetime import datetime, date as date_type

riwayat_admin_bp = Blueprint('riwayat_admin', __name__, url_prefix='/api/riwayat_admin')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

@riwayat_admin_bp.route('/', methods=['GET'])
def get_all_riwayat():
    """Menggabungkan pemasukan, pengeluaran, dan riwayat aktivitas"""
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Data Pemasukan (Transaksi Masuk)
            cursor.execute("""
                SELECT 
                    p.id,
                    p.tanggal,
                    'Pemasukan' AS type,
                    CONCAT('Pembayaran dari ', w.nama_warga, ' - ', p.jumlah_karung, ' karung') AS description,
                    p.jumlah_pembayaran AS amount,
                    p.jumlah_karung,
                    w.nama_warga,
                    NULL AS nama_petugas,
                    'Completed' AS status
                FROM pemasukan p
                LEFT JOIN warga w ON p.id_warga = w.id
                ORDER BY p.tanggal DESC
            """)
            pemasukan_data = cursor.fetchall()
            
            # 2. Data Pengeluaran (Transaksi Keluar)
            cursor.execute("""
                SELECT 
                    id,
                    tanggal,
                    'Pengeluaran' AS type,
                    CONCAT(jenis_pengeluaran, ' - ', nama_pengeluaran) AS description,
                    jumlah_pengeluaran AS amount,
                    NULL AS jumlah_karung,
                    NULL AS nama_warga,
                    NULL AS nama_petugas,
                    'Completed' AS status
                FROM pengeluaran
                ORDER BY tanggal DESC
            """)
            pengeluaran_data = cursor.fetchall()
            
            # 3. Data Riwayat Aktivitas
            cursor.execute("""
                SELECT 
                    r.id,
                    r.tanggal,
                    'Aktivitas' AS type,
                    CONCAT(
                        CASE 
                            WHEN w.nama_warga IS NOT NULL THEN CONCAT('Warga ', w.nama_warga)
                            WHEN p.nama_petugas IS NOT NULL THEN CONCAT('Petugas ', p.nama_petugas)
                            ELSE 'Sistem'
                        END,
                        ' - ', r.status
                    ) AS description,
                    NULL AS amount,
                    r.jumlah_karung,
                    w.nama_warga,
                    p.nama_petugas,
                    r.status
                FROM riwayat_aktivitas r
                LEFT JOIN warga w ON r.id_warga = w.id
                LEFT JOIN petugas p ON r.id_petugas = p.id
                ORDER BY r.tanggal DESC
            """)
            aktivitas_data = cursor.fetchall()
            
            # Gabungkan semua data
            all_data = pemasukan_data + pengeluaran_data + aktivitas_data
            
            # Sort berdasarkan tanggal (terbaru pertama)
            all_data.sort(key=lambda x: x['tanggal'], reverse=True)
            
            # Format tanggal
            for item in all_data:
                if item['tanggal']:
                    if isinstance(item['tanggal'], datetime):
                        item['tanggal'] = item['tanggal'].strftime("%Y-%m-%d %H:%M:%S")
                    elif isinstance(item['tanggal'], date_type):
                        item['tanggal'] = item['tanggal'].strftime("%Y-%m-%d")
            
        return jsonify({"success": True, "data": all_data}), 200
        
    except Exception as e:
        print("get_all_riwayat error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()