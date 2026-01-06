from flask import Blueprint, request, jsonify, make_response
import pymysql
from config import DB_CONFIG
import re
from werkzeug.security import generate_password_hash
from .auth import token_required

warga_bp = Blueprint('warga', __name__, url_prefix='/api/warga')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# CORS Middleware

@warga_bp.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    return response

# Helper function untuk validasi warga
def validate_warga_data(data, is_update=False):
    errors = []
    
    # Validasi nama
    if not is_update and (not data.get('nama_lengkap') or len(data['nama_lengkap']) < 2):
        errors.append("Nama lengkap minimal 2 karakter")
    
    # Validasi NIK
    nik = data.get('nik', '')
    if nik and (not nik.isdigit() or len(nik) != 16):
        errors.append("NIK harus 16 digit angka")
    
    # Validasi nomor telepon
    no_telepon = data.get('no_telepon', '')
    if no_telepon:
        if not re.match(r'^[0-9]{10,14}$', no_telepon):
            errors.append("Nomor telepon tidak valid (10-14 digit)")
    
    # Validasi email untuk user (wajib untuk create)
    if not is_update and not data.get('email'):
        errors.append("Email wajib diisi")
    elif data.get('email'):
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data['email']):
            errors.append("Format email tidak valid")
    
    # Validasi password untuk user baru
    if not is_update and (not data.get('password') or len(data['password']) < 6):
        errors.append("Password minimal 6 karakter")
    
    # Validasi RT/RW
    rt = data.get('rt', '')
    if rt and (not rt.isdigit() or int(rt) < 1 or int(rt) > 50):
        errors.append("RT harus angka 1-50")
    
    rw = data.get('rw', '')
    if rw and (not rw.isdigit() or int(rw) < 1 or int(rw) > 20):
        errors.append("RW harus angka 1-20")
    
    return errors

# 1. GET ALL WARGA
@warga_bp.route('/', methods=['GET'])
@token_required
def get_all_warga(current_user):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query untuk mengambil semua warga beserta data user
        cursor.execute("""
            SELECT 
                w.id,
                w.nama_lengkap,
                w.nik,
                w.no_telepon,
                w.alamat_lengkap,
                w.rt,
                w.rw,
                w.kelurahan,
                w.latitude,
                w.longitude,
                w.saldo,
                u.username,
                u.email,
                u.role,
                u.status as user_status,
                u.created_at
            FROM warga w
            JOIN users u ON w.user_id = u.id
            WHERE u.status = 'active'
            ORDER BY w.nama_lengkap ASC
        """)
        
        warga_list = cursor.fetchall()
        conn.close()
        
        # Format response
        formatted_data = []
        for warga in warga_list:
            formatted_data.append({
                'id': warga['id'],
                'nama_lengkap': warga['nama_lengkap'],
                'nik': warga['nik'],
                'no_telp': warga['no_telepon'],
                'alamat_lengkap': warga['alamat_lengkap'],
                'rt': warga['rt'],
                'rw': warga['rw'],
                'kelurahan': warga['kelurahan'] or 'Suraja',
                'latitude': float(warga['latitude']) if warga['latitude'] else None,
                'longitude': float(warga['longitude']) if warga['longitude'] else None,
                'saldo': float(warga['saldo']) if warga['saldo'] else 0.00,
                'username': warga['username'],
                'email': warga['email'],
                'user_status': warga['user_status'],
                'created_at': warga['created_at'].isoformat() if warga['created_at'] else None
            })
        
        return jsonify({
            'success': True,
            'count': len(formatted_data),
            'data': formatted_data
        }), 200
        
    except Exception as e:
        print(f"Error get_all_warga: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat mengambil data warga'
        }), 500

# 2. GET SINGLE WARGA
@warga_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_warga(current_user, id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                w.*,
                u.username,
                u.email,
                u.role,
                u.status as user_status,
                u.created_at
            FROM warga w
            JOIN users u ON w.user_id = u.id
            WHERE w.id = %s
        """, (id,))
        
        warga = cursor.fetchone()
        conn.close()
        
        if not warga:
            return jsonify({
                'success': False,
                'message': 'Warga tidak ditemukan'
            }), 404
        
        # Format response
        response_data = {
            'id': warga['id'],
            'nama_lengkap': warga['nama_lengkap'],
            'nik': warga['nik'],
            'no_telepon': warga['no_telepon'],
            'alamat_lengkap': warga['alamat_lengkap'],
            'rt': warga['rt'],
            'rw': warga['rw'],
            'kelurahan': warga['kelurahan'],
            'latitude': float(warga['latitude']) if warga['latitude'] else None,
            'longitude': float(warga['longitude']) if warga['longitude'] else None,
            'saldo': float(warga['saldo']) if warga['saldo'] else 0.00,
            'username': warga['username'],
            'email': warga['email'],
            'user_id': warga['user_id'],
            'user_status': warga['user_status'],
            'created_at': warga['created_at'].isoformat() if warga['created_at'] else None
        }
        
        return jsonify({
            'success': True,
            'data': response_data
        }), 200
        
    except Exception as e:
        print(f"Error get_warga: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat mengambil data warga'
        }), 500

# 3. CREATE NEW WARGA
@warga_bp.route('/', methods=['POST'])
@token_required
def create_warga(current_user):
    try:
        data = request.json
        
        # Validasi input
        validation_errors = validate_warga_data(data)
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
            cursor.execute("SELECT id FROM warga WHERE nik = %s", (data['nik'],))
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
                VALUES (%s, %s, %s, 'warga', 'active')
            """, (data['username'], data['email'], hashed_password))
            
            user_id = cursor.lastrowid
            
            # 2. Buat data warga
            cursor.execute("""
                INSERT INTO warga (
                    user_id, nama_lengkap, nik, no_telepon, alamat_lengkap,
                    rt, rw, kelurahan, latitude, longitude, saldo
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                data['nama_lengkap'],
                data.get('nik'),
                data.get('no_telepon'),
                data.get('alamat_lengkap'),
                data.get('rt'),
                data.get('rw'),
                data.get('kelurahan', 'Suraja'),
                float(data.get('latitude', 0)) if data.get('latitude') else None,
                float(data.get('longitude', 0)) if data.get('longitude') else None,
                float(data.get('saldo', 0))
            ))
            
            warga_id = cursor.lastrowid
            
            # Commit transaction
            conn.commit()
            
            # Ambil data yang baru dibuat
            cursor.execute("""
                SELECT 
                    w.*,
                    u.username,
                    u.email,
                    u.role,
                    u.status as user_status
                FROM warga w
                JOIN users u ON w.user_id = u.id
                WHERE w.id = %s
            """, (warga_id,))
            
            new_warga = cursor.fetchone()
            
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Warga berhasil ditambahkan',
                'data': {
                    'id': new_warga['id'],
                    'nama_lengkap': new_warga['nama_lengkap'],
                    'nik': new_warga['nik'],
                    'no_telp': new_warga['no_telepon'],
                    'alamat_lengkap': new_warga['alamat_lengkap'],
                    'rt': new_warga['rt'],
                    'rw': new_warga['rw'],
                    'kelurahan': new_warga['kelurahan'],
                    'saldo': float(new_warga['saldo']),
                    'username': new_warga['username'],
                    'email': new_warga['email']
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
        print(f"Error create_warga: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat menambahkan warga'
        }), 500

# 4. UPDATE WARGA
@warga_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_warga(current_user, id):
    try:
        data = request.json
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Cek apakah warga ada
        cursor.execute("""
            SELECT w.*, u.id as user_id 
            FROM warga w 
            JOIN users u ON w.user_id = u.id 
            WHERE w.id = %s
        """, (id,))
        
        warga = cursor.fetchone()
        
        if not warga:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Warga tidak ditemukan'
            }), 404
        
        # Hapus password dari data jika kosong
        if 'password' in data and (not data['password'] or data['password'].strip() == ''):
            data.pop('password', None)
        
        # Validasi untuk update
        validation_errors = validate_warga_data(data, is_update=True)
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
            # Update data warga
            update_fields = []
            update_values = []
            
            if 'nama_lengkap' in data:
                update_fields.append("nama_lengkap = %s")
                update_values.append(data['nama_lengkap'])
            
            if 'nik' in data:
                # Cek NIK duplikat
                cursor.execute("SELECT id FROM warga WHERE nik = %s AND id != %s", 
                             (data['nik'], id))
                if cursor.fetchone():
                    raise Exception("NIK sudah digunakan oleh warga lain")
                update_fields.append("nik = %s")
                update_values.append(data['nik'])
            
            if 'no_telepon' in data:
                update_fields.append("no_telepon = %s")
                update_values.append(data['no_telepon'])
            
            if 'alamat_lengkap' in data:
                update_fields.append("alamat_lengkap = %s")
                update_values.append(data['alamat_lengkap'])
            
            if 'rt' in data:
                update_fields.append("rt = %s")
                update_values.append(data['rt'])
            
            if 'rw' in data:
                update_fields.append("rw = %s")
                update_values.append(data['rw'])
            
            if 'kelurahan' in data:
                update_fields.append("kelurahan = %s")
                update_values.append(data['kelurahan'])
            
            if 'latitude' in data:
                update_fields.append("latitude = %s")
                update_values.append(float(data['latitude']) if data['latitude'] else None)
            
            if 'longitude' in data:
                update_fields.append("longitude = %s")
                update_values.append(float(data['longitude']) if data['longitude'] else None)
            
            if 'saldo' in data:
                update_fields.append("saldo = %s")
                update_values.append(float(data['saldo']))
            
            # Update warga jika ada field yang diubah
            if update_fields:
                update_values.append(id)
                update_query = f"UPDATE warga SET {', '.join(update_fields)} WHERE id = %s"
                cursor.execute(update_query, update_values)
            
            # Update user jika ada data yang perlu diubah
            user_update_fields = []
            user_update_values = []
            
            if 'username' in data:
                # Cek username duplikat
                cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", 
                             (data['username'], warga['user_id']))
                if cursor.fetchone():
                    raise Exception("Username sudah digunakan")
                user_update_fields.append("username = %s")
                user_update_values.append(data['username'])
            
            if 'email' in data:
                # Cek email duplikat
                cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", 
                             (data['email'], warga['user_id']))
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
                user_update_values.append(warga['user_id'])
                user_update_query = f"UPDATE users SET {', '.join(user_update_fields)} WHERE id = %s"
                cursor.execute(user_update_query, user_update_values)
            
            # Commit transaction
            conn.commit()
            
            # Ambil data yang sudah diupdate
            cursor.execute("""
                SELECT 
                    w.*,
                    u.username,
                    u.email,
                    u.role,
                    u.status as user_status
                FROM warga w
                JOIN users u ON w.user_id = u.id
                WHERE w.id = %s
            """, (id,))
            
            updated_warga = cursor.fetchone()
            
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Warga berhasil diperbarui',
                'data': {
                    'id': updated_warga['id'],
                    'nama_lengkap': updated_warga['nama_lengkap'],
                    'nik': updated_warga['nik'],
                    'no_telp': updated_warga['no_telepon'],
                    'alamat_lengkap': updated_warga['alamat_lengkap'],
                    'rt': updated_warga['rt'],
                    'rw': updated_warga['rw'],
                    'kelurahan': updated_warga['kelurahan'],
                    'saldo': float(updated_warga['saldo']),
                    'username': updated_warga['username'],
                    'email': updated_warga['email']
                }
            }), 200
            
        except Exception as e:
            conn.rollback()
            raise e
            
    except Exception as e:
        print(f"Error update_warga: {str(e)}")
        error_msg = str(e)
        if "duplicate" in error_msg.lower() or "sudah digunakan" in error_msg:
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat memperbarui warga'
        }), 500

# 5. DELETE WARGA (SOFT DELETE)
@warga_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_warga(current_user, id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Ambil data warga + user_id
        cursor.execute("""
            SELECT w.user_id, w.nama_lengkap
            FROM warga w
            WHERE w.id = %s
        """, (id,))
        warga = cursor.fetchone()
        
        if not warga:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Warga tidak ditemukan'
            }), 404
        
        conn.begin()
        
        # Nonaktifkan user
        cursor.execute("""
            UPDATE users
            SET status = 'inactive'
            WHERE id = %s
        """, (warga['user_id'],))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f"Warga {warga['nama_lengkap']} berhasil dinonaktifkan"
        }), 200
        
    except Exception as e:
        print(f"Error delete_warga: {e}")
        return jsonify({
            'success': False,
            'message': 'Gagal menghapus warga'
        }), 500

# 6. GET WARGA STATISTICS
@warga_bp.route('/stats', methods=['GET'])
@token_required
def get_warga_stats(current_user):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Hitung total warga
        cursor.execute("SELECT COUNT(*) as total FROM warga w JOIN users u ON w.user_id = u.id WHERE u.status = 'active'")
        total = cursor.fetchone()['total']
        
        # Hitung per RT
        cursor.execute("""
            SELECT rt, COUNT(*) as jumlah
            FROM warga w 
            JOIN users u ON w.user_id = u.id 
            WHERE u.status = 'active' AND rt IS NOT NULL
            GROUP BY rt
            ORDER BY rt
        """)
        per_rt = cursor.fetchall()
        
        # Total saldo semua warga
        cursor.execute("SELECT SUM(saldo) as total_saldo FROM warga w JOIN users u ON w.user_id = u.id WHERE u.status = 'active'")
        total_saldo = cursor.fetchone()['total_saldo'] or 0
        
        # Warga dengan saldo tertinggi
        cursor.execute("""
            SELECT nama_lengkap, saldo
            FROM warga w 
            JOIN users u ON w.user_id = u.id 
            WHERE u.status = 'active'
            ORDER BY saldo DESC
            LIMIT 5
        """)
        top_saldo = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'per_rt': per_rt,
                'total_saldo': float(total_saldo),
                'top_saldo': [
                    {'nama': row['nama_lengkap'], 'saldo': float(row['saldo'])} 
                    for row in top_saldo
                ]
            }
        }), 200
        
    except Exception as e:
        print(f"Error get_warga_stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat mengambil statistik'
        }), 500

# 7. SEARCH WARGA
@warga_bp.route('/search', methods=['GET'])
@token_required
def search_warga(current_user):
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
                w.id,
                w.nama_lengkap,
                w.no_telepon,
                w.rt,
                w.rw,
                w.saldo,
                u.username,
                u.email
            FROM warga w
            JOIN users u ON w.user_id = u.id
            WHERE u.status = 'active'
            AND (
                w.nama_lengkap LIKE %s OR
                w.no_telepon LIKE %s OR
                u.username LIKE %s OR
                u.email LIKE %s OR
                w.nik LIKE %s
            )
            ORDER BY w.nama_lengkap ASC
            LIMIT 20
        """, (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern))
        
        results = cursor.fetchall()
        conn.close()
        
        formatted_results = []
        for warga in results:
            formatted_results.append({
                'id': warga['id'],
                'nama_lengkap': warga['nama_lengkap'],
                'no_telp': warga['no_telepon'],
                'rt': warga['rt'],
                'rw': warga['rw'],
                'saldo': float(warga['saldo']) if warga['saldo'] else 0,
                'username': warga['username'],
                'email': warga['email']
            })
        
        return jsonify({
            'success': True,
            'count': len(formatted_results),
            'data': formatted_results
        }), 200
        
    except Exception as e:
        print(f"Error search_warga: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat mencari warga'
        }), 500

# 8. TOPUP SALDO WARGA
@warga_bp.route('/<int:id>/topup', methods=['POST'])
@token_required
def topup_saldo(current_user, id):
    try:
        data = request.json
        jumlah = data.get('jumlah')
        
        if not jumlah or float(jumlah) <= 0:
            return jsonify({
                'success': False,
                'message': 'Jumlah topup harus lebih dari 0'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Cek apakah warga ada
        cursor.execute("SELECT id, saldo, nama_lengkap FROM warga WHERE id = %s", (id,))
        warga = cursor.fetchone()
        
        if not warga:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Warga tidak ditemukan'
            }), 404
        
        # Update saldo
        new_saldo = float(warga['saldo']) + float(jumlah)
        cursor.execute("UPDATE warga SET saldo = %s WHERE id = %s", (new_saldo, id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Saldo {warga["nama_lengkap"]} berhasil ditambahkan Rp {jumlah:,}',
            'data': {
                'saldo_sebelum': float(warga['saldo']),
                'saldo_sesudah': new_saldo
            }
        }), 200
        
    except Exception as e:
        print(f"Error topup_saldo: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat topup saldo'
        }), 500
        
@warga_bp.route('/by-user/<int:user_id>', methods=['GET'])
def get_warga_by_user_id(user_id):
    """Get warga data by user_id"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT 
                    id,
                    nama_lengkap,
                    alamat_lengkap,
                    no_telepon,
                    user_id
                FROM warga 
                WHERE user_id = %s
            """
            cursor.execute(sql, (user_id,))
            warga = cursor.fetchone()
            
            if not warga:
                return jsonify({
                    "success": False,
                    "message": "Data warga tidak ditemukan"
                }), 404
            
            return jsonify({
                "success": True,
                "data": warga,
                "message": "Data warga ditemukan"
            }), 200
            
    except Exception as e:
        print(f"Error in get_warga_by_user_id: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal mengambil data warga"
        }), 500
    finally:
        conn.close()
        
        
# 9. GET WARGA LIST UNTUK DROPDOWN (simple)
# Di warga.py (TAMBAHKAN setelah fungsi-fungsi lain):
# 9. GET WARGA LIST FOR DROPDOWN
# 9. GET WARGA LIST FOR DROPDOWN
@warga_bp.route('/list', methods=['GET'])
@token_required
def get_warga_list(current_user):
    try:
        print("=" * 50)
        print(f"📋 GET WARGA LIST DIPANGGIL oleh: {current_user}")
        print(f"📋 User ID: {current_user['id']}, Role: {current_user['role']}")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query untuk mengambil data warga
        query = """
            SELECT 
                w.id,
                w.nama_lengkap,
                w.alamat_lengkap,
                w.rt,
                w.rw,
                COALESCE(w.saldo, 0) as saldo,
                w.no_telepon
            FROM warga w
            JOIN users u ON w.user_id = u.id
            WHERE u.status = 'active'
            ORDER BY w.nama_lengkap ASC
        """
        
        print(f"📋 Executing query: {query}")
        cursor.execute(query)
        warga_list = cursor.fetchall()
        
        print(f"📋 Found {len(warga_list)} warga")
        for i, warga in enumerate(warga_list[:5]):  # Log 5 pertama
            print(f"  {i+1}. {warga['nama_lengkap']} (ID: {warga['id']})")
        
        if len(warga_list) > 5:
            print(f"  ... dan {len(warga_list) - 5} lainnya")
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': warga_list,
            'count': len(warga_list),
            'message': f'Ditemukan {len(warga_list)} warga aktif'
        }), 200
        
    except Exception as e:
        print(f"❌ ERROR in get_warga_list: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Gagal mengambil data warga',
            'error': str(e)
        }), 500