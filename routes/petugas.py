from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG
import re
from werkzeug.security import generate_password_hash
from .auth import token_required

petugas_bp = Blueprint('petugas', __name__, url_prefix='/api/petugas')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# Helper function untuk validasi
# Di fungsi validate_petugas_data(), tambah pengecualian untuk update
def validate_petugas_data(data, is_update=False):
    errors = []
    
    # ... existing validations ...
    
    # Validasi password HANYA untuk create atau jika ada password baru
    if not is_update and (not data.get('password') or len(data['password']) < 6):
        errors.append("Password minimal 6 karakter")
    
    # Untuk update, validasi password hanya jika ada dan bukan placeholder
    if is_update and 'password' in data:
        password = data['password']
        # Jika password ada dan bukan placeholder/empty, harus minimal 6 karakter
        if password and password.strip() and password != '********' and len(password) < 6:
            errors.append("Password baru minimal 6 karakter")
    
    return errors
# 1. GET ALL PETUGAS
@petugas_bp.route('/', methods=['GET'])
@token_required
def get_all_petugas(current_user):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query untuk mengambil semua petugas beserta data user
        cursor.execute("""
            SELECT 
                p.id,
                p.nama_lengkap,
                p.nik,
                p.no_telepon,
                p.alamat,
                p.status_kerja,
                p.gaji_per_karung,
                p.latitude,
                p.longitude,
                p.total_karung,
                u.username,
                u.email,
                u.role,
                u.status as user_status,
                u.created_at
            FROM petugas p
            JOIN users u ON p.user_id = u.id
            WHERE u.status = 'active'
            ORDER BY p.nama_lengkap ASC
        """)
        
        petugas_list = cursor.fetchall()
        conn.close()
        
        # Format response
        formatted_data = []
        for petugas in petugas_list:
            formatted_data.append({
                'id': petugas['id'],
                'nama_petugas': petugas['nama_lengkap'],
                'nik': petugas['nik'],
                'no_telp': petugas['no_telepon'],
                'alamat': petugas['alamat'],
                'status': petugas['status_kerja'].capitalize() if petugas['status_kerja'] else 'Tidak Aktif',
                'gaji_per_karung': float(petugas['gaji_per_karung']) if petugas['gaji_per_karung'] else 0,
                'username': petugas['username'],
                'email': petugas['email'],
                'user_status': petugas['user_status'],
                'created_at': petugas['created_at'].isoformat() if petugas['created_at'] else None,
                'total_karung': petugas['total_karung'] or 0
            })
        
        return jsonify({
            'success': True,
            'count': len(formatted_data),
            'data': formatted_data
        }), 200
        
    except Exception as e:
        print(f"Error get_all_petugas: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat mengambil data petugas'
        }), 500

# 2. GET SINGLE PETUGAS
@petugas_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_petugas(current_user, id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                p.*,
                u.username,
                u.email,
                u.role,
                u.status as user_status,
                u.created_at
            FROM petugas p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = %s
        """, (id,))
        
        petugas = cursor.fetchone()
        conn.close()
        
        if not petugas:
            return jsonify({
                'success': False,
                'message': 'Petugas tidak ditemukan'
            }), 404
        
        # Format response
        response_data = {
            'id': petugas['id'],
            'nama_lengkap': petugas['nama_lengkap'],
            'nik': petugas['nik'],
            'no_telepon': petugas['no_telepon'],
            'alamat': petugas['alamat'],
            'status_kerja': petugas['status_kerja'],
            'gaji_per_karung': float(petugas['gaji_per_karung']) if petugas['gaji_per_karung'] else 0,
            'latitude': float(petugas['latitude']) if petugas['latitude'] else None,
            'longitude': float(petugas['longitude']) if petugas['longitude'] else None,
            'total_karung': petugas['total_karung'] or 0,
            'username': petugas['username'],
            'email': petugas['email'],
            'user_id': petugas['user_id'],
            'user_status': petugas['user_status'],
            'created_at': petugas['created_at'].isoformat() if petugas['created_at'] else None
        }
        
        return jsonify({
            'success': True,
            'data': response_data
        }), 200
        
    except Exception as e:
        print(f"Error get_petugas: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat mengambil data petugas'
        }), 500

# 3. CREATE NEW PETUGAS
@petugas_bp.route('/', methods=['POST'])
@token_required
def create_petugas(current_user):
    try:
        data = request.json
        print(f"🔍 DATA DITERIMA DARI FRONTEND: {data}")  # <-- TAMBAHKAN INI
        
        # Validasi input
        validation_errors = validate_petugas_data(data)
        print(f"🔍 HASIL VALIDASI: {validation_errors}")  # <-- TAMBAHKAN INI
        if validation_errors:
            return jsonify({
                'success': False,
                'message': 'Validasi gagal',
                'errors': validation_errors
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Cek apakah username/email sudah terdaftar
        cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", 
                      (data['username'], data['email']))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Username atau email sudah terdaftar'
            }), 400
        
        # Cek apakah NIK sudah terdaftar (jika ada)
        if data.get('nik'):
            cursor.execute("SELECT id FROM petugas WHERE nik = %s", (data['nik'],))
            existing_nik = cursor.fetchone()
            if existing_nik:
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'NIK sudah terdaftar'
                }), 400
        
        # Hash password
        hashed_password = generate_password_hash(data['password'])
        
        # Mulai transaction
        conn.begin()
        
        try:
            # 1. Buat user dulu
            cursor.execute("""
                INSERT INTO users (username, email, password, role, status)
                VALUES (%s, %s, %s, 'petugas', 'active')
            """, (data['username'], data['email'], hashed_password))
            
            user_id = cursor.lastrowid
            
            # 2. Buat data petugas
            cursor.execute("""
                INSERT INTO petugas (
                    user_id, nama_lengkap, nik, no_telepon, alamat,
                    status_kerja, gaji_per_karung, latitude, longitude
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                data['nama_lengkap'],
                data.get('nik'),
                data.get('no_telepon'),
                data.get('alamat'),
                data.get('status_kerja', 'aktif'),
                float(data.get('gaji_per_karung', 5000)),
                float(data.get('latitude', 0)) if data.get('latitude') else None,
                float(data.get('longitude', 0)) if data.get('longitude') else None
            ))
            
            petugas_id = cursor.lastrowid
            
            # Commit transaction
            conn.commit()
            
            # Ambil data yang baru dibuat
            cursor.execute("""
                SELECT 
                    p.*,
                    u.username,
                    u.email,
                    u.role,
                    u.status as user_status
                FROM petugas p
                JOIN users u ON p.user_id = u.id
                WHERE p.id = %s
            """, (petugas_id,))
            
            new_petugas = cursor.fetchone()
            
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Petugas berhasil ditambahkan',
                'data': {
                    'id': new_petugas['id'],
                    'nama_petugas': new_petugas['nama_lengkap'],
                    'nik': new_petugas['nik'],
                    'no_telp': new_petugas['no_telepon'],
                    'alamat': new_petugas['alamat'],
                    'status': new_petugas['status_kerja'].capitalize(),
                    'gaji_per_karung': float(new_petugas['gaji_per_karung']),
                    'username': new_petugas['username'],
                    'email': new_petugas['email']
                }
            }), 201
            
        except Exception as e:
            conn.rollback()
            raise e
            
    except pymysql.err.IntegrityError as e:
        return jsonify({
            'success': False,
            'message': 'Data duplikat ditemukan'
        }), 400
    except Exception as e:
        print(f"Error create_petugas: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat menambahkan petugas'
        }), 500

# 4. UPDATE PETUGAS
@petugas_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_petugas(current_user, id):
    try:
        data = request.json
        
         # DEBUG: Print data yang diterima
        print(f"📥 UPDATE DATA: {data}")
        print(f"📥 Password field exists: {'password' in data}")
        if 'password' in data:
            print(f"📥 Password value: '{data['password']}'")
        
        # Hapus password dari data jika kosong (untuk menghindari validasi)
        if 'password' in data and (not data['password'] or data['password'].strip() == ''):
            print("🗑️ Removing empty password field")
            data.pop('password', None)
            
        conn = get_connection()
        cursor = conn.cursor()
        
        # Cek apakah petugas ada
        cursor.execute("""
            SELECT p.*, u.id as user_id 
            FROM petugas p 
            JOIN users u ON p.user_id = u.id 
            WHERE p.id = %s
        """, (id,))
        
        petugas = cursor.fetchone()
        
        if not petugas:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Petugas tidak ditemukan'
            }), 404
        
        # Validasi untuk update
        validation_errors = validate_petugas_data(data, is_update=True)
        if validation_errors:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Validasi gagal',
                'errors': validation_errors
            }), 400
        
        # Mulai transaction
        conn.begin()
        
        try:
            # Update data petugas
            update_fields = []
            update_values = []
            
            if 'nama_lengkap' in data:
                update_fields.append("nama_lengkap = %s")
                update_values.append(data['nama_lengkap'])
            
            if 'nik' in data:
                # Cek NIK duplikat (kecuali untuk petugas ini)
                cursor.execute("SELECT id FROM petugas WHERE nik = %s AND id != %s", 
                             (data['nik'], id))
                if cursor.fetchone():
                    raise Exception("NIK sudah digunakan oleh petugas lain")
                update_fields.append("nik = %s")
                update_values.append(data['nik'])
            
            if 'no_telepon' in data:
                update_fields.append("no_telepon = %s")
                update_values.append(data['no_telepon'])
            
            if 'alamat' in data:
                update_fields.append("alamat = %s")
                update_values.append(data['alamat'])
            
            if 'status_kerja' in data:
                update_fields.append("status_kerja = %s")
                update_values.append(data['status_kerja'])
            
            if 'gaji_per_karung' in data:
                update_fields.append("gaji_per_karung = %s")
                update_values.append(float(data['gaji_per_karung']))
            
            if 'latitude' in data:
                update_fields.append("latitude = %s")
                update_values.append(float(data['latitude']) if data['latitude'] else None)
            
            if 'longitude' in data:
                update_fields.append("longitude = %s")
                update_values.append(float(data['longitude']) if data['longitude'] else None)
            
            # Update petugas jika ada field yang diubah
            if update_fields:
                update_values.append(id)
                update_query = f"UPDATE petugas SET {', '.join(update_fields)} WHERE id = %s"
                cursor.execute(update_query, update_values)
            
            # Update user jika ada data yang perlu diubah
            user_update_fields = []
            user_update_values = []
            
            if 'username' in data:
                # Cek username duplikat
                cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", 
                             (data['username'], petugas['user_id']))
                if cursor.fetchone():
                    raise Exception("Username sudah digunakan")
                user_update_fields.append("username = %s")
                user_update_values.append(data['username'])
            
            if 'email' in data:
                # Cek email duplikat
                cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", 
                             (data['email'], petugas['user_id']))
                if cursor.fetchone():
                    raise Exception("Email sudah digunakan")
                user_update_fields.append("email = %s")
                user_update_values.append(data['email'])
            
            if 'password' in data and data['password']:
                hashed_password = generate_password_hash(data['password'])
                user_update_fields.append("password = %s")
                user_update_values.append(hashed_password)
            
            # Update user jika ada field yang diubah
            if user_update_fields:
                user_update_values.append(petugas['user_id'])
                user_update_query = f"UPDATE users SET {', '.join(user_update_fields)} WHERE id = %s"
                cursor.execute(user_update_query, user_update_values)
            
            # Commit transaction
            conn.commit()
            
            # Ambil data yang sudah diupdate
            cursor.execute("""
                SELECT 
                    p.*,
                    u.username,
                    u.email,
                    u.role,
                    u.status as user_status
                FROM petugas p
                JOIN users u ON p.user_id = u.id
                WHERE p.id = %s
            """, (id,))
            
            updated_petugas = cursor.fetchone()
            
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Petugas berhasil diperbarui',
                'data': {
                    'id': updated_petugas['id'],
                    'nama_petugas': updated_petugas['nama_lengkap'],
                    'nik': updated_petugas['nik'],
                    'no_telp': updated_petugas['no_telepon'],
                    'alamat': updated_petugas['alamat'],
                    'status': updated_petugas['status_kerja'].capitalize(),
                    'gaji_per_karung': float(updated_petugas['gaji_per_karung']),
                    'username': updated_petugas['username'],
                    'email': updated_petugas['email']
                }
            }), 200
            
        except Exception as e:
            conn.rollback()
            raise e
            
    except Exception as e:
        print(f"Error update_petugas: {str(e)}")
        error_msg = str(e)
        if "duplicate" in error_msg.lower() or "sudah digunakan" in error_msg:
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat memperbarui petugas'
        }), 500

# 5. DELETE PETUGAS (SOFT DELETE)
# Di routes/petugas.py - fungsi delete_petugas(), tambah logging:
@petugas_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_petugas(current_user, id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Ambil data petugas + user_id dulu
        cursor.execute("""
            SELECT p.user_id, p.nama_lengkap
            FROM petugas p
            WHERE p.id = %s
        """, (id,))
        petugas = cursor.fetchone()

        if not petugas:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Petugas tidak ditemukan'
            }), 404

        conn.begin()

        # 1. Soft delete petugas
        cursor.execute("""
            UPDATE petugas
            SET status_kerja = 'nonaktif'
            WHERE id = %s
        """, (id,))

        # 2. Nonaktifkan user
        cursor.execute("""
            UPDATE users
            SET status = 'inactive'
            WHERE id = %s
        """, (petugas['user_id'],))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f"Petugas {petugas['nama_lengkap']} berhasil dinonaktifkan"
        }), 200

    except Exception as e:
        print(f"Error delete_petugas: {e}")
        return jsonify({
            'success': False,
            'message': 'Gagal menghapus petugas'
        }), 500



# 6. GET PETUGAS STATISTICS
@petugas_bp.route('/stats', methods=['GET'])
@token_required
def get_petugas_stats(current_user):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Hitung total petugas
        cursor.execute("SELECT COUNT(*) as total FROM petugas")
        total = cursor.fetchone()['total']
        
        # Hitung petugas aktif
        cursor.execute("""
            SELECT COUNT(*) as aktif 
            FROM petugas p 
            JOIN users u ON p.user_id = u.id 
            WHERE p.status_kerja = 'aktif' AND u.status = 'active'
        """)
        aktif = cursor.fetchone()['aktif']
        
        # Hitung petugas tidak aktif
        tidak_aktif = total - aktif
        
        # Rata-rata gaji per karung
        cursor.execute("SELECT AVG(gaji_per_karung) as avg_gaji FROM petugas")
        avg_gaji = cursor.fetchone()['avg_gaji'] or 0
        
        # Total karung yang sudah dikumpulkan
        cursor.execute("SELECT SUM(total_karung) as total_karung FROM petugas")
        total_karung = cursor.fetchone()['total_karung'] or 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'aktif': aktif,
                'tidak_aktif': tidak_aktif,
                'rata_gaji': float(avg_gaji),
                'total_karung': total_karung
            }
        }), 200
        
    except Exception as e:
        print(f"Error get_petugas_stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat mengambil statistik'
        }), 500

# 7. SEARCH PETUGAS
@petugas_bp.route('/search', methods=['GET'])
@token_required
def search_petugas(current_user):
    try:
        search_term = request.args.get('q', '').strip()
        
        if not search_term:
            return jsonify({
                'success': False,
                'message': 'Kata kunci pencarian diperlukan'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        
        cursor.execute("""
            SELECT 
                p.id,
                p.nama_lengkap,
                p.no_telepon,
                p.status_kerja,
                p.total_karung,
                u.username,
                u.email
            FROM petugas p
            JOIN users u ON p.user_id = u.id
            WHERE u.status = 'active'
            AND (
                p.nama_lengkap LIKE %s OR
                p.no_telepon LIKE %s OR
                u.username LIKE %s OR
                u.email LIKE %s
            )
                        ORDER BY p.nama_lengkap ASC
            LIMIT 20
        """, (search_pattern, search_pattern, search_pattern, search_pattern))
        
        results = cursor.fetchall()
        conn.close()
        
        formatted_results = []
        for petugas in results:
            formatted_results.append({
                'id': petugas['id'],
                'nama_petugas': petugas['nama_lengkap'],
                'no_telp': petugas['no_telepon'],
                'status': petugas['status_kerja'].capitalize(),
                'total_karung': petugas['total_karung'],
                'username': petugas['username'],
                'email': petugas['email']
            })
        
        return jsonify({
            'success': True,
            'count': len(formatted_results),
            'data': formatted_results
        }), 200
        
    except Exception as e:
        print(f"Error search_petugas: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat mencari petugas'
        }), 500
        
# 8. GET TRANSACTIONS FOR PETUGAS
@petugas_bp.route('/transaksi', methods=['GET'])
@token_required
def get_petugas_transaksi(current_user):
    """
    Mendapatkan data transaksi dengan filter untuk petugas
    Query params:
    - tanggal: YYYY-MM-DD (default: hari ini)
    - jenis: pemasukan/pengeluaran/gaji/topup/semua (default: semua)
    - filter_user: semua/saya/warga/petugas_lain (default: semua)
    """
    try:
        # Get query parameters
        tanggal = request.args.get('tanggal')
        jenis = request.args.get('jenis', 'semua')
        filter_user = request.args.get('filter_user', 'semua')
        
        # Jika user bukan petugas, return error
        if current_user['role'] != 'petugas':
            return jsonify({
                'success': False,
                'message': 'Akses ditolak. Hanya untuk petugas'
            }), 403
        
        # Set default tanggal ke hari ini jika tidak ada
        if not tanggal:
            from datetime import datetime
            tanggal = datetime.now().strftime('%Y-%m-%d')
        
        # Connect to database
        conn = get_connection()
        cursor = conn.cursor()
        
        # Base query untuk transaksi
        query = """
            SELECT 
                t.*,
                w.nama_lengkap as nama_warga,
                w.alamat_lengkap alamat_warga,
                w.rt as rt_warga,
                w.rw as rw_warga,
                p.nama_lengkap as nama_petugas,
                l.jenis_sampah,
                l.estimasi_volume,
                l.foto_sampah
            FROM transaksi t
            LEFT JOIN warga w ON t.warga_id = w.id
            LEFT JOIN petugas p ON t.petugas_id = p.id
            LEFT JOIN laporan l ON t.laporan_id = l.id
            WHERE DATE(t.tanggal) = %s
        """
        params = [tanggal]
        
        # Filter by jenis transaksi
        if jenis != 'semua':
            query += " AND t.jenis = %s"
            params.append(jenis)
        
        # Filter by user type berdasarkan petugas yang login
        if filter_user == 'saya':
            # Ambil data petugas yang login
            cursor.execute("SELECT id FROM petugas WHERE user_id = %s", (current_user['id'],))
            petugas_data = cursor.fetchone()
            
            if petugas_data:
                query += " AND t.petugas_id = %s"
                params.append(petugas_data['id'])
            else:
                query += " AND t.petugas_id IS NULL"
                
        elif filter_user == 'warga':
            query += " AND t.warga_id IS NOT NULL AND t.petugas_id IS NULL"
        elif filter_user == 'petugas_lain':
            # Ambil data petugas yang login
            cursor.execute("SELECT id FROM petugas WHERE user_id = %s", (current_user['id'],))
            petugas_data = cursor.fetchone()
            
            if petugas_data:
                query += " AND t.petugas_id IS NOT NULL AND t.petugas_id != %s"
                params.append(petugas_data['id'])
            else:
                query += " AND t.petugas_id IS NOT NULL"
        
        # Order by tanggal terbaru
        query += " ORDER BY t.tanggal DESC"
        
        # Execute query
        cursor.execute(query, params)
        transaksi = cursor.fetchall()
        
        # Calculate summary statistics
        summary_query = """
            SELECT 
                COALESCE(SUM(CASE WHEN jenis = 'pemasukan' THEN jumlah ELSE 0 END), 0) as total_pemasukan,
                COALESCE(SUM(CASE WHEN jenis = 'pengeluaran' THEN jumlah ELSE 0 END), 0) as total_pengeluaran,
                COALESCE(SUM(CASE WHEN jenis = 'gaji' THEN jumlah ELSE 0 END), 0) as total_gaji,
                COALESCE(SUM(CASE WHEN jenis = 'topup' THEN jumlah ELSE 0 END), 0) as total_topup,
                COALESCE(COUNT(*), 0) as total_transaksi,
                COALESCE(SUM(CASE WHEN status_bayar = 'lunas' THEN 1 ELSE 0 END), 0) as transaksi_lunas,
                COALESCE(SUM(CASE WHEN status_bayar = 'pending' THEN 1 ELSE 0 END), 0) as transaksi_pending
            FROM transaksi 
            WHERE DATE(tanggal) = %s
        """
        
        summary_params = [tanggal]
        
        # Add filters to summary if needed
        if jenis != 'semua':
            summary_query += " AND jenis = %s"
            summary_params.append(jenis)
        
        cursor.execute(summary_query, summary_params)
        summary_result = cursor.fetchone()
        
        # Calculate statistics for current petugas
        if filter_user == 'saya' or filter_user == 'semua':
            # Ambil data petugas yang login
            cursor.execute("SELECT id FROM petugas WHERE user_id = %s", (current_user['id'],))
            petugas_data = cursor.fetchone()
            
            if petugas_data:
                petugas_stats_query = """
                    SELECT 
                        COALESCE(COUNT(*), 0) as transaksi_saya,
                        COALESCE(SUM(CASE WHEN jenis = 'pemasukan' THEN jumlah ELSE 0 END), 0) as pemasukan_saya
                    FROM transaksi 
                    WHERE DATE(tanggal) = %s AND petugas_id = %s
                """
                cursor.execute(petugas_stats_query, (tanggal, petugas_data['id']))
                petugas_stats = cursor.fetchone()
                
                transaksi_saya = petugas_stats['transaksi_saya']
                pemasukan_saya = float(petugas_stats['pemasukan_saya'] or 0)
            else:
                transaksi_saya = 0
                pemasukan_saya = 0
        else:
            transaksi_saya = 0
            pemasukan_saya = 0
        
        # Format summary
        summary = {
            'pemasukan': float(summary_result['total_pemasukan'] or 0),
            'pengeluaran': float(summary_result['total_pengeluaran'] or 0),
            'gaji': float(summary_result['total_gaji'] or 0),
            'topup': float(summary_result['total_topup'] or 0),
            'saldo': float((summary_result['total_pemasukan'] or 0) - (summary_result['total_pengeluaran'] or 0)),
            'total_transaksi': summary_result['total_transaksi'] or 0,
            'transaksi_lunas': summary_result['transaksi_lunas'] or 0,
            'transaksi_pending': summary_result['transaksi_pending'] or 0,
            'transaksi_saya': transaksi_saya,
            'pemasukan_saya': pemasukan_saya
        }
        
        conn.close()
        
        # Format response data
        formatted_transaksi = []
        for t in transaksi:
            formatted_transaksi.append({
                'id': t['id'],
                'kode_transaksi': t['kode_transaksi'],
                'jenis': t['jenis'],
                'kategori': t['kategori'],
                'jumlah': float(t['jumlah']),
                'harga_per_karung': float(t['harga_per_karung']) if t['harga_per_karung'] else None,
                'total_karung': t['total_karung'],
                'metode_bayar': t['metode_bayar'],
                'status_bayar': t['status_bayar'],
                'keterangan': t['keterangan'],
                'tanggal': t['tanggal'].isoformat() if t['tanggal'] else None,
                'warga_id': t['warga_id'],
                'petugas_id': t['petugas_id'],
                'laporan_id': t['laporan_id'],
                'nama_warga': t['nama_warga'],
                'nama_petugas': t['nama_petugas'],
                'jenis_sampah': t['jenis_sampah'],
                'total_karung': t['total_karung']
            })
        
        return jsonify({
            'success': True,
            'data': formatted_transaksi,
            'summary': summary,
            'tanggal': tanggal,
            'filters': {
                'jenis': jenis,
                'filter_user': filter_user
            }
        }), 200
        
    except Exception as e:
        print(f"Error get_petugas_transaksi: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Gagal mengambil data transaksi',
            'error': str(e)
        }), 500

# 9. GET TRANSACTION SUMMARY FOR PETUGAS (Untuk Dashboard)
@petugas_bp.route('/summary', methods=['GET'])
@token_required
def get_petugas_summary(current_user):
    """
    Mendapatkan summary rekap harian petugas (untuk halaman rekap)
    """
    try:
        tanggal = request.args.get('tanggal')
        
        # Jika user bukan petugas, return error
        if current_user['role'] != 'petugas':
            return jsonify({
                'success': False,
                'message': 'Akses ditolak. Hanya untuk petugas'
            }), 403
        
        # Set default tanggal ke hari ini jika tidak ada
        if not tanggal:
            from datetime import datetime
            tanggal = datetime.now().strftime('%Y-%m-%d')
        
        # Connect to database
        conn = get_connection()
        cursor = conn.cursor()
        
        # Ambil data petugas yang login
        cursor.execute("SELECT id FROM petugas WHERE user_id = %s", (current_user['id'],))
        petugas_data = cursor.fetchone()
        
        if not petugas_data:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Data petugas tidak ditemukan'
            }), 404
        
        petugas_id = petugas_data['id']
        
        # Query untuk summary khusus petugas
        query = """
            SELECT 
                -- Total pengambilan sampah (laporan yang dibuat oleh petugas ini)
                COALESCE(COUNT(DISTINCT l.id), 0) as total_pengambilan,
                
                -- Total pemasukan dari petugas ini
                COALESCE(SUM(CASE WHEN t.petugas_id = %s AND t.jenis = 'pemasukan' THEN t.jumlah ELSE 0 END), 0) as pemasukan_hari_ini,
                
                -- Total tunggak (transaksi pending dari warga untuk petugas ini)
                COALESCE(SUM(CASE WHEN t.petugas_id = %s AND t.status_bayar = 'pending' THEN 1 ELSE 0 END), 0) as total_tunggak_kasus,
                
                -- Total transaksi yang dibuat oleh petugas ini
                COALESCE(COUNT(CASE WHEN t.petugas_id = %s THEN 1 END), 0) as total_transaksi_saya
                
            FROM transaksi t
            LEFT JOIN laporan l ON t.laporan_id = l.id AND l.petugas_id = %s
            WHERE DATE(t.tanggal) = %s
        """
        
        cursor.execute(query, (petugas_id, petugas_id, petugas_id, petugas_id, tanggal))
        summary = cursor.fetchone()
        
        # Query untuk detail transaksi petugas (untuk tabel)
        detail_query = """
            SELECT 
                t.id as id_transaksi,
                COALESCE(w.nama_lengkap, 'Tidak ada data') as nama,
                COALESCE(w.alamat_lengkap, '-') as alamat,
                COALESCE(l.estimasi_volume, 0) as total_karung,
                t.jumlah as pembayaran,
                t.status_bayar,
                CASE 
                    WHEN t.status_bayar = 'pending' THEN 'Nunggak'
                    WHEN t.status_bayar = 'lunas' THEN 'Lunas'
                    ELSE 'Gagal'
                END as status_pembayaran,
                t.keterangan,
                t.kode_transaksi
            FROM transaksi t
            LEFT JOIN warga w ON t.warga_id = w.id
            LEFT JOIN laporan l ON t.laporan_id = l.id
            WHERE DATE(t.tanggal) = %s AND t.petugas_id = %s
            ORDER BY t.tanggal DESC
        """
        
        cursor.execute(detail_query, (tanggal, petugas_id))
        detail = cursor.fetchall()
        
        conn.close()
        
        # Format detail
        formatted_detail = []
        for d in detail:
            formatted_detail.append({
                'id': d['id_transaksi'],
                'name': d['nama'],
                'bags': d['total_karung'],
                'payment': f"Rp {int(d['pembayaran']):,}".replace(',', '.'),
                'status_bayar': d['status_bayar'],
                'status_pembayaran': d['status_pembayaran'],
                'keterangan': d['keterangan'],
                'kode_transaksi': d['kode_transaksi']
            })
        
        return jsonify({
            'success': True,
            'data': {
                'pengambilan_sampah': summary['total_pengambilan'],
                'pemasukan_hari_ini': float(summary['pemasukan_hari_ini']),
                'total_tunggak_kasus': summary['total_tunggak_kasus'],
                'total_transaksi_saya': summary['total_transaksi_saya'],
                'detail': formatted_detail
            }
        }), 200
        
    except Exception as e:
        print(f"Error get_petugas_summary: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Gagal mengambil summary',
            'error': str(e)
        }), 500

# 10. CREATE TRANSACTION (Untuk Petugas)
@petugas_bp.route('/transaksi/create', methods=['POST'])
@token_required
def create_transaksi(current_user):
    """
    Membuat transaksi baru (untuk petugas)
    """
    try:
        data = request.json
        
        # Jika user bukan petugas, return error
        if current_user['role'] != 'petugas':
            return jsonify({
                'success': False,
                'message': 'Akses ditolak. Hanya untuk petugas'
            }), 403
        
        # Validasi data wajib
        required_fields = ['jenis', 'jumlah']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Field {field} harus diisi'
                }), 400
        
        # Connect to database
        conn = get_connection()
        cursor = conn.cursor()
        
        # Ambil data petugas yang login
        cursor.execute("SELECT id FROM petugas WHERE user_id = %s", (current_user['id'],))
        petugas_data = cursor.fetchone()
        
        if not petugas_data:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Data petugas tidak ditemukan'
            }), 404
        
        petugas_id = petugas_data['id']
        
        # Generate kode transaksi
        from datetime import datetime
        import random
        
        date_prefix = datetime.now().strftime('%y%m%d')
        random_suffix = str(random.randint(1000, 9999))
        
        if data['jenis'] == 'pemasukan':
            prefix = 'PM'
        elif data['jenis'] == 'pengeluaran':
            prefix = 'PL'
        elif data['jenis'] == 'gaji':
            prefix = 'GJ'
        elif data['jenis'] == 'topup':
            prefix = 'TP'
        else:
            prefix = 'TRX'
        
        kode_transaksi = f"{prefix}-{date_prefix}-{random_suffix}"
        
        # Mulai transaction
        conn.begin()
        
        try:
            # Query untuk insert transaksi
            query = """
                INSERT INTO transaksi (
                    kode_transaksi,
                    laporan_id,
                    warga_id,
                    petugas_id,
                    jenis,
                    kategori,
                    jumlah,
                    harga_per_karung,
                    total_karung,
                    metode_bayar,
                    status_bayar,
                    keterangan,
                    tanggal
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                kode_transaksi,
                data.get('laporan_id'),
                data.get('warga_id'),
                petugas_id,  # Petugas yang membuat
                data['jenis'],
                data.get('kategori'),
                float(data['jumlah']),
                data.get('harga_per_karung', 5000.00),
                data.get('total_karung'),
                data.get('metode_bayar', 'cash'),
                data.get('status_bayar', 'lunas'),
                data.get('keterangan'),
                datetime.now()
            )
            
            cursor.execute(query, values)
            transaksi_id = cursor.lastrowid
            
            # Jika transaksi pemasukan dari warga, update saldo warga
            if data['jenis'] == 'pemasukan' and data.get('warga_id'):
                update_saldo_query = """
                    UPDATE warga 
                    SET saldo = saldo - %s
                    WHERE id = %s
                """
                cursor.execute(update_saldo_query, (float(data['jumlah']), data['warga_id']))
            
            conn.commit()
            
            # Ambil data transaksi yang baru dibuat
            cursor.execute("SELECT * FROM transaksi WHERE id = %s", (transaksi_id,))
            new_transaksi = cursor.fetchone()
            
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Transaksi berhasil dibuat',
                'data': {
                    'id': transaksi_id,
                    'kode_transaksi': kode_transaksi,
                    'jenis': new_transaksi['jenis'],
                    'jumlah': float(new_transaksi['jumlah']),
                    'status_bayar': new_transaksi['status_bayar'],
                    'tanggal': new_transaksi['tanggal'].isoformat() if new_transaksi['tanggal'] else None
                }
            }), 201
            
        except Exception as e:
            conn.rollback()
            raise e
            
    except Exception as e:
        print(f"Error create_transaksi: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Gagal membuat transaksi',
            'error': str(e)
        }), 500

# 11. GET TRANSACTION PERIOD (Untuk Grafik/Chart)
@petugas_bp.route('/transaksi/period', methods=['GET'])
@token_required
def get_transaksi_period(current_user):
    """
    Mendapatkan data transaksi untuk periode tertentu (grafik)
    """
    try:
        period = request.args.get('period', 'today')
        
        # Jika user bukan petugas, return error
        if current_user['role'] != 'petugas':
            return jsonify({
                'success': False,
                'message': 'Akses ditolak. Hanya untuk petugas'
            }), 403
        
        # Connect to database
        conn = get_connection()
        cursor = conn.cursor()
        
        # Ambil data petugas yang login
        cursor.execute("SELECT id FROM petugas WHERE user_id = %s", (current_user['id'],))
        petugas_data = cursor.fetchone()
        
        if not petugas_data:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Data petugas tidak ditemukan'
            }), 404
        
        petugas_id = petugas_data['id']
        
        # Base query dengan filter periode
        if period == 'today':
            date_filter = "DATE(tanggal) = CURDATE()"
        elif period == 'week':
            date_filter = "YEARWEEK(tanggal, 1) = YEARWEEK(CURDATE(), 1)"
        elif period == 'month':
            date_filter = "MONTH(tanggal) = MONTH(CURDATE()) AND YEAR(tanggal) = YEAR(CURDATE())"
        elif period == 'year':
            date_filter = "YEAR(tanggal) = YEAR(CURDATE())"
        else:
            # Custom range: format YYYY-MM-DD to YYYY-MM-DD
            date_range = period.split('_')
            if len(date_range) == 2:
                date_filter = f"DATE(tanggal) BETWEEN '{date_range[0]}' AND '{date_range[1]}'"
            else:
                date_filter = "DATE(tanggal) = CURDATE()"
        
        # Query untuk chart/grafik
        query = f"""
            SELECT 
                DATE(tanggal) as tanggal,
                jenis,
                COALESCE(SUM(CASE WHEN jenis = 'pemasukan' THEN jumlah ELSE 0 END), 0) as total_pemasukan,
                COALESCE(SUM(CASE WHEN jenis = 'pengeluaran' THEN jumlah ELSE 0 END), 0) as total_pengeluaran,
                COALESCE(COUNT(*), 0) as jumlah_transaksi
            FROM transaksi
            WHERE {date_filter} AND petugas_id = %s
            GROUP BY DATE(tanggal), jenis 
            ORDER BY tanggal
        """
        
        cursor.execute(query, (petugas_id,))
        chart_data = cursor.fetchall()
        
        # Query untuk top 5 warga
        top_warga_query = f"""
            SELECT 
                w.nama_legkap,
                w.alamat_lengkap,
                COALESCE(COUNT(t.id), 0) as jumlah_transaksi,
                COALESCE(SUM(t.jumlah), 0) as total_nominal
            FROM transaksi t
            JOIN warga w ON t.warga_id = w.id
            WHERE {date_filter} AND t.petugas_id = %s AND t.jenis = 'pemasukan'
            GROUP BY w.id
            ORDER BY total_nominal DESC
            LIMIT 5
        """
        
        cursor.execute(top_warga_query, (petugas_id,))
        top_warga = cursor.fetchall()
        
        conn.close()
        
        # Format response
        formatted_chart = []
        for data in chart_data:
            formatted_chart.append({
                'tanggal': data['tanggal'].isoformat() if data['tanggal'] else None,
                'jenis': data['jenis'],
                'total_pemasukan': float(data['total_pemasukan']),
                'total_pengeluaran': float(data['total_pengeluaran']),
                'jumlah_transaksi': data['jumlah_transaksi']
            })
        
        formatted_top_warga = []
        for warga in top_warga:
            formatted_top_warga.append({
                'nama': warga['nama'],
                'alamat': warga['alamat'],
                'jumlah_transaksi': warga['jumlah_transaksi'],
                'total_nominal': float(warga['total_nominal'])
            })
        
        return jsonify({
            'success': True,
            'period': period,
            'chart_data': formatted_chart,
            'top_warga': formatted_top_warga
        }), 200
        
    except Exception as e:
        print(f"Error get_transaksi_period: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Gagal mengambil data transaksi periode',
            'error': str(e)
        }), 500

# 12. GET TRANSACTION DETAIL
@petugas_bp.route('/transaksi/<int:transaksi_id>', methods=['GET'])
@token_required
def get_transaksi_detail(current_user, transaksi_id):
    """
    Mendapatkan detail transaksi tertentu
    """
    try:
        # Jika user bukan petugas, return error
        if current_user['role'] != 'petugas':
            return jsonify({
                'success': False,
                'message': 'Akses ditolak. Hanya untuk petugas'
            }), 403
        
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                t.*,
                w.nama_lengkap as nama_warga,
                w.no_telepon as telepon_warga,
                w.alamat_lengkap as alamat_warga,
                w.rt as rt_warga,
                w.rw as rw_warga,
                p.nama_lengkap as nama_petugas,
                p.no_telepon as telepon_petugas,
                l.jenis_sampah,
                l.estimasi_volume,
                l.foto_sampah
            FROM transaksi t
            LEFT JOIN warga w ON t.warga_id = w.id
            LEFT JOIN petugas p ON t.petugas_id = p.id
            LEFT JOIN laporan l ON t.laporan_id = l.id
            WHERE t.id = %s
        """
        
        cursor.execute(query, (transaksi_id,))
        transaksi = cursor.fetchone()
        
        conn.close()
        
        if not transaksi:
            return jsonify({
                'success': False,
                'message': 'Transaksi tidak ditemukan'
            }), 404
        
        # Format response
        formatted_transaksi = {
            'id': transaksi['id'],
            'kode_transaksi': transaksi['kode_transaksi'],
            'jenis': transaksi['jenis'],
            'kategori': transaksi['kategori'],
            'jumlah': float(transaksi['jumlah']),
            'harga_per_karung': float(transaksi['harga_per_karung']) if transaksi['harga_per_karung'] else None,
            'total_karung': transaksi['total_karung'],
            'metode_bayar': transaksi['metode_bayar'],
            'status_bayar': transaksi['status_bayar'],
            'keterangan': transaksi['keterangan'],
            'tanggal': transaksi['tanggal'].isoformat() if transaksi['tanggal'] else None,
            'bukti_bayar': transaksi['bukti_bayar'],
            'warga_id': transaksi['warga_id'],
            'petugas_id': transaksi['petugas_id'],
            'laporan_id': transaksi['laporan_id'],
            'nama_warga': transaksi['nama_warga'],
            'telepon_warga': transaksi['telepon_warga'],
            'alamat_warga': transaksi['alamat_warga'],
            'rt_warga': transaksi['rt_warga'],
            'rw_warga': transaksi['rw_warga'],
            'nama_petugas': transaksi['nama_petugas'],
            'telepon_petugas': transaksi['telepon_petugas'],
            'jenis_sampah': transaksi['jenis_sampah'],
            'total_karung': transaksi['total_karung'],
            'foto_bukti': transaksi['foto_bukti']
        }
        
        return jsonify({
            'success': True,
            'data': formatted_transaksi
        }), 200
        
    except Exception as e:
        print(f"Error get_transaksi_detail: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Gagal mengambil detail transaksi',
            'error': str(e)
        }), 500