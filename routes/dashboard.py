# routes/dashboard.py
from flask import Blueprint, jsonify
import pymysql
from config import DB_CONFIG
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

@dashboard_bp.route('/summary', methods=['GET'])
def get_dashboard_summary():
    """Get dashboard summary statistics"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. TODAY'S STATS
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_transaksi_hari_ini,
                    SUM(CASE WHEN jenis = 'pemasukan' THEN jumlah ELSE 0 END) as pemasukan_hari_ini,
                    SUM(CASE WHEN jenis IN ('pengeluaran', 'gaji') THEN jumlah ELSE 0 END) as pengeluaran_hari_ini
                FROM transaksi 
                WHERE DATE(tanggal) = CURDATE()
            """)
            today_stats = cursor.fetchone()
            
            # 2. MONTHLY STATS
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_transaksi_bulan_ini,
                    SUM(CASE WHEN jenis = 'pemasukan' THEN jumlah ELSE 0 END) as pemasukan_bulan_ini,
                    SUM(CASE WHEN jenis IN ('pengeluaran', 'gaji') THEN jumlah ELSE 0 END) as pengeluaran_bulan_ini,
                    (SUM(CASE WHEN jenis = 'pemasukan' THEN jumlah ELSE 0 END) - 
                     SUM(CASE WHEN jenis IN ('pengeluaran', 'gaji') THEN jumlah ELSE 0 END)) as saldo_bulan_ini
                FROM transaksi 
                WHERE MONTH(tanggal) = MONTH(CURDATE()) 
                AND YEAR(tanggal) = YEAR(CURDATE())
            """)
            monthly_stats = cursor.fetchone()
            
            # 3. TOTAL STATS
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_transaksi_all,
                    SUM(CASE WHEN jenis = 'pemasukan' THEN jumlah ELSE 0 END) as total_pemasukan_all,
                    SUM(CASE WHEN jenis IN ('pengeluaran', 'gaji') THEN jumlah ELSE 0 END) as total_pengeluaran_all
                FROM transaksi
            """)
            total_stats = cursor.fetchone()
            
            # 4. PETUGAS STATS
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_petugas,
                    SUM(CASE WHEN status_kerja = 'aktif' THEN 1 ELSE 0 END) as petugas_aktif,
                    SUM(CASE WHEN status_kerja = 'cuti' THEN 1 ELSE 0 END) as petugas_cuti,
                    SUM(CASE WHEN status_kerja = 'resign' THEN 1 ELSE 0 END) as petugas_resign
                FROM petugas
            """)
            petugas_stats = cursor.fetchone()
            
            # 5. WARGA STATS
            cursor.execute("""
                SELECT COUNT(*) as total_warga FROM warga
            """)
            warga_stats = cursor.fetchone()
            
            # 6. TOP 5 PETUGAS
            cursor.execute("""
                SELECT 
                    p.nama_lengkap,
                    p.no_telepon,
                    COUNT(t.id) as jumlah_transaksi,
                    SUM(t.jumlah) as total_transaksi
                FROM petugas p
                LEFT JOIN transaksi t ON p.id = t.petugas_id
                WHERE p.status_kerja = 'aktif'
                GROUP BY p.id
                ORDER BY total_transaksi DESC
                LIMIT 5
            """)
            top_petugas = cursor.fetchall()
            
            # 7. RECENT TRANSACTIONS
            cursor.execute("""
                SELECT 
                    t.id,
                    t.kode_transaksi,
                    t.jenis,
                    t.kategori,
                    t.jumlah,
                    t.keterangan,
                    DATE_FORMAT(t.tanggal, '%H:%i') as waktu,
                    p.nama_lengkap as petugas
                FROM transaksi t
                LEFT JOIN petugas p ON t.petugas_id = p.id
                ORDER BY t.tanggal DESC
                LIMIT 8
            """)
            recent_transactions = cursor.fetchall()
            
            # 8. TRANSACTION BY TYPE (for chart)
            cursor.execute("""
                SELECT 
                    jenis,
                    COUNT(*) as count,
                    SUM(jumlah) as total
                FROM transaksi
                WHERE tanggal >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                GROUP BY jenis
                ORDER BY total DESC
            """)
            transaction_by_type = cursor.fetchall()
            
            # 9. DAILY REVENUE LAST 7 DAYS
            cursor.execute("""
                SELECT 
                    DATE(tanggal) as tanggal,
                    SUM(CASE WHEN jenis = 'pemasukan' THEN jumlah ELSE 0 END) as pemasukan,
                    SUM(CASE WHEN jenis IN ('pengeluaran', 'gaji') THEN jumlah ELSE 0 END) as pengeluaran
                FROM transaksi
                WHERE tanggal >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                GROUP BY DATE(tanggal)
                ORDER BY tanggal
            """)
            daily_revenue = cursor.fetchall()
            
            # Format daily revenue for chart
            chart_labels = []
            chart_pemasukan = []
            chart_pengeluaran = []
            
            for day in daily_revenue:
                date_obj = datetime.strptime(str(day['tanggal']), '%Y-%m-%d')
                chart_labels.append(date_obj.strftime('%a %d'))
                chart_pemasukan.append(float(day['pemasukan'] or 0))
                chart_pengeluaran.append(float(day['pengeluaran'] or 0))
            
            # 10. JADWAL HARI INI
            cursor.execute("""
                SELECT 
                    id,
                    wilayah,
                    DATE_FORMAT(tanggal, '%Y-%m-%d') as tanggal,
                    TIME_FORMAT(jam_mulai, '%H:%i') as jam_mulai,
                    TIME_FORMAT(jam_selesai, '%H:%i') as jam_selesai,
                    keterangan
                FROM jadwal
                WHERE DATE(tanggal) = CURDATE()
                AND (status = 'aktif' OR status IS NULL)
                ORDER BY jam_mulai ASC
                LIMIT 5
            """)
            today_schedule = cursor.fetchall()
            
            return jsonify({
                "success": True,
                "data": {
                    "today_stats": today_stats or {},
                    "monthly_stats": monthly_stats or {},
                    "total_stats": total_stats or {},
                    "petugas_stats": petugas_stats or {},
                    "warga_stats": warga_stats or {},
                    "top_petugas": top_petugas,
                    "recent_transactions": recent_transactions,
                    "transaction_by_type": transaction_by_type,
                    "chart_data": {
                        "labels": chart_labels,
                        "pemasukan": chart_pemasukan,
                        "pengeluaran": chart_pengeluaran
                    },
                    "today_schedule": today_schedule
                },
                "last_updated": datetime.now().isoformat()
            }), 200
            
    except Exception as e:
        print(f"❌ Error in get_dashboard_summary: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "Gagal mengambil data dashboard"
        }), 500
    finally:
        conn.close()

@dashboard_bp.route('/quick-stats', methods=['GET'])
def get_quick_stats():
    """Quick stats for dashboard cards"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # TODAY
            cursor.execute("""
                SELECT 
                    COUNT(*) as transaksi,
                    SUM(jumlah) as total
                FROM transaksi
                WHERE DATE(tanggal) = CURDATE()
            """)
            today = cursor.fetchone()
            
            # YESTERDAY
            cursor.execute("""
                SELECT 
                    COUNT(*) as transaksi,
                    SUM(jumlah) as total
                FROM transaksi
                WHERE DATE(tanggal) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
            """)
            yesterday = cursor.fetchone()
            
            # THIS WEEK
            cursor.execute("""
                SELECT 
                    COUNT(*) as transaksi,
                    SUM(jumlah) as total
                FROM transaksi
                WHERE YEARWEEK(tanggal, 1) = YEARWEEK(CURDATE(), 1)
            """)
            week = cursor.fetchone()
            
            # THIS MONTH
            cursor.execute("""
                SELECT 
                    COUNT(*) as transaksi,
                    SUM(jumlah) as total
                FROM transaksi
                WHERE MONTH(tanggal) = MONTH(CURDATE())
                AND YEAR(tanggal) = YEAR(CURDATE())
            """)
            month = cursor.fetchone()
            
            # ACTIVE PETUGAS
            cursor.execute("SELECT COUNT(*) as count FROM petugas WHERE status_kerja = 'aktif'")
            active_petugas = cursor.fetchone()
            
            # TODAY'S SCHEDULE COUNT
            cursor.execute("SELECT COUNT(*) as count FROM jadwal WHERE DATE(tanggal) = CURDATE()")
            today_schedule_count = cursor.fetchone()
            
            # PENDING TRANSACTIONS
            cursor.execute("SELECT COUNT(*) as count FROM transaksi WHERE status_bayar = 'pending'")
            pending_transactions = cursor.fetchone()
            
            return jsonify({
                "success": True,
                "data": {
                    "today": today or {"transaksi": 0, "total": 0},
                    "yesterday": yesterday or {"transaksi": 0, "total": 0},
                    "week": week or {"transaksi": 0, "total": 0},
                    "month": month or {"transaksi": 0, "total": 0},
                    "active_petugas": active_petugas or {"count": 0},
                    "today_schedule_count": today_schedule_count or {"count": 0},
                    "pending_transactions": pending_transactions or {"count": 0}
                }
            }), 200
            
    except Exception as e:
        print(f"Error in get_quick_stats: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()