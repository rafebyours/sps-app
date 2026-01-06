from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG
from .auth import token_required

lokasi_bp = Blueprint('lokasi', __name__, url_prefix='/api/lokasi')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# HAPUS CORS middleware yang duplikat, biarkan di app.py saja
# Atau gunakan decorator @cross_origin jika perlu

# 1. GET LOKASI PETUGAS
# lokasi.py
@lokasi_bp.route('/petugas', methods=['GET'])
@token_required
def get_lokasi_petugas(current_user):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                p.id,
                p.nama_lengkap,
                p.no_telepon,
                p.live_latitude,
                p.live_longitude
            FROM petugas p
            JOIN users u ON p.user_id = u.id
            WHERE p.live_latitude IS NOT NULL
            AND p.live_longitude IS NOT NULL
            AND p.is_online = 1

        """)

        data = cursor.fetchall()
        conn.close()

        return jsonify({
            'success': True,
            'count': len(data),
            'data': data
        }), 200

    except Exception as e:
        print("Error get_lokasi_petugas:", e)
        return jsonify({
            'success': False,
            'message': 'Gagal mengambil lokasi petugas'
        }), 500


# 2. UPDATE LOKASI PETUGAS (untuk mobile app petugas)
@lokasi_bp.route('/petugas/<int:id>', methods=['PUT'])
@token_required
def update_lokasi_petugas(current_user, id):
    try:
        data = request.json
        
        # Validasi input
        if not data.get('latitude') or not data.get('longitude'):
            return jsonify({
                'success': False,
                'message': 'Latitude dan longitude wajib diisi'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Update lokasi petugas
        cursor.execute("""
            UPDATE petugas 
            SET live_latitude = %s,
            live_longitude = %s,
            live_location_updated = NOW(),
            is_online = 1
            WHERE id = %s
        """, (data['latitude'], data['longitude'], id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Lokasi petugas berhasil diperbarui'
        }), 200
        
    except Exception as e:
        print(f"Error in update_lokasi_petugas: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat memperbarui lokasi petugas'
        }), 500

# 3. GET LOKASI PETUGAS TERDEKAT
@lokasi_bp.route('/petugas/terdekat', methods=['GET'])
@token_required
def get_petugas_terdekat(current_user):
    try:
        # Ambil parameter latitude dan longitude dari query string
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', 5, type=float)  # radius dalam km
        
        if not lat or not lng:
            return jsonify({
                'success': False,
                'message': 'Parameter latitude dan longitude diperlukan'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query untuk mencari petugas terdekat (Haversine formula)
        cursor.execute("""
            SELECT 
                p.id,
                p.nama_lengkap as nama_petugas,
                p.latitude,
                p.longitude,
                p.no_telepon,
                u.username,
                (6371 * acos(cos(radians(%s)) * cos(radians(p.latitude)) 
                * cos(radians(p.longitude) - radians(%s)) + sin(radians(%s)) 
                * sin(radians(p.latitude)))) AS distance_km
            FROM petugas p
            JOIN users u ON p.user_id = u.id
            WHERE u.status = 'active' 
            AND p.latitude IS NOT NULL 
            AND p.longitude IS NOT NULL
            HAVING distance_km <= %s
            ORDER BY distance_km ASC
            LIMIT 10
        """, (lat, lng, lat, radius))
        
        petugas_list = cursor.fetchall()
        conn.close()
        
        # Format response
        formatted_data = []
        for petugas in petugas_list:
            formatted_data.append({
                'id': petugas['id'],
                'nama_petugas': petugas['nama_petugas'],
                'latitude': float(petugas['latitude']),
                'longitude': float(petugas['longitude']),
                'no_telepon': petugas['no_telepon'],
                'username': petugas['username'],
                'distance_km': round(float(petugas['distance_km']), 2)
            })
        
        return jsonify({
            'success': True,
            'count': len(formatted_data),
            'data': formatted_data
        }), 200
        
    except Exception as e:
        print(f"Error in get_petugas_terdekat: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan saat mencari petugas terdekat'
        }), 500
        
        
# 4. LOGOUT PETUGAS (set is_online = 0)
@lokasi_bp.route('/petugas/logout', methods=['POST'])
@token_required
def logout_petugas(current_user):
    print("🔥 LOGOUT PETUGAS DIPANGGIL")

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE petugas
            SET 
                is_online = 0,
                live_latitude = NULL,
                live_longitude = NULL,
                live_location_updated = NOW()
            WHERE id = %s
        """, (current_user['petugas_id'],))

        conn.commit()
        print("ROW AFFECTED:", cursor.rowcount)

        return jsonify({
            "success": True,
            "message": "Logout & live location cleared"
        }), 200

    except Exception as e:
        print("❌ ERROR LOGOUT PETUGAS:", e)
        return jsonify({
            "success": False,
            "message": "Gagal logout petugas"
        }), 500

    finally:
        if 'conn' in locals():
            conn.close()
