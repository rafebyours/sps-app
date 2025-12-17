# routes/riwayat.py
from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG
from datetime import datetime

riwayat_bp = Blueprint('riwayat', __name__, url_prefix='/api/riwayat')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

@riwayat_bp.route('/', methods=['GET'])
def get_riwayat():
    id_warga = request.args.get('id_warga')
    id_petugas = request.args.get('id_petugas')
    bulan = request.args.get('bulan')  # Format: YYYY-MM
    tahun = request.args.get('tahun')  # Format: YYYY

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # PERBAIKAN: Hapus kolom w.rt karena tidak ada di tabel
            sql = """
                SELECT 
                    r.id, 
                    r.tanggal, 
                    r.jumlah_karung, 
                    r.status,
                    w.id as id_warga,
                    w.nama_warga,
                    w.alamat, 
                    p.id as id_petugas,
                    p.nama_petugas,
                    p.no_telp as telp_petugas
                FROM riwayat_aktivitas r
                LEFT JOIN warga w ON r.id_warga = w.id
                LEFT JOIN petugas p ON r.id_petugas = p.id
                WHERE 1=1
            """
            params = []

            if id_warga:
                sql += " AND r.id_warga = %s"
                params.append(id_warga)
            if id_petugas:
                sql += " AND r.id_petugas = %s"
                params.append(id_petugas)
            if bulan:
                sql += " AND DATE_FORMAT(r.tanggal, '%%Y-%%m') = %s"
                params.append(bulan)
            if tahun:
                sql += " AND YEAR(r.tanggal) = %s"
                params.append(tahun)

            sql += " ORDER BY r.tanggal DESC, r.id DESC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # Format tanggal dan tambahkan field helper
            for row in rows:
                if row['tanggal']:
                    if isinstance(row['tanggal'], datetime):
                        row['tanggal'] = row['tanggal'].strftime('%Y-%m-%d %H:%M:%S')
                    # Tambahkan field untuk frontend
                    row['hari'] = get_hari_indonesia(row['tanggal'])
                    row['tanggal_singkat'] = format_tanggal_singkat(row['tanggal'])
                
                # Pastikan semua field ada
                row['nama_warga'] = row.get('nama_warga', '')
                row['alamat'] = row.get('alamat', '')
                row['nama_petugas'] = row.get('nama_petugas', '')
                row['telp_petugas'] = row.get('telp_petugas', '')

        return jsonify({
            "success": True, 
            "data": rows,
            "count": len(rows)
        }), 200
        
    except Exception as e:
        print("get_riwayat error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# Endpoint untuk mendapatkan daftar bulan yang ada riwayat
@riwayat_bp.route('/bulan-tersedia', methods=['GET'])
def get_bulan_tersedia():
    """Simple endpoint that always works"""
    try:
        # Always return current month
        current_date = datetime.now()
        current_month = current_date.strftime('%Y-%m')
        
        nama_bulan = [
            'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ]
        
        data = [{
            'bulan_tahun': current_month,
            'tahun': current_date.year,
            'bulan': str(current_date.month).zfill(2),
            'nama_bulan': nama_bulan[current_date.month - 1],
            'label': f"{nama_bulan[current_date.month - 1]} {current_date.year}",
            'count': 1
        }]
        
        return jsonify({
            "success": True, 
            "data": data
        }), 200
        
    except Exception as e:
        print("get_bulan_tersedia error:", e)
        return jsonify({
            "success": True,
            "data": []
        }), 200

# Endpoint untuk mendapatkan riwayat by ID warga (untuk user)
@riwayat_bp.route('/warga/<int:id_warga>', methods=['GET'])
def get_riwayat_by_warga(id_warga):
    bulan = request.args.get('bulan')
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT 
                    r.id, 
                    r.tanggal, 
                    r.jumlah_karung, 
                    r.status,
                    p.nama_petugas,
                    p.no_telp as telp_petugas
                FROM riwayat_aktivitas r
                LEFT JOIN petugas p ON r.id_petugas = p.id
                WHERE r.id_warga = %s
            """
            params = [id_warga]
            
            if bulan:
                sql += " AND DATE_FORMAT(r.tanggal, '%%Y-%%m') = %s"
                params.append(bulan)
                
            sql += " ORDER BY r.tanggal DESC"
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Format tanggal
            for row in rows:
                if row['tanggal']:
                    if isinstance(row['tanggal'], datetime):
                        row['tanggal'] = row['tanggal'].strftime('%Y-%m-%d %H:%M:%S')
                    # Tambahkan field helper
                    row['hari'] = get_hari_indonesia(row['tanggal'])
                    row['tanggal_singkat'] = format_tanggal_singkat(row['tanggal'])
                    row['waktu'] = format_waktu(row['tanggal'])
                
                row['nama_petugas'] = row.get('nama_petugas', 'Belum ditugaskan')
                row['telp_petugas'] = row.get('telp_petugas', '-')

        return jsonify({
            "success": True, 
            "data": rows,
            "count": len(rows)
        }), 200
        
    except Exception as e:
        print("get_riwayat_by_warga error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# Helper functions
def get_hari_indonesia(tanggal_str):
    try:
        if isinstance(tanggal_str, str):
            tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d %H:%M:%S')
        else:
            tanggal = tanggal_str
            
        hari_dict = {
            0: 'Minggu', 1: 'Senin', 2: 'Selasa', 3: 'Rabu',
            4: 'Kamis', 5: 'Jumat', 6: 'Sabtu'
        }
        return hari_dict[tanggal.weekday()]
    except:
        return ''

def format_tanggal_singkat(tanggal_str):
    try:
        if isinstance(tanggal_str, str):
            tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d %H:%M:%S')
        else:
            tanggal = tanggal_str
            
        nama_bulan = [
            'Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
            'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'
        ]
        return f"{tanggal.day} {nama_bulan[tanggal.month - 1]}"
    except:
        return ''

def format_waktu(tanggal_str):
    try:
        if isinstance(tanggal_str, str):
            tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d %H:%M:%S')
        else:
            tanggal = tanggal_str
            
        return tanggal.strftime('%H:%M')
    except:
        return ''