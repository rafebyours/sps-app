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