# routes/log.py atau tambahkan di routes/transaksi.py
from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG
from datetime import datetime, timedelta

log_bp = Blueprint('log', __name__, url_prefix='/api/log')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

@log_bp.route('/aktivitas', methods=['GET'])
def get_aktivitas():
    """Get semua aktivitas transaksi"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Parameter filter
            jenis = request.args.get('jenis')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            kategori = request.args.get('kategori')
            petugas_id = request.args.get('petugas_id')
            
            # Base query - TANPA JOIN ke tabel laporan (karena tidak ada)
            sql = """
                SELECT 
                    t.*,
                    p.nama_lengkap as nama_petugas,
                    p.no_telepon as telepon_petugas,
                    w.nama_lengkap as nama_warga,
                    w.alamat_lengkap as alamat_warga,
                    DATE_FORMAT(t.tanggal, '%%Y-%%m-%%d %%H:%%i') as waktu
                FROM transaksi t
                LEFT JOIN petugas p ON t.petugas_id = p.id
                LEFT JOIN warga w ON t.warga_id = w.id
                WHERE 1=1
            """
            
            params = []
            
            # Apply filters
            if jenis:
                sql += " AND t.jenis = %s"
                params.append(jenis)
            
            if start_date:
                sql += " AND DATE(t.tanggal) >= %s"
                params.append(start_date)
            
            if end_date:
                sql += " AND DATE(t.tanggal) <= %s"
                params.append(end_date)
            
            if kategori:
                sql += " AND t.kategori = %s"
                params.append(kategori)
            
            if petugas_id:
                sql += " AND t.petugas_id = %s"
                params.append(petugas_id)
            
            # Order dan limit
            sql += " ORDER BY t.tanggal DESC LIMIT 100"
            
            print(f"🔍 SQL: {sql}")
            print(f"🔍 Params: {params}")
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Format hasil
            for row in rows:
                # Format jumlah dengan pemisah ribuan
                row['jumlah_formatted'] = f"Rp {float(row['jumlah']):,.0f}".replace(',', '.')
                
                # Warna berdasarkan jenis
                if row['jenis'] == 'pemasukan':
                    row['color'] = 'green'
                    row['icon'] = 'arrow_upward'
                elif row['jenis'] == 'pengeluaran':
                    row['color'] = 'red'
                    row['icon'] = 'arrow_downward'
                elif row['jenis'] == 'gaji':
                    row['color'] = 'orange'
                    row['icon'] = 'paid'
                elif row['jenis'] == 'topup':
                    row['color'] = 'blue'
                    row['icon'] = 'account_balance_wallet'
                else:
                    row['color'] = 'grey'
                    row['icon'] = 'receipt'
                
                # Status badge
                if row['status_bayar'] == 'lunas':
                    row['status_color'] = 'positive'
                elif row['status_bayar'] == 'pending':
                    row['status_color'] = 'warning'
                else:
                    row['status_color'] = 'negative'
                
                # Jika ada laporan_id, coba ambil dari tabel yang ada
                if row.get('laporan_id'):
                    # Coba ambil dari tabel jadwal atau lainnya
                    # Atau biarkan kosong jika tidak ada tabel laporan
                    pass
            
            return jsonify({
                "success": True,
                "data": rows,
                "message": f"Found {len(rows)} aktivitas"
            }), 200
            
    except Exception as e:
        print(f"❌ Error in get_aktivitas: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal mengambil data aktivitas",
            "error": str(e)
        }), 500
    finally:
        conn.close()

@log_bp.route('/summary', methods=['GET'])
def get_summary():
    """Get summary/statistik aktivitas"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            # Query untuk summary per jenis
            sql = """
                SELECT 
                    jenis,
                    COUNT(*) as total_transaksi,
                    SUM(jumlah) as total_jumlah
                FROM transaksi
                WHERE 1=1
            """
            
            params = []
            
            if start_date:
                sql += " AND DATE(tanggal) >= %s"
                params.append(start_date)
            
            if end_date:
                sql += " AND DATE(tanggal) <= %s"
                params.append(end_date)
            
            sql += " GROUP BY jenis ORDER BY total_jumlah DESC"
            
            cursor.execute(sql, params)
            summary_by_jenis = cursor.fetchall()
            
            # Total keseluruhan
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_aktivitas,
                    SUM(CASE WHEN jenis = 'pemasukan' THEN jumlah ELSE 0 END) as total_pemasukan,
                    SUM(CASE WHEN jenis = 'pengeluaran' OR jenis = 'gaji' THEN jumlah ELSE 0 END) as total_pengeluaran
                FROM transaksi
                WHERE 1=1
            """ + (" AND DATE(tanggal) >= %s" if start_date else "") +
            (" AND DATE(tanggal) <= %s" if end_date else ""), 
            params if params else ())
            
            totals = cursor.fetchone()
            
            # Top petugas
            cursor.execute("""
                SELECT 
                    p.nama_lengkap,
                    COUNT(t.id) as jumlah_transaksi,
                    SUM(t.jumlah) as total_transaksi
                FROM transaksi t
                LEFT JOIN petugas p ON t.petugas_id = p.id
                WHERE t.petugas_id IS NOT NULL
                GROUP BY t.petugas_id
                ORDER BY total_transaksi DESC
                LIMIT 5
            """)
            top_petugas = cursor.fetchall()
            
            return jsonify({
                "success": True,
                "data": {
                    "summary_by_jenis": summary_by_jenis,
                    "totals": totals,
                    "top_petugas": top_petugas
                }
            }), 200
            
    except Exception as e:
        print(f"Error in get_summary: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal mengambil summary"
        }), 500
    finally:
        conn.close()

@log_bp.route('/harian', methods=['GET'])
def get_aktivitas_harian():
    """Get aktivitas per hari untuk chart"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            days = int(request.args.get('days', 7))
            
            sql = """
                SELECT 
                    DATE(tanggal) as tanggal,
                    COUNT(*) as jumlah_transaksi,
                    SUM(CASE WHEN jenis = 'pemasukan' THEN jumlah ELSE 0 END) as pemasukan,
                    SUM(CASE WHEN jenis IN ('pengeluaran', 'gaji') THEN jumlah ELSE 0 END) as pengeluaran
                FROM transaksi
                WHERE tanggal >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                GROUP BY DATE(tanggal)
                ORDER BY tanggal DESC
            """
            
            cursor.execute(sql, (days,))
            rows = cursor.fetchall()
            
            # Format untuk chart
            labels = []
            pemasukan_data = []
            pengeluaran_data = []
            
            for row in rows:
                # Format tanggal jadi "20 Jan"
                date_obj = datetime.strptime(str(row['tanggal']), '%Y-%m-%d')
                labels.append(date_obj.strftime('%d %b'))
                pemasukan_data.append(float(row['pemasukan'] or 0))
                pengeluaran_data.append(float(row['pengeluaran'] or 0))
            
            # Reverse untuk urutan ascending
            labels.reverse()
            pemasukan_data.reverse()
            pengeluaran_data.reverse()
            
            return jsonify({
                "success": True,
                "data": {
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Pemasukan",
                            "data": pemasukan_data,
                            "borderColor": "#4CAF50",
                            "backgroundColor": "rgba(76, 175, 80, 0.1)"
                        },
                        {
                            "label": "Pengeluaran",
                            "data": pengeluaran_data,
                            "borderColor": "#F44336",
                            "backgroundColor": "rgba(244, 67, 54, 0.1)"
                        }
                    ]
                }
            }), 200
            
    except Exception as e:
        print(f"Error in get_aktivitas_harian: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal mengambil data harian"
        }), 500
    finally:
        conn.close()

# Optional: Export ke CSV/Excel
@log_bp.route('/export-csv', methods=['GET'])
def export_csv():
    """Simple CSV export for frontend download"""
    try:
        # Get parameters
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        jenis = request.args.get('jenis', '')
        kategori = request.args.get('kategori', '')
        
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Build query
        query = """
            SELECT 
                t.id,
                t.kode_transaksi,
                t.jenis,
                t.kategori,
                t.jumlah,
                t.harga_per_karung,
                t.total_karung,
                t.metode_bayar,
                t.status_bayar,
                t.keterangan,
                DATE(t.tanggal) as tanggal,
                TIME(t.tanggal) as jam,
                p.nama_lengkap as petugas,
                w.nama_lengkap as warga
            FROM transaksi t
            LEFT JOIN petugas p ON t.petugas_id = p.id
            LEFT JOIN warga w ON t.warga_id = w.id
            WHERE 1=1
        """
        
        params = []
        
        if start_date:
            query += " AND DATE(t.tanggal) >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(t.tanggal) <= %s"
            params.append(end_date)
        
        if jenis:
            query += " AND t.jenis = %s"
            params.append(jenis)
        
        if kategori:
            query += " AND t.kategori = %s"
            params.append(kategori)
        
        query += " ORDER BY t.tanggal DESC"
        
        cursor.execute(query, params)
        data = cursor.fetchall()
        
        if not data:
            from flask import jsonify
            return jsonify({
                "success": False,
                "message": "Tidak ada data untuk di-export"
            }), 404
        
        # Create CSV content
        import csv
        from io import StringIO
        from datetime import datetime
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write UTF-8 BOM for Excel
        output.write('\ufeff')
        
        # Write header
        writer.writerow([
            'NO',
            'TANGGAL',
            'JAM', 
            'KODE TRANSAKSI',
            'JENIS',
            'KATEGORI',
            'JUMLAH (Rp)',
            'HARGA/KARUNG (Rp)',
            'TOTAL KARUNG',
            'METODE BAYAR',
            'STATUS',
            'KETERANGAN',
            'PETUGAS',
            'WARGA'
        ])
        
        # Write data
        for i, row in enumerate(data, 1):
            writer.writerow([
                i,
                row.get('tanggal', ''),
                row.get('jam', ''),
                row.get('kode_transaksi', '') or '-',
                row.get('jenis', ''),
                row.get('kategori', '') or '-',
                f"{float(row.get('jumlah', 0)):,.0f}".replace(',', '.'),
                f"{float(row.get('harga_per_karung', 0)):,.0f}".replace(',', '.') if row.get('harga_per_karung') else '-',
                row.get('total_karung', '') or '-',
                row.get('metode_bayar', '') or '-',
                row.get('status_bayar', '') or '-',
                (row.get('keterangan', '') or '-')[:100],
                row.get('petugas', '') or '-',
                row.get('warga', '') or '-'
            ])
        
        # Get CSV string
        csv_string = output.getvalue()
        
        # Create filename dengan filter info
        today = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Tambahkan info filter di filename
        filename_parts = ['laporan_transaksi', today]
        
        if start_date:
            filename_parts.append(f'dari_{start_date}')
        if end_date:
            filename_parts.append(f'sampai_{end_date}')
        if jenis:
            filename_parts.append(jenis)
        
        filename = '_'.join(filename_parts) + '.csv'
        
        # Clean filename dari karakter aneh
        import re
        filename = re.sub(r'[^\w\-\.]', '_', filename)
        
        print(f"📁 Export filename: {filename}")
        
        # Return as file download
        from flask import make_response
        
        response = make_response(csv_string)
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        print(f"Export error: {e}")
        from flask import jsonify
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500
        
    finally:
        if 'conn' in locals() and conn:
            conn.close()