from flask import Blueprint, request, jsonify, make_response
import pymysql
from config import DB_CONFIG
import jwt
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from functools import wraps

# Load environment variables
load_dotenv()

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'fallback_secret_key_change_in_production')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# Token verification decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        # ✅ PENTING: BIAR CORS OPTIONS LOLOS
        if request.method == 'OPTIONS':
            return make_response('', 200)

        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Token is missing!'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401
        except Exception:
            return jsonify({'message': 'Token verification failed!'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

# Login endpoint
@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        
        if not data:
            return jsonify({"message": "No data provided"}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"message": "Username and password are required"}), 400
        
        conn = get_connection()
        
        try:
            with conn.cursor() as cursor:
                # QUERY LENGKAP - ambil semua data warga sekaligus
                cursor.execute("""
                    SELECT 
                        u.id,
                        u.username,
                        u.password,
                        u.role,
                        u.status,
                        u.created_at,
                        w.id as warga_id,
                        w.nama_lengkap as warga_nama,
                        w.alamat_lengkap,
                        w.rt,
                        w.rw,
                        w.kelurahan,
                        w.saldo,
                        w.no_telepon,
                        p.id as petugas_id,
                        p.nama_lengkap as petugas_nama,
                        p.no_telepon as petugas_no_telepon
                    FROM users u
                    LEFT JOIN warga w ON u.id = w.user_id
                    LEFT JOIN petugas p ON u.id = p.user_id
                    WHERE u.username = %s
                """, (username,))
                
                user = cursor.fetchone()
                
        finally:
            conn.close()
        
        if not user:
            return jsonify({"message": "User not found"}), 404
        
        if user['status'] != 'active':
            return jsonify({"message": "Account is inactive"}), 403
        
        if not check_password_hash(user['password'], password):
            return jsonify({"message": "Invalid password"}), 401
        
        # Tentukan data berdasarkan role
        if user['role'] == 'warga':
            nama = user['warga_nama']
            telepon = user['no_telepon']
            id_spesifik = user['warga_id']
        elif user['role'] == 'petugas':
            nama = user['petugas_nama']
            telepon = user['petugas_no_telepon']
            id_spesifik = user['petugas_id']
        else:
            nama = None
            telepon = None
            id_spesifik = None
        
        # Token payload
        payload = {
            "id": user['id'],
            "username": user['username'],
            "role": user['role'],
            "nama": nama,
            "no_telepon": telepon,
            "saldo": float(user['saldo']) if user['saldo'] is not None else None,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        }
        
        # Generate token
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        
        # User data untuk response - SEMUA DATA WARGA DIMASUKKAN
        user_data = {
            "id": user['id'],
            "username": user['username'],
            "role": user['role'],
            "nama": nama,
            "no_telepon": telepon,
            "saldo": float(user['saldo']) if user['saldo'] is not None else None,
            "created_at": user['created_at'].isoformat() if user.get('created_at') else None
        }
        
        # Tambah data lengkap untuk warga
        if user['role'] == 'warga':
            user_data.update({
                "warga_id": user['warga_id'],
                "alamat": user['alamat_lengkap'],
                "rt": user['rt'],
                "rw": user['rw'],
                "wilayah": user['kelurahan'] or 'Suraja'
            })
        
        return jsonify({
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": user_data
        }), 200
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500

# Verify token endpoint
@auth_bp.route('/verify', methods=['GET'])
@token_required
def verify_token(current_user):
    return jsonify({
        "success": True,
        "valid": True,
        "user": current_user
    }), 200

# Logout endpoint
@auth_bp.route('/logout', methods=['POST'])
def logout():
    try:
        # In a stateless JWT system, logout is handled client-side
        # But we can blacklist tokens if needed (requires token store)
        response = jsonify({
            "success": True,
            "message": "Logout successful"
        })
        
        return response, 200
        
    except Exception as e:
        print(f"Logout error: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Server error during logout"
        }), 500

# Get current user info
@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    try:
        conn = get_connection()
        
        try:
            with conn.cursor() as cursor:
                # Get updated user info from database
                cursor.execute("""
                    SELECT 
                        u.id,
                        u.username,
                        u.role,
                        u.status,
                        u.created_at,
                        CASE 
                            WHEN u.role = 'warga' THEN w.nama_lengkap
                            WHEN u.role = 'petugas' THEN p.nama_lengkap
                            ELSE NULL 
                        END as nama,
                        CASE 
                            WHEN u.role = 'warga' THEN w.saldo
                            ELSE NULL 
                        END as saldo,
                        CASE 
                            WHEN u.role = 'warga' THEN w.no_telepon
                            WHEN u.role = 'petugas' THEN p.no_telepon
                            ELSE NULL 
                        END as no_telepon
                    FROM users u
                    LEFT JOIN warga w ON u.id = w.user_id AND u.role = 'warga'
                    LEFT JOIN petugas p ON u.id = p.user_id AND u.role = 'petugas'
                    WHERE u.id = %s
                """, (current_user['id'],))
                
                user = cursor.fetchone()
                
        finally:
            conn.close()
        
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        # Prepare response data
        user_data = {
            "id": user['id'],
            "username": user['username'],
            "role": user['role'],
            "nama": user.get('nama'),
            "no_telepon": user.get('no_telepon'),
            "saldo": float(user.get('saldo', 0)) if user.get('saldo') is not None else None,
            "status": user['status'],
            "created_at": user['created_at'].isoformat() if user.get('created_at') else None
        }
        
        return jsonify({
            "success": True,
            "user": user_data
        }), 200
        
    except Exception as e:
        print(f"Get user error: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500