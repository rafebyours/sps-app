# routes/riwayat.py
from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG
from datetime import datetime, timedelta
from .auth import token_required
import json

riwayat_bp = Blueprint('riwayat', __name__, url_prefix='/api/riwayat')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

# ============ HELPER FUNCTIONS ============
def get_hari_indonesia(tanggal_str):
    try:
        if isinstance(tanggal_str, str):
            try:
                tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d %H:%M:%S')
            except:
                tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d')
        else:
            tanggal = tanggal_str
            
        hari_dict = {
            0: 'Minggu', 1: 'Senin', 2: 'Selasa', 3: 'Rabu',
            4: 'Kamis', 5: 'Jumat', 6: 'Sabru'
        }
        return hari_dict[tanggal.weekday()]
    except:
        return ''

def format_tanggal_singkat(tanggal_str):
    try:
        if isinstance(tanggal_str, str):
            try:
                tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d %H:%M:%S')
            except:
                tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d')
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
            try:
                tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d %H:%M:%S')
            except:
                return ''
        else:
            tanggal = tanggal_str
            
        return tanggal.strftime('%H:%M')
    except:
        return ''

def format_tanggal_lengkap(tanggal_str):
    try:
        if isinstance(tanggal_str, str):
            try:
                tanggal = datetime.strptime(tanggal_str, '%Y-%m-d %H:%M:%S')
            except:
                tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d')
        else:
            tanggal = tanggal_str
            
        hari = get_hari_indonesia(tanggal_str)
        bulan_lengkap = [
            'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ]
        
        return f"{hari}, {tanggal.day} {bulan_lengkap[tanggal.month - 1]} {tanggal.year}"
    except:
        return ''

# ============ ENDPOINTS ============

# 1. GET RIWAYAT UNTUK USER (Gabungan laporan + transaksi)
@riwayat_bp.route('/user', methods=['GET'])
@token_required
def get_riwayat_user(current_user):
    try:
        bulan = request.args.get('bulan')  # Format: YYYY-MM
        tahun = request.args.get('tahun')  # Format: YYYY
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        tipe = request.args.get('tipe')  # 'laporan' atau 'transaksi' atau None (semua)
        
        offset = (page - 1) * limit
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get user's warga id
        cursor.execute("SELECT id FROM warga WHERE user_id = %s", (current_user['id'],))
        warga = cursor.fetchone()
        
        if not warga:
            return jsonify({"success": False, "message": "Data warga tidak ditemukan"}), 404
        
        id_warga = warga['id']
        
        # ============ DATA LAPORAN ============
        laporan_data = []
        if not tipe or tipe == 'laporan':
            # PERBAIKAN: Tidak ada kolom id_petugas di laporan, hapus JOIN dengan petugas
            sql_laporan = """
                SELECT 
                    l.id,
                    l.kode_laporan as kode,
                    'laporan' as tipe,
                    l.jenis_sampah,
                    l.estimasi_volume,
                    l.status,
                    l.tanggal_laporan as tanggal,
                    l.waktu_pengambilan,
                    l.keterangan,
                    l.catatan_petugas,
                    l.alamat_detail,
                    l.rt,
                    l.rw,
                    l.nomor_hp,
                    l.nama_pemohon,
                    l.foto_sampah,
                    l.tanggal_verifikasi,
                    l.tanggal_selesai,
                    w.nama_lengkap as nama_warga
                FROM laporan l
                JOIN warga w ON l.id_warga = w.id
                WHERE l.id_warga = %s
                AND l.status NOT IN ('selesai', 'dibatalkan')
            """
            params_laporan = [id_warga]
            
            if bulan:
                sql_laporan += " AND DATE_FORMAT(l.tanggal_laporan, '%%Y-%%m') = %s"
                params_laporan.append(bulan)
            if tahun:
                sql_laporan += " AND YEAR(l.tanggal_laporan) = %s"
                params_laporan.append(tahun)
            
            sql_laporan += " ORDER BY l.tanggal_laporan DESC"
            
            cursor.execute(sql_laporan, params_laporan)
            laporan_rows = cursor.fetchall()
            
            for row in laporan_rows:
                # Format estimasi volume ke jumlah karung
                estimasi_volume = row['estimasi_volume']
                jumlah_karung = 0
                if estimasi_volume == 'sedikit':
                    jumlah_karung = 1
                elif estimasi_volume == 'sedang':
                    jumlah_karung = 2
                elif estimasi_volume == 'banyak':
                    jumlah_karung = 3
                
                # Format status
                status_map = {
                    'menunggu': 'pending',
                    'diproses': 'proses',
                    'diverifikasi': 'verifikasi',
                    'selesai': 'selesai',
                    'dibatalkan': 'ditolak'
                }
                status = status_map.get(row['status'], row['status'])
                
                laporan_data.append({
                    'id': row['id'],
                    'kode': row['kode'],
                    'tipe': 'laporan',
                    'jenis': 'Pengambilan Sampah',
                    'jumlah_karung': jumlah_karung,
                    'status': status,
                    'catatan': row['keterangan'] or row['catatan_petugas'] or '',
                    'tanggal': row['tanggal'].strftime('%Y-%m-%d %H:%M:%S') if row['tanggal'] else None,
                    'tanggal_verifikasi': row['tanggal_verifikasi'].strftime('%Y-%m-%d %H:%M:%S') if row['tanggal_verifikasi'] else None,
                    'tanggal_selesai': row['tanggal_selesai'].strftime('%Y-%m-%d %H:%M:%S') if row['tanggal_selesai'] else None,
                    'petugas': {
                        'nama': 'Belum ditugaskan',  # Karena tidak ada petugas di laporan
                        'telp': ''
                    },
                    'waktu_pengambilan': row['waktu_pengambilan'],
                    'jenis_sampah': row['jenis_sampah'],
                    'estimasi_volume': estimasi_volume,
                    'alamat': row['alamat_detail'] or '',
                    'rt': row['rt'],
                    'rw': row['rw'],
                    'pemohon': row['nama_pemohon'],
                    'telepon': row['nomor_hp'],
                    'foto_sampah': row['foto_sampah'],
                    # Field helper
                    'hari': get_hari_indonesia(row['tanggal']),
                    'tanggal_singkat': format_tanggal_singkat(row['tanggal']),
                    'waktu': format_waktu(row['tanggal']),
                    'tanggal_lengkap': format_tanggal_lengkap(row['tanggal'])
                })
        
        # ============ DATA TRANSAKSI ============
        transaksi_data = []
        if not tipe or tipe == 'transaksi':
            sql_transaksi = """
                SELECT 
                    t.id,
                    t.kode_transaksi as kode,
                    'transaksi' as tipe,
                    t.jenis,
                    t.kategori,
                    t.jumlah,
                    t.harga_per_karung,
                    t.total_karung,
                    t.status_bayar as status,
                    t.keterangan as catatan,
                    t.tanggal,
                    t.metode_bayar,
                    t.bukti_bayar,
                    p.nama_lengkap as nama_petugas,
                    w.nama_lengkap as nama_warga
                FROM transaksi t
                LEFT JOIN petugas p ON t.petugas_id = p.id
                LEFT JOIN warga w ON t.warga_id = w.id
                WHERE t.warga_id = %s
            """
            params_transaksi = [id_warga]
            
            if bulan:
                sql_transaksi += " AND DATE_FORMAT(t.tanggal, '%%Y-%%m') = %s"
                params_transaksi.append(bulan)
            if tahun:
                sql_transaksi += " AND YEAR(t.tanggal) = %s"
                params_transaksi.append(tahun)
            
            sql_transaksi += " ORDER BY t.tanggal DESC"
            
            cursor.execute(sql_transaksi, params_transaksi)
            transaksi_rows = cursor.fetchall()
            
            for row in transaksi_rows:
                # Tentukan jenis transaksi untuk frontend
                if row['jenis'] == 'pemasukan' and row['kategori'] == 'Iuran Warga':
                    jenis_transaksi = 'Iuran Bulanan'
                elif row['jenis'] == 'pemasukan':
                    jenis_transaksi = 'Pembayaran Layanan'
                elif row['jenis'] == 'pengeluaran':
                    jenis_transaksi = 'Pengeluaran'
                else:
                    jenis_transaksi = row['kategori'] or row['jenis']
                
                # Format status
                status_map = {
                    'pending': 'pending',
                    'lunas': 'selesai',
                    'gagal': 'ditolak'
                }
                status = status_map.get(row['status'], row['status'])
                
                transaksi_data.append({
                    'id': row['id'],
                    'kode': row['kode'],
                    'tipe': 'transaksi',
                    'jenis': jenis_transaksi,
                    'jumlah_karung': row['total_karung'] or 0,
                    'status': status,
                    'catatan': row['catatan'] or '',
                    'tanggal': row['tanggal'].strftime('%Y-%m-%d %H:%M:%S') if row['tanggal'] else None,
                    'jumlah': float(row['jumlah']) if row['jumlah'] else 0,
                    'harga_per_karung': float(row['harga_per_karung']) if row['harga_per_karung'] else 0,
                    'metode_bayar': row['metode_bayar'],
                    'bukti_bayar': row['bukti_bayar'],
                    'petugas': {
                        'nama': row['nama_petugas'] or '',
                        'telp': ''
                    },
                    # Field helper
                    'hari': get_hari_indonesia(row['tanggal']),
                    'tanggal_singkat': format_tanggal_singkat(row['tanggal']),
                    'waktu': format_waktu(row['tanggal']),
                    'tanggal_lengkap': format_tanggal_lengkap(row['tanggal'])
                })
        
        # Gabungkan dan sort data
        all_data = laporan_data + transaksi_data
        all_data.sort(key=lambda x: x['tanggal'] if x['tanggal'] else '', reverse=True)
        
        # Pagination
        total = len(all_data)
        start = offset
        end = offset + limit
        paginated_data = all_data[start:end]
        
        conn.close()
        
        return jsonify({
            "success": True, 
            "data": paginated_data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            },
            "summary": {
                "laporan": len(laporan_data),
                "transaksi": len(transaksi_data),
                "total": total
            }
        }), 200
        
    except Exception as e:
        print("get_riwayat_user error:", e)
        return jsonify({"success": False, "message": "Server error: " + str(e)}), 500

# 2. GET BULAN TERSEDIA (untuk user)
@riwayat_bp.route('/user/bulan-tersedia', methods=['GET'])
@token_required
def get_bulan_tersedia_user(current_user):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get user's warga id
        cursor.execute("SELECT id FROM warga WHERE user_id = %s", (current_user['id'],))
        warga = cursor.fetchone()
        
        if not warga:
            return jsonify({"success": False, "message": "Data warga tidak ditemukan"}), 404
        
        id_warga = warga['id']
        
        # Get months from laporan
        sql_laporan = """
            SELECT 
                DATE_FORMAT(tanggal_laporan, '%%Y-%%m') as bulan_tahun,
                YEAR(tanggal_laporan) as tahun,
                MONTH(tanggal_laporan) as bulan,
                COUNT(*) as count
            FROM laporan
            WHERE id_warga = %s
            GROUP BY DATE_FORMAT(tanggal_laporan, '%%Y-%%m'), YEAR(tanggal_laporan), MONTH(tanggal_laporan)
        """
        
        cursor.execute(sql_laporan, (id_warga,))
        laporan_months = cursor.fetchall()
        
        # Get months from transaksi
        sql_transaksi = """
            SELECT 
                DATE_FORMAT(tanggal, '%%Y-%%m') as bulan_tahun,
                YEAR(tanggal) as tahun,
                MONTH(tanggal) as bulan,
                COUNT(*) as count
            FROM transaksi
            WHERE warga_id = %s
            GROUP BY DATE_FORMAT(tanggal, '%%Y-%%m'), YEAR(tanggal), MONTH(tanggal)
        """
        
        cursor.execute(sql_transaksi, (id_warga,))
        transaksi_months = cursor.fetchall()
        
        # Combine months
        month_dict = {}
        
        for item in laporan_months:
            bulan_tahun = item['bulan_tahun']
            if bulan_tahun not in month_dict:
                month_dict[bulan_tahun] = {
                    'bulan_tahun': bulan_tahun,
                    'tahun': item['tahun'],
                    'bulan': item['bulan'],
                    'count_laporan': item['count'],
                    'count_transaksi': 0
                }
            else:
                month_dict[bulan_tahun]['count_laporan'] = item['count']
        
        for item in transaksi_months:
            bulan_tahun = item['bulan_tahun']
            if bulan_tahun not in month_dict:
                month_dict[bulan_tahun] = {
                    'bulan_tahun': bulan_tahun,
                    'tahun': item['tahun'],
                    'bulan': item['bulan'],
                    'count_laporan': 0,
                    'count_transaksi': item['count']
                }
            else:
                month_dict[bulan_tahun]['count_transaksi'] = item['count']
        
        # Format data
        nama_bulan = [
            'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ]
        
        current_date = datetime.now()
        current_month = current_date.strftime('%Y-%m')
        
        formatted_data = []
        for bulan_tahun, data in month_dict.items():
            bulan_int = int(data['bulan'])
            total_count = data['count_laporan'] + data['count_transaksi']
            
            formatted_data.append({
                'bulan_tahun': data['bulan_tahun'],
                'tahun': data['tahun'],
                'bulan': str(data['bulan']).zfill(2),
                'nama_bulan': nama_bulan[bulan_int - 1],
                'label': f"{nama_bulan[bulan_int - 1]} {data['tahun']}",
                'count': total_count,
                'count_laporan': data['count_laporan'],
                'count_transaksi': data['count_transaksi'],
                'isCurrent': data['bulan_tahun'] == current_month
            })
        
        # Sort by date descending
        formatted_data.sort(key=lambda x: (x['tahun'], x['bulan']), reverse=True)
        
        # Jika tidak ada data, tambahkan bulan ini
        if not formatted_data:
            formatted_data.append({
                'bulan_tahun': current_month,
                'tahun': current_date.year,
                'bulan': str(current_date.month).zfill(2),
                'nama_bulan': nama_bulan[current_date.month - 1],
                'label': f"{nama_bulan[current_date.month - 1]} {current_date.year}",
                'count': 0,
                'count_laporan': 0,
                'count_transaksi': 0,
                'isCurrent': True
            })
        
        conn.close()
        
        return jsonify({
            "success": True, 
            "data": formatted_data
        }), 200
        
    except Exception as e:
        print("get_bulan_tersedia_user error:", e)
        # Fallback
        current_date = datetime.now()
        nama_bulan = [
            'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ]
        
        data = [{
            'bulan_tahun': current_date.strftime('%Y-%m'),
            'tahun': current_date.year,
            'bulan': str(current_date.month).zfill(2),
            'nama_bulan': nama_bulan[current_date.month - 1],
            'label': f"{nama_bulan[current_date.month - 1]} {current_date.year}",
            'count': 0,
            'count_laporan': 0,
            'count_transaksi': 0,
            'isCurrent': True
        }]
        
        return jsonify({
            "success": True,
            "data": data
        }), 200

# 3. GET STATISTIK RIWAYAT USER
@riwayat_bp.route('/user/stats', methods=['GET'])
@token_required
def get_stats_user(current_user):
    try:
        bulan = request.args.get('bulan')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get user's warga id
        cursor.execute("SELECT id FROM warga WHERE user_id = %s", (current_user['id'],))
        warga = cursor.fetchone()
        
        if not warga:
            return jsonify({"success": False, "message": "Data warga tidak ditemukan"}), 404
        
        id_warga = warga['id']
        
        # Base WHERE clause
        where_laporan = "WHERE id_warga = %s"
        where_transaksi = "WHERE warga_id = %s"
        params = [id_warga]
        params_transaksi = [id_warga]
        
        if bulan:
            where_laporan += " AND DATE_FORMAT(tanggal_laporan, '%%Y-%%m') = %s"
            params.append(bulan)
            where_transaksi += " AND DATE_FORMAT(tanggal, '%%Y-%%m') = %s"
            params_transaksi.append(bulan)
        
        # Stats for laporan
        sql_laporan = f"""
            SELECT 
                status,
                COUNT(*) as count,
                SUM(CASE 
                    WHEN estimasi_volume = 'sedikit' THEN 1
                    WHEN estimasi_volume = 'sedang' THEN 2
                    WHEN estimasi_volume = 'banyak' THEN 3
                    ELSE 1
                END) as total_karung
            FROM laporan 
            {where_laporan}
            GROUP BY status
        """
        cursor.execute(sql_laporan, params)
        laporan_stats = cursor.fetchall()
        
        # Stats for transaksi
        sql_transaksi = f"""
            SELECT 
                jenis,
                SUM(jumlah) as total_jumlah,
                SUM(total_karung) as total_karung,
                COUNT(*) as count
            FROM transaksi 
            {where_transaksi}
            GROUP BY jenis
        """
        cursor.execute(sql_transaksi, params_transaksi)
        transaksi_stats = cursor.fetchall()
        
        # Total laporan dan karung
        sql_total_laporan = f"SELECT COUNT(*) as total FROM laporan {where_laporan}"
        cursor.execute(sql_total_laporan, params)
        total_laporan = cursor.fetchone()['total']
        
        sql_total_karung = f"""
            SELECT SUM(CASE 
                WHEN estimasi_volume = 'sedikit' THEN 1
                WHEN estimasi_volume = 'sedang' THEN 2
                WHEN estimasi_volume = 'banyak' THEN 3
                ELSE 1
            END) as total_karung 
            FROM laporan 
            {where_laporan}
        """
        cursor.execute(sql_total_karung, params)
        total_karung_laporan = cursor.fetchone()['total_karung'] or 0
        
        # Total transaksi
        sql_total_transaksi = f"SELECT COUNT(*) as total FROM transaksi {where_transaksi}"
        cursor.execute(sql_total_transaksi, params_transaksi)
        total_transaksi = cursor.fetchone()['total']
        
        # Format status stats
        status_counts = {}
        for item in laporan_stats:
            status_counts[item['status']] = {
                'count': item['count'],
                'total_karung': item['total_karung'] or 0
            }
        
        # Format transaksi stats
        transaksi_counts = {}
        for item in transaksi_stats:
            transaksi_counts[item['jenis']] = {
                'count': item['count'],
                'total_jumlah': float(item['total_jumlah']) if item['total_jumlah'] else 0,
                'total_karung': item['total_karung'] or 0
            }
        
        conn.close()
        
        return jsonify({
            "success": True,
            "data": {
                "laporan": {
                    "total": total_laporan,
                    "menunggu": status_counts.get('menunggu', {'count': 0})['count'],
                    "diproses": status_counts.get('diproses', {'count': 0})['count'],
                    "totalKarung": total_karung_laporan,
                    "statusStats": status_counts
                },
                "transaksi": {
                    "total": total_transaksi,
                    "pemasukan": transaksi_counts.get('pemasukan', {'count': 0, 'total_jumlah': 0})['total_jumlah'],
                    "pengeluaran": transaksi_counts.get('pengeluaran', {'count': 0, 'total_jumlah': 0})['total_jumlah'],
                    "totalKarung": sum(item['total_karung'] for item in transaksi_stats if item['total_karung']),
                    "jenisStats": transaksi_counts
                }
            }
        }), 200
        
    except Exception as e:
        print("get_stats_user error:", e)
        return jsonify({
            "success": True,
            "data": {
                "laporan": {
                    "total": 0,
                    "menunggu": 0,
                    "diproses": 0,
                    "totalKarung": 0,
                    "statusStats": {}
                },
                "transaksi": {
                    "total": 0,
                    "pemasukan": 0,
                    "pengeluaran": 0,
                    "totalKarung": 0,
                    "jenisStats": {}
                }
            }
        }), 200

# 4. GET DETAIL LAPORAN
@riwayat_bp.route('/laporan/<int:id>', methods=['GET'])
@token_required
def get_laporan_detail(current_user, id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # PERBAIKAN: Hapus JOIN dengan petugas karena tidak ada id_petugas
        sql = """
            SELECT 
                l.*,
                w.nama_lengkap as nama_warga,
                w.alamat_lengkap as alamat_warga,
                w.no_telepon,
                w.rt as rt_warga,
                w.rw as rw_warga,
                w.user_id as warga_user_id
            FROM laporan l
            JOIN warga w ON l.id_warga = w.id
            WHERE l.id = %s
        """
        
        cursor.execute(sql, (id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({"success": False, "message": "Laporan tidak ditemukan"}), 404
        
        # Check permission
        if current_user['role'] == 'warga' and row['warga_user_id'] != current_user['id']:
            return jsonify({"success": False, "message": "Tidak memiliki akses"}), 403
        
        # Format estimasi volume ke jumlah karung
        estimasi_volume = row['estimasi_volume']
        jumlah_karung = 0
        if estimasi_volume == 'sedikit':
            jumlah_karung = 1
        elif estimasi_volume == 'sedang':
            jumlah_karung = 2
        elif estimasi_volume == 'banyak':
            jumlah_karung = 3
        
        # Format status
        status_map = {
            'menunggu': 'pending',
            'diproses': 'proses',
            'diverifikasi': 'verifikasi',
            'selesai': 'selesai',
            'dibatalkan': 'ditolak'
        }
        status = status_map.get(row['status'], row['status'])
        
        # Format data
        formatted_data = {
            'id': row['id'],
            'kode_laporan': row['kode_laporan'],
            'jenis_sampah': row['jenis_sampah'],
            'jenis_lainnya': row['jenis_lainnya'],
            'estimasi_volume': estimasi_volume,
            'jumlah_karung': jumlah_karung,
            'status': status,
            'catatan': row['keterangan'] or row['catatan_petugas'] or '',
            'tanggal_laporan': row['tanggal_laporan'].strftime('%Y-%m-%d %H:%M:%S') if row['tanggal_laporan'] else None,
            'tanggal_verifikasi': row['tanggal_verifikasi'].strftime('%Y-%m-%d %H:%M:%S') if row['tanggal_verifikasi'] else None,
            'tanggal_selesai': row['tanggal_selesai'].strftime('%Y-%m-%d %H:%M:%S') if row['tanggal_selesai'] else None,
            'waktu_pengambilan': row['waktu_pengambilan'],
            'alamat_detail': row['alamat_detail'],
            'rt': row['rt'],
            'rw': row['rw'],
            'nomor_hp': row['nomor_hp'],
            'nama_pemohon': row['nama_pemohon'],
            'foto_sampah': row['foto_sampah'],
            'warga': {
                'id': row['id_warga'],
                'nama': row['nama_warga'] or '',
                'alamat': row['alamat_warga'] or '',
                'no_telepon': row['no_telepon'] or '',
                'rt': row['rt_warga'],
                'rw': row['rw_warga']
            },
            'petugas': {
                'nama': 'Belum ditugaskan',
                'no_telp': '',
                'username': ''
            },
            # Field helper
            'hari': get_hari_indonesia(row['tanggal_laporan']),
            'tanggal_singkat': format_tanggal_singkat(row['tanggal_laporan']),
            'waktu': format_waktu(row['tanggal_laporan']),
            'tanggal_lengkap': format_tanggal_lengkap(row['tanggal_laporan'])
        }
        
        conn.close()
        
        return jsonify({
            "success": True, 
            "data": formatted_data
        }), 200
        
    except Exception as e:
        print("get_laporan_detail error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500

# 5. GET DETAIL TRANSAKSI
@riwayat_bp.route('/transaksi/<int:id>', methods=['GET'])
@token_required
def get_transaksi_detail(current_user, id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get transaksi detail
        sql = """
            SELECT 
                t.*,
                w.nama_lengkap as nama_warga,
                w.user_id as warga_user_id,
                p.nama_lengkap as nama_petugas,
                p.no_telepon as telp_petugas,
                l.kode_laporan
            FROM transaksi t
            LEFT JOIN warga w ON t.warga_id = w.id
            LEFT JOIN petugas p ON t.petugas_id = p.id
            LEFT JOIN laporan l ON t.laporan_id = l.id
            WHERE t.id = %s
        """
        
        cursor.execute(sql, (id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({"success": False, "message": "Transaksi tidak ditemukan"}), 404
        
        # Check permission
        if current_user['role'] == 'warga' and row['warga_user_id'] != current_user['id']:
            return jsonify({"success": False, "message": "Tidak memiliki akses"}), 403
        
        # Tentukan jenis transaksi
        if row['jenis'] == 'pemasukan' and row['kategori'] == 'Iuran Warga':
            jenis_transaksi = 'Iuran Bulanan'
        elif row['jenis'] == 'pemasukan':
            jenis_transaksi = 'Pembayaran Layanan'
        elif row['jenis'] == 'pengeluaran':
            jenis_transaksi = 'Pengeluaran'
        else:
            jenis_transaksi = row['kategori'] or row['jenis']
        
        # Format status
        status_map = {
            'pending': 'pending',
            'lunas': 'selesai',
            'gagal': 'ditolak'
        }
        status = status_map.get(row['status_bayar'], row['status_bayar'])
        
        # Format data
        formatted_data = {
            'id': row['id'],
            'kode_transaksi': row['kode_transaksi'],
            'kode_laporan': row['kode_laporan'],
            'jenis': row['jenis'],
            'kategori': row['kategori'],
            'jenis_transaksi': jenis_transaksi,
            'jumlah': float(row['jumlah']) if row['jumlah'] else 0,
            'harga_per_karung': float(row['harga_per_karung']) if row['harga_per_karung'] else 0,
            'total_karung': row['total_karung'] or 0,
            'status': status,
            'catatan': row['keterangan'] or '',
            'metode_bayar': row['metode_bayar'],
            'bukti_bayar': row['bukti_bayar'],
            'tanggal': row['tanggal'].strftime('%Y-%m-%d %H:%M:%S') if row['tanggal'] else None,
            'warga': {
                'id': row['warga_id'],
                'nama': row['nama_warga'] or ''
            },
            'petugas': {
                'id': row['petugas_id'],
                'nama': row['nama_petugas'] or '',
                'no_telp': row['telp_petugas'] or ''
            },
            # Field helper
            'hari': get_hari_indonesia(row['tanggal']),
            'tanggal_singkat': format_tanggal_singkat(row['tanggal']),
            'waktu': format_waktu(row['tanggal']),
            'tanggal_lengkap': format_tanggal_lengkap(row['tanggal'])
        }
        
        conn.close()
        
        return jsonify({
            "success": True, 
            "data": formatted_data
        }), 200
        
    except Exception as e:
        print("get_transaksi_detail error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500

# 6. BATALKAN LAPORAN
@riwayat_bp.route('/laporan/<int:id>/batal', methods=['PUT'])
@token_required
def batalkan_laporan(current_user, id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get laporan
        sql = "SELECT id_warga, w.user_id as warga_user_id FROM laporan l JOIN warga w ON l.id_warga = w.id WHERE l.id = %s"
        cursor.execute(sql, (id,))
        laporan = cursor.fetchone()
        
        if not laporan:
            return jsonify({"success": False, "message": "Laporan tidak ditemukan"}), 404
        
        # Check permission
        if current_user['role'] == 'warga' and laporan['warga_user_id'] != current_user['id']:
            return jsonify({"success": False, "message": "Tidak memiliki akses"}), 403
        
        # Update status
        update_sql = """
            UPDATE laporan 
            SET status = 'dibatalkan',
                catatan_petugas = CONCAT(COALESCE(catatan_petugas, ''), ' [Dibatalkan user]')
            WHERE id = %s
        """
        
        cursor.execute(update_sql, (id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True, 
            "message": "Laporan berhasil dibatalkan"
        }), 200
        
    except Exception as e:
        print("batalkan_laporan error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500

# 7. VERIFIKASI LAPORAN SELESAI (User konfirmasi)
@riwayat_bp.route('/laporan/<int:id>/selesai', methods=['PUT'])
@token_required
def verifikasi_laporan_selesai(current_user, id):
    try:
        data = request.json
        catatan = data.get('catatan', '')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get laporan
        sql = "SELECT id_warga, w.user_id as warga_user_id, status FROM laporan l JOIN warga w ON l.id_warga = w.id WHERE l.id = %s"
        cursor.execute(sql, (id,))
        laporan = cursor.fetchone()
        
        if not laporan:
            return jsonify({"success": False, "message": "Laporan tidak ditemukan"}), 404
        
        # Check permission
        if current_user['role'] == 'warga' and laporan['warga_user_id'] != current_user['id']:
            return jsonify({"success": False, "message": "Tidak memiliki akses"}), 403
        
        # Check if laporan can be marked as done
        if laporan['status'] not in ['diproses', 'diverifikasi']:
            return jsonify({"success": False, "message": "Laporan tidak dapat diselesaikan"}), 400
        
        # Update status to selesai
        update_sql = """
            UPDATE laporan 
            SET status = 'selesai',
                tanggal_selesai = NOW(),
                catatan_petugas = CONCAT(COALESCE(catatan_petugas, ''), ' [Diverifikasi user: ', %s, ']')
            WHERE id = %s
        """
        
        cursor.execute(update_sql, (catatan, id))
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True, 
            "message": "Laporan berhasil diverifikasi selesai"
        }), 200
        
    except Exception as e:
        print("verifikasi_laporan_selesai error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500