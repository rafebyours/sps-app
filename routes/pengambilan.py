# routes/pengambilan.py (File baru)
from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG
from datetime import datetime
import random
from .auth import token_required

pengambilan_bp = Blueprint('pengambilan', __name__, url_prefix='/api/pengambilan')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# POST /api/pengambilan - Tambah pengambilan manual/patroli
@pengambilan_bp.route('/', methods=['POST'])
@token_required
def create_pengambilan(current_user):
    """Create pengambilan manual/patroli"""
    data = request.get_json() or {}
    
    # Required fields
    type = data.get('type')  # 'manual' atau 'patroli'
    jumlah_karung = data.get('jumlah_karung')
    jenis_sampah = data.get('jenis_sampah')
    petugas_id = data.get('petugas_id') or current_user.get('petugas_id')
    
    if not all([type, jumlah_karung, jenis_sampah, petugas_id]):
        return jsonify({
            "success": False,
            "message": "type, jumlah_karung, jenis_sampah, dan petugas_id diperlukan"
        }), 400
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Mulai transaction
            conn.begin()
            
            # 1. Buat laporan manual
            cursor.execute("""
                INSERT INTO laporan (
                    kode_laporan, jenis_sampah, alamat_detail,
                    nama_pemohon, nomor_hp, keterangan, status,
                    tanggal_laporan, estimasi_volume, jumlah_karung
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
            """, (
                f"MAN-{datetime.now().strftime('%y%m%d')}-{random.randint(1000, 9999)}",
                jenis_sampah,
                data.get('alamat', 'Lokasi Patroli'),
                'Laporan Petugas',
                '',
                f"Pengambilan {type} oleh petugas",
                'selesai',  # Langsung selesai karena diambil langsung
                jumlah_karung,
                jumlah_karung
            ))
            
            laporan_id = cursor.lastrowid
            
            # 2. Buat transaksi jika ada biaya
            biaya = data.get('biaya', 0)
            if biaya > 0:
                kode_transaksi = f"TRX-{datetime.now().strftime('%y%m%d')}-{random.randint(1000, 9999)}"
                
                cursor.execute("""
                    INSERT INTO transaksi (
                        kode_transaksi, laporan_id, petugas_id,
                        jenis, kategori, jumlah, harga_per_karung,
                        total_karung, metode_bayar, status_bayar,
                        keterangan, tanggal
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    kode_transaksi,
                    laporan_id,
                    petugas_id,
                    'pemasukan',
                    'Pengambilan Sampah',
                    float(biaya),
                    5000,  # harga per karung default
                    int(jumlah_karung),
                    data.get('metode_bayar', 'cash'),
                    'lunas',
                    f"Pengambilan {type}: {data.get('keterangan', '')}"
                ))
            
            # 3. Update total karung petugas
            cursor.execute("""
                UPDATE petugas 
                SET total_karung = COALESCE(total_karung, 0) + %s
                WHERE id = %s
            """, (int(jumlah_karung), petugas_id))
            
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": f"Pengambilan {type} berhasil dicatat",
                "data": {
                    "laporan_id": laporan_id,
                    "jumlah_karung": jumlah_karung,
                    "biaya": biaya
                }
            }), 201
            
    except Exception as e:
        conn.rollback()
        print(f"Error create_pengambilan: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal mencatat pengambilan"
        }), 500
    finally:
        conn.close()