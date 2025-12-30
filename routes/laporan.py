from flask import Blueprint, request, jsonify, make_response
import pymysql
from config import DB_CONFIG
import re
from datetime import datetime
from werkzeug.security import generate_password_hash
from .auth import token_required
import uuid

# Definisikan blueprint TERLEBIH DAHULU
laporan_bp = Blueprint('laporan', __name__, url_prefix='/api/laporan')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# CORS Middleware


# Helper function untuk generate kode laporan
def generate_kode_laporan():
    # Format: LAP-YYMMDD-XXX
    now = datetime.now()
    date_str = now.strftime('%y%m%d')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Cari sequence untuk hari ini
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM laporan 
        WHERE DATE(tanggal_laporan) = CURDATE()
    """)
    result = cursor.fetchone()
    sequence = result['count'] + 1 if result else 1
    
    conn.close()
    
    return f"LAP-{date_str}-{str(sequence).zfill(3)}"

# Helper function untuk validasi data laporan
def validate_laporan_data(data):
    errors = []
    
    # Validasi id_jadwal
    if not data.get('id_jadwal'):
        errors.append("ID jadwal wajib diisi")
    
    # Validasi id_warga
    if not data.get('id_warga'):
        errors.append("ID warga wajib diisi")
    
    # Validasi jenis sampah
    if not data.get('jenis_sampah') or len(data['jenis_sampah'].strip()) == 0:
        errors.append("Jenis sampah wajib diisi")
    
    # Validasi alamat
    if not data.get('alamat_detail') or len(data['alamat_detail'].strip()) < 10:
        errors.append("Alamat detail minimal 10 karakter")
    
    # Validasi nomor HP
    nomor_hp = data.get('nomor_hp', '')
    if nomor_hp and not re.match(r'^[0-9]{10,14}$', nomor_hp):
        errors.append("Nomor HP tidak valid (10-14 digit)")
    
    # Validasi nama pemohon
    if not data.get('nama_pemohon') or len(data['nama_pemohon'].strip()) < 2:
        errors.append("Nama pemohon minimal 2 karakter")
    
    return errors

# 1. CREATE LAPORAN (POST) - TAMBAH @cross_origin() di sini
@laporan_bp.route('', methods=['POST'])
@token_required
def create_laporan(current_user):
    try:
        data = request.json
        print("Data received:", data)  # Debug logging
        
        # Validasi input
        validation_errors = validate_laporan_data(data)
        if validation_errors:
            return jsonify({
                'success': False,
                'message': 'Validasi gagal',
                'errors': validation_errors
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Generate kode laporan
        kode_laporan = generate_kode_laporan()
        
        # Cek apakah data jadwal valid
        if data.get('id_jadwal'):
            cursor.execute("SELECT id FROM jadwal WHERE id = %s", (data['id_jadwal'],))
            jadwal = cursor.fetchone()
            if not jadwal:
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'Jadwal tidak ditemukan'
                }), 404
        
        # Cek apakah warga valid
        if data.get('id_warga'):
            cursor.execute("SELECT id FROM warga WHERE id = %s", (data['id_warga'],))
            warga = cursor.fetchone()
            if not warga:
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'Warga tidak ditemukan'
                }), 404
        
        # Siapkan data untuk insert
        insert_data = {
            'id_jadwal': data.get('id_jadwal'),
            'id_warga': data.get('id_warga'),
            'kode_laporan': kode_laporan,
            'jenis_sampah': data.get('jenis_sampah', ''),
            'jenis_lainnya': data.get('jenis_lainnya', ''),
            'estimasi_volume': data.get('estimasi_volume', 'sedang'),
            'alamat_detail': data.get('alamat_detail', ''),
            'rt': data.get('rt', ''),
            'rw': data.get('rw', ''),
            'nomor_hp': data.get('nomor_hp', ''),
            'nama_pemohon': data.get('nama_pemohon', ''),
            'keterangan': data.get('keterangan', ''),
            'waktu_pengambilan': data.get('waktu_pengambilan', 'pagi'),
            'foto_sampah': data.get('foto_sampah'),
            'status': data.get('status', 'menunggu'),
            'catatan_petugas': data.get('catatan_petugas', '')
        }
        
        # Query untuk insert
        query = """
            INSERT INTO laporan (
                id_jadwal, id_warga, kode_laporan, jenis_sampah, jenis_lainnya,
                estimasi_volume, alamat_detail, rt, rw, nomor_hp, nama_pemohon,
                keterangan, waktu_pengambilan, foto_sampah, status, catatan_petugas
            ) VALUES (
                %(id_jadwal)s, %(id_warga)s, %(kode_laporan)s, %(jenis_sampah)s, %(jenis_lainnya)s,
                %(estimasi_volume)s, %(alamat_detail)s, %(rt)s, %(rw)s, %(nomor_hp)s, %(nama_pemohon)s,
                %(keterangan)s, %(waktu_pengambilan)s, %(foto_sampah)s, %(status)s, %(catatan_petugas)s
            )
        """
        
        cursor.execute(query, insert_data)
        laporan_id = cursor.lastrowid
        
        conn.commit()
        
        # Ambil data yang baru dibuat
        cursor.execute("""
            SELECT l.*, j.tanggal as tanggal_jadwal, j.wilayah, 
                   w.nama_lengkap as nama_warga, w.no_telepon
            FROM laporan l
            LEFT JOIN jadwal j ON l.id_jadwal = j.id
            LEFT JOIN warga w ON l.id_warga = w.id
            WHERE l.id = %s
        """, (laporan_id,))
        
        new_laporan = cursor.fetchone()
        conn.close()
        
        # Format response
        response_data = {
            'id': new_laporan['id'],
            'kode_laporan': new_laporan['kode_laporan'],
            'id_jadwal': new_laporan['id_jadwal'],
            'id_warga': new_laporan['id_warga'],
            'jenis_sampah': new_laporan['jenis_sampah'],
            'jenis_lainnya': new_laporan['jenis_lainnya'],
            'estimasi_volume': new_laporan['estimasi_volume'],
            'alamat_detail': new_laporan['alamat_detail'],
            'rt': new_laporan['rt'],
            'rw': new_laporan['rw'],
            'nomor_hp': new_laporan['nomor_hp'],
            'nama_pemohon': new_laporan['nama_pemohon'],
            'keterangan': new_laporan['keterangan'],
            'waktu_pengambilan': new_laporan['waktu_pengambilan'],
            'status': new_laporan['status'],
            'tanggal_laporan': new_laporan['tanggal_laporan'].isoformat() if new_laporan['tanggal_laporan'] else None,
            'nama_warga': new_laporan['nama_warga'],
            'wilayah': new_laporan['wilayah'],
            'tanggal_jadwal': new_laporan['tanggal_jadwal'].isoformat() if new_laporan['tanggal_jadwal'] else None
        }
        
        return jsonify({
            'success': True,
            'message': 'Laporan berhasil dibuat',
            'data': response_data
        }), 201
        
    except pymysql.err.IntegrityError as e:
        print(f"IntegrityError: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Data duplikat ditemukan'
        }), 400
    except Exception as e:
        print(f"Error in create_laporan: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat membuat laporan'
        }), 500

# 2. GET ALL LAPORAN (GET)
@laporan_bp.route('/', methods=['GET'])
@token_required
def get_all_laporan(current_user):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query dengan join ke tabel terkait
        cursor.execute("""
            SELECT 
                l.*,
                j.tanggal as tanggal_jadwal, j.wilayah, j.jam_mulai, j.jam_selesai, j.nama_petugas,
                w.nama_lengkap as nama_warga, w.no_telepon as telp_warga,
                u.username
            FROM laporan l
            LEFT JOIN jadwal j ON l.id_jadwal = j.id
            LEFT JOIN warga w ON l.id_warga = w.id
            LEFT JOIN users u ON w.user_id = u.id
            ORDER BY l.tanggal_laporan DESC
        """)
        
        laporan_list = cursor.fetchall()
        conn.close()
        
        # Format response
        formatted_data = []
        for laporan in laporan_list:
            formatted_data.append({
                'id': laporan['id'],
                'kode_laporan': laporan['kode_laporan'],
                'id_jadwal': laporan['id_jadwal'],
                'id_warga': laporan['id_warga'],
                'jenis_sampah': laporan['jenis_sampah'],
                'estimasi_volume': laporan['estimasi_volume'],
                'alamat_detail': laporan['alamat_detail'],
                'rt': laporan['rt'],
                'rw': laporan['rw'],
                'nomor_hp': laporan['nomor_hp'],
                'nama_pemohon': laporan['nama_pemohon'],
                'status': laporan['status'],
                'tanggal_laporan': laporan['tanggal_laporan'].isoformat() if laporan['tanggal_laporan'] else None,
                'nama_warga': laporan['nama_warga'],
                'telp_warga': laporan['telp_warga'],
                'username': laporan['username'],
                'wilayah': laporan['wilayah'],
                'tanggal_jadwal': laporan['tanggal_jadwal'].isoformat() if laporan['tanggal_jadwal'] else None,
                'nama_petugas': laporan['nama_petugas']
            })
        
        return jsonify({
            'success': True,
            'count': len(formatted_data),
            'data': formatted_data
        }), 200
        
    except Exception as e:
        print(f"Error in get_all_laporan: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat mengambil data laporan'
        }), 500

# 3. GET LAPORAN BY ID (GET)
@laporan_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_laporan(current_user, id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                l.*,
                j.tanggal as tanggal_jadwal, j.wilayah, j.jam_mulai, j.jam_selesai, j.nama_petugas,
                w.nama_lengkap as nama_warga, w.no_telepon as telp_warga, w.alamat_lengkap as alamat_warga,
                u.username, u.email
            FROM laporan l
            LEFT JOIN jadwal j ON l.id_jadwal = j.id
            LEFT JOIN warga w ON l.id_warga = w.id
            LEFT JOIN users u ON w.user_id = u.id
            WHERE l.id = %s
        """, (id,))
        
        laporan = cursor.fetchone()
        conn.close()
        
        if not laporan:
            return jsonify({
                'success': False,
                'message': 'Laporan tidak ditemukan'
            }), 404
        
        # Format response
        response_data = {
            'id': laporan['id'],
            'kode_laporan': laporan['kode_laporan'],
            'id_jadwal': laporan['id_jadwal'],
            'id_warga': laporan['id_warga'],
            'jenis_sampah': laporan['jenis_sampah'],
            'jenis_lainnya': laporan['jenis_lainnya'],
            'estimasi_volume': laporan['estimasi_volume'],
            'alamat_detail': laporan['alamat_detail'],
            'rt': laporan['rt'],
            'rw': laporan['rw'],
            'nomor_hp': laporan['nomor_hp'],
            'nama_pemohon': laporan['nama_pemohon'],
            'keterangan': laporan['keterangan'],
            'waktu_pengambilan': laporan['waktu_pengambilan'],
            'foto_sampah': laporan['foto_sampah'],
            'status': laporan['status'],
            'tanggal_laporan': laporan['tanggal_laporan'].isoformat() if laporan['tanggal_laporan'] else None,
            'tanggal_verifikasi': laporan['tanggal_verifikasi'].isoformat() if laporan['tanggal_verifikasi'] else None,
            'tanggal_selesai': laporan['tanggal_selesai'].isoformat() if laporan['tanggal_selesai'] else None,
            'catatan_petugas': laporan['catatan_petugas'],
            'nama_warga': laporan['nama_warga'],
            'telp_warga': laporan['telp_warga'],
            'alamat_warga': laporan['alamat_warga'],
            'username': laporan['username'],
            'email': laporan['email'],
            'wilayah': laporan['wilayah'],
            'tanggal_jadwal': laporan['tanggal_jadwal'].isoformat() if laporan['tanggal_jadwal'] else None,
            'jam_mulai': str(laporan['jam_mulai']) if laporan['jam_mulai'] else None,
            'jam_selesai': str(laporan['jam_selesai']) if laporan['jam_selesai'] else None,
            'nama_petugas': laporan['nama_petugas']
        }
        
        return jsonify({
            'success': True,
            'data': response_data
        }), 200
        
    except Exception as e:
        print(f"Error in get_laporan: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat mengambil data laporan'
        }), 500

# 4. UPDATE LAPORAN (PUT)
@laporan_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_laporan(current_user, id):
    try:
        data = request.json
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Cek apakah laporan ada
        cursor.execute("SELECT id FROM laporan WHERE id = %s", (id,))
        laporan = cursor.fetchone()
        
        if not laporan:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Laporan tidak ditemukan'
            }), 404
        
        # Update fields
        update_fields = []
        update_values = []
        
        fields_to_update = [
            'status', 'catatan_petugas', 'jenis_sampah', 'jenis_lainnya',
            'estimasi_volume', 'alamat_detail', 'rt', 'rw', 'nomor_hp',
            'nama_pemohon', 'keterangan', 'waktu_pengambilan', 'foto_sampah'
        ]
        
        for field in fields_to_update:
            if field in data:
                update_fields.append(f"{field} = %s")
                update_values.append(data[field])
        
        # Tanggal verifikasi jika status berubah
        if 'status' in data and data['status'] == 'diproses' and 'tanggal_verifikasi' not in data:
            update_fields.append("tanggal_verifikasi = NOW()")
        
        # Tanggal selesai jika status berubah menjadi selesai
        if 'status' in data and data['status'] == 'selesai':
            update_fields.append("tanggal_selesai = NOW()")
        
        # Update jika ada field yang diubah
        if update_fields:
            update_values.append(id)
            update_query = f"UPDATE laporan SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(update_query, update_values)
            conn.commit()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Laporan berhasil diperbarui'
        }), 200
        
    except Exception as e:
        print(f"Error in update_laporan: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat memperbarui laporan'
        }), 500

# 5. GET LAPORAN BY WARGA (GET)
@laporan_bp.route('/warga/<int:warga_id>', methods=['GET'])
@token_required
def get_laporan_by_warga(current_user, warga_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                l.*,
                j.tanggal as tanggal_jadwal, j.wilayah, j.jam_mulai, j.jam_selesai, j.nama_petugas
            FROM laporan l
            LEFT JOIN jadwal j ON l.id_jadwal = j.id
            WHERE l.id_warga = %s
            ORDER BY l.tanggal_laporan DESC
        """, (warga_id,))
        
        laporan_list = cursor.fetchall()
        conn.close()
        
        # Format response
        formatted_data = []
        for laporan in laporan_list:
            formatted_data.append({
                'id': laporan['id'],
                'kode_laporan': laporan['kode_laporan'],
                'jenis_sampah': laporan['jenis_sampah'],
                'estimasi_volume': laporan['estimasi_volume'],
                'alamat_detail': laporan['alamat_detail'],
                'status': laporan['status'],
                'tanggal_laporan': laporan['tanggal_laporan'].isoformat() if laporan['tanggal_laporan'] else None,
                'wilayah': laporan['wilayah'],
                'tanggal_jadwal': laporan['tanggal_jadwal'].isoformat() if laporan['tanggal_jadwal'] else None,
                'nama_petugas': laporan['nama_petugas']
            })
        
        return jsonify({
            'success': True,
            'count': len(formatted_data),
            'data': formatted_data
        }), 200
        
    except Exception as e:
        print(f"Error in get_laporan_by_warga: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat mengambil data laporan'
        }), 500

# 6. STATISTICS LAPORAN (GET)
@laporan_bp.route('/stats', methods=['GET'])
@token_required
def get_laporan_stats(current_user):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Total laporan
        cursor.execute("SELECT COUNT(*) as total FROM laporan")
        total = cursor.fetchone()['total']
        
        # Per status
        cursor.execute("""
            SELECT status, COUNT(*) as jumlah
            FROM laporan
            GROUP BY status
        """)
        per_status = cursor.fetchall()
        
        # Per hari (7 hari terakhir)
        cursor.execute("""
            SELECT DATE(tanggal_laporan) as tanggal, COUNT(*) as jumlah
            FROM laporan
            WHERE tanggal_laporan >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(tanggal_laporan)
            ORDER BY tanggal DESC
        """)
        per_hari = cursor.fetchall()
        
        # Per wilayah
        cursor.execute("""
            SELECT j.wilayah, COUNT(l.id) as jumlah
            FROM laporan l
            LEFT JOIN jadwal j ON l.id_jadwal = j.id
            WHERE j.wilayah IS NOT NULL
            GROUP BY j.wilayah
            ORDER BY jumlah DESC
            LIMIT 10
        """)
        per_wilayah = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'per_status': per_status,
                'per_hari': [
                    {
                        'tanggal': row['tanggal'].isoformat() if row['tanggal'] else None,
                        'jumlah': row['jumlah']
                    }
                    for row in per_hari
                ],
                'per_wilayah': per_wilayah
            }
        }), 200
        
    except Exception as e:
        print(f"Error in get_laporan_stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat mengambil statistik laporan'
        }), 500