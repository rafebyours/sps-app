from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG
from datetime import datetime
import random
import json
from .auth import token_required

transaksi_bp = Blueprint('transaksi', __name__, url_prefix='/api/transaksi')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# Generate kode transaksi
def generate_kode_transaksi(jenis):
    prefix_map = {
        'pemasukan': 'PM',
        'pengeluaran': 'PL',
        'gaji': 'GJ',
        'topup': 'TP'
    }
    
    prefix = prefix_map.get(jenis, 'TRX')
    date_str = datetime.now().strftime('%y%m%d')
    random_suffix = str(random.randint(1000, 9999))
    
    return f"{prefix}-{date_str}-{random_suffix}"

# Endpoint untuk pengambilan sampah
@transaksi_bp.route('/pengambilan', methods=['POST'])
@token_required
def create_pengambilan(current_user):
    """Membuat transaksi pengambilan sampah"""
    try:
        data = request.json
        print("=" * 50)
        print("DATA PENERIMAAN CREATE_PENGAMBILAN:")
        print(json.dumps(data, indent=2))
        print("=" * 50)
        
        # Validasi data wajib
        required_fields = ['total_karung', 'harga_per_karung', 'jumlah', 'petugas_id']
        for field in required_fields:
            if field not in data:
                print(f"❌ Field {field} tidak ditemukan dalam data")
                return jsonify({
                    'success': False,
                    'message': f'Field {field} harus diisi'
                }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Mulai transaction
        conn.begin()
        
        try:
            # 1. Generate kode transaksi
            kode_transaksi = generate_kode_transaksi(data.get('jenis', 'pemasukan'))
            print(f"✅ Kode transaksi: {kode_transaksi}")
            
            # 2. Insert ke tabel transaksi
            transaksi_query = """
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
            
            transaksi_values = (
                kode_transaksi,
                data.get('laporan_id'),
                data.get('warga_id'),
                data['petugas_id'],
                data.get('jenis', 'pemasukan'),
                data.get('kategori', 'Pengambilan Sampah'),
                float(data['jumlah']),
                float(data['harga_per_karung']),
                int(data['total_karung']),
                data.get('metode_bayar', 'cash'),
                data.get('status_bayar', 'lunas'),
                data.get('keterangan', ''),
                data.get('tanggal', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            
            print(f"✅ Eksekusi query transaksi")
            cursor.execute(transaksi_query, transaksi_values)
            transaksi_id = cursor.lastrowid
            print(f"✅ Transaksi ID: {transaksi_id}")
            
            # 3. Insert ke tabel pemasukan
            pemasukan_query = """
                INSERT INTO pemasukan (
                    tanggal,
                    jumlah,
                    kategori,
                    keterangan
                ) VALUES (%s, %s, %s, %s)
            """
            
            pemasukan_values = (
                datetime.now().strftime('%Y-%m-%d'),
                float(data['jumlah']),
                data.get('kategori', 'Pengambilan Sampah'),
                f"Transaksi {kode_transaksi}: {data.get('keterangan', '')}"
            )
            
            print(f"✅ Eksekusi query pemasukan")
            cursor.execute(pemasukan_query, pemasukan_values)
            pemasukan_id = cursor.lastrowid
            print(f"✅ Pemasukan ID: {pemasukan_id}")
            
            # 4. Update status laporan jika ada laporan_id
            if data.get('laporan_id'):
                print(f"✅ Update laporan ID: {data['laporan_id']}")
                update_laporan_query = """
                    UPDATE laporan 
                    SET status = 'selesai',
                        tanggal_selesai = NOW(),
                        catatan_petugas = CONCAT('Pengambilan selesai: ', %s, ' karung @ Rp ', %s)
                    WHERE id = %s
                """
                
                catatan = f"{data.get('total_karung')} karung @ Rp {data.get('harga_per_karung'):,}"
                cursor.execute(update_laporan_query, (data['total_karung'], data['harga_per_karung'], data['laporan_id']))
                print(f"✅ Laporan diupdate ke status 'selesai'")
                
                # Cek apakah update berhasil
                cursor.execute("SELECT status FROM laporan WHERE id = %s", (data['laporan_id'],))
                updated_laporan = cursor.fetchone()
                print(f"✅ Status laporan setelah update: {updated_laporan['status']}")
            
            # 5. Update total karung petugas
            if data.get('petugas_id'):
                print(f"✅ Update petugas ID: {data['petugas_id']}")
                update_petugas_query = """
                    UPDATE petugas 
                    SET total_karung = COALESCE(total_karung, 0) + %s
                    WHERE id = %s
                """
                
                cursor.execute(update_petugas_query, (int(data['total_karung']), data['petugas_id']))
                print(f"✅ Petugas ditambah {data['total_karung']} karung")
            
            # 6. Update saldo warga jika pemasukan dan ada warga_id
            if data.get('warga_id') and data.get('jenis') == 'pemasukan' and data.get('status_bayar') == 'lunas':
                print(f"✅ Update saldo warga ID: {data['warga_id']}")
                update_warga_query = """
                    UPDATE warga 
                    SET saldo = COALESCE(saldo, 0) + %s
                    WHERE id = %s
                """
                
                cursor.execute(update_warga_query, (float(data['jumlah']), data['warga_id']))
                print(f"✅ Saldo warga dikurangi Rp {data['jumlah']}")
            
            # Commit semua perubahan
            conn.commit()
            print("✅ Semua perubahan di-commit ke database")
            
            # Ambil data transaksi yang baru dibuat
            cursor.execute("""
                SELECT t.*, p.nama_lengkap as nama_petugas, w.nama_lengkap as nama_warga
                FROM transaksi t
                LEFT JOIN petugas p ON t.petugas_id = p.id
                LEFT JOIN warga w ON t.warga_id = w.id
                WHERE t.id = %s
            """, (transaksi_id,))
            
            transaksi_detail = cursor.fetchone()
            
            conn.close()
            
            print("=" * 50)
            print("✅ TRANSAKSI BERHASIL DIBUAT")
            print(f"Transaksi ID: {transaksi_id}")
            print(f"Kode: {kode_transaksi}")
            print(f"Jumlah: Rp {data['jumlah']:,.0f}")
            print(f"Karung: {data['total_karung']}")
            print("=" * 50)
            
            return jsonify({
                'success': True,
                'message': 'Pengambilan berhasil dicatat',
                'data': {
                    'transaksi': {
                        'id': transaksi_id,
                        'kode': kode_transaksi,
                        'jumlah': float(data['jumlah']),
                        'total_karung': int(data['total_karung'])
                    },
                    'pemasukan_id': pemasukan_id,
                    'detail': transaksi_detail
                }
            }), 201
            
        except Exception as e:
            conn.rollback()
            print(f"❌ ERROR dalam transaction: {str(e)}")
            import traceback
            traceback.print_exc()
            raise e
            
    except Exception as e:
        print(f"❌ ERROR in create_pengambilan: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Gagal mencatat pengambilan',
            'error': str(e)
        }), 500

# Endpoint untuk mendapatkan detail transaksi
@transaksi_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_transaksi_detail(current_user, id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                t.*,
                p.nama_lengkap as nama_petugas,
                w.nama_lengkap as nama_warga,
                l.kode_laporan,
                l.jenis_sampah
            FROM transaksi t
            LEFT JOIN petugas p ON t.petugas_id = p.id
            LEFT JOIN warga w ON t.warga_id = w.id
            LEFT JOIN laporan l ON t.laporan_id = l.id
            WHERE t.id = %s
        """, (id,))
        
        transaksi = cursor.fetchone()
        conn.close()
        
        if not transaksi:
            return jsonify({
                'success': False,
                'message': 'Transaksi tidak ditemukan'
            }), 404
        
        return jsonify({
            'success': True,
            'data': transaksi
        }), 200
        
    except Exception as e:
        print(f"Error in get_transaksi_detail: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Gagal mengambil detail transaksi'
        }), 500

# Endpoint untuk mendapatkan transaksi petugas
@transaksi_bp.route('/petugas/<int:petugas_id>', methods=['GET'])
@token_required
def get_transaksi_petugas(current_user, petugas_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Parameter
        tanggal = request.args.get('tanggal', '')
        limit = request.args.get('limit', 50)
        
        query = """
            SELECT 
                t.*,
                w.nama_lengkap as nama_warga,
                l.kode_laporan,
                l.jenis_sampah
            FROM transaksi t
            LEFT JOIN warga w ON t.warga_id = w.id
            LEFT JOIN laporan l ON t.laporan_id = l.id
            WHERE t.petugas_id = %s
        """
        
        params = [petugas_id]
        
        if tanggal:
            query += " AND DATE(t.tanggal) = %s"
            params.append(tanggal)
        
        query += " ORDER BY t.tanggal DESC LIMIT %s"
        params.append(int(limit))
        
        cursor.execute(query, params)
        transaksi_list = cursor.fetchall()
        
        # Hitung total
        total_query = """
            SELECT 
                COUNT(*) as total_transaksi,
                SUM(total_karung) as total_karung,
                SUM(jumlah) as total_pendapatan
            FROM transaksi 
            WHERE petugas_id = %s
        """
        
        if tanggal:
            total_query += " AND DATE(tanggal) = %s"
            cursor.execute(total_query, (petugas_id, tanggal))
        else:
            cursor.execute(total_query, (petugas_id,))
        
        total = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': transaksi_list,
            'total': total
        }), 200
        
    except Exception as e:
        print(f"Error in get_transaksi_petugas: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Gagal mengambil data transaksi petugas'
        }), 500