from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG
from datetime import datetime, timedelta

gaji_bp = Blueprint('gaji', __name__, url_prefix='/api/gaji')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

def format_timedelta_to_time(td):
    """Convert timedelta to HH:MM string"""
    if not td:
        return ''
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"

@gaji_bp.route('/jadwal', methods=['GET'])
def get_all_jadwal():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # OPTION 1: Ambil data mentah, format di Python (lebih aman)
            sql = """
                SELECT 
                    id, 
                    tanggal,
                    jam_mulai,
                    jam_selesai,
                    wilayah, 
                    keterangan, 
                    COALESCE(status, 'aktif') as status
                FROM jadwal
                WHERE status = 'aktif' OR status IS NULL
                ORDER BY tanggal DESC, jam_mulai DESC
            """
            
            print("📋 Executing SQL:", sql)
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            print(f"📋 [DEBUG] Raw rows count: {len(rows)}")
            for row in rows:
                print(f"📋 Row data types - tanggal: {type(row['tanggal'])}, jam_mulai: {type(row['jam_mulai'])}")
            
            formatted_rows = []
            for row in rows:
                # Format tanggal
                tanggal_str = ''
                if row['tanggal']:
                    if isinstance(row['tanggal'], datetime):
                        tanggal_str = row['tanggal'].strftime('%Y-%m-%d')
                    elif hasattr(row['tanggal'], 'strftime'):
                        tanggal_str = row['tanggal'].strftime('%Y-%m-%d')
                    elif isinstance(row['tanggal'], str):
                        # Jika sudah string, coba parse
                        try:
                            dt = datetime.strptime(row['tanggal'], '%Y-%m-%d')
                            tanggal_str = dt.strftime('%Y-%m-%d')
                        except:
                            tanggal_str = row['tanggal']
                    else:
                        tanggal_str = str(row['tanggal'])
                
                # Format jam_mulai
                jam_mulai_str = ''
                if row['jam_mulai']:
                    if isinstance(row['jam_mulai'], timedelta):
                        jam_mulai_str = format_timedelta_to_time(row['jam_mulai'])
                    elif isinstance(row['jam_mulai'], datetime):
                        jam_mulai_str = row['jam_mulai'].strftime('%H:%M')
                    elif hasattr(row['jam_mulai'], 'strftime'):
                        jam_mulai_str = row['jam_mulai'].strftime('%H:%M')
                    elif isinstance(row['jam_mulai'], str):
                        # Jika sudah string format "HH:MM:SS"
                        if ':' in row['jam_mulai']:
                            parts = row['jam_mulai'].split(':')
                            jam_mulai_str = f"{parts[0]}:{parts[1]}"
                        else:
                            jam_mulai_str = row['jam_mulai']
                    else:
                        jam_mulai_str = str(row['jam_mulai'])
                
                # Format jam_selesai
                jam_selesai_str = ''
                if row['jam_selesai']:
                    if isinstance(row['jam_selesai'], timedelta):
                        jam_selesai_str = format_timedelta_to_time(row['jam_selesai'])
                    elif isinstance(row['jam_selesai'], datetime):
                        jam_selesai_str = row['jam_selesai'].strftime('%H:%M')
                    elif hasattr(row['jam_selesai'], 'strftime'):
                        jam_selesai_str = row['jam_selesai'].strftime('%H:%M')
                    elif isinstance(row['jam_selesai'], str):
                        if ':' in row['jam_selesai']:
                            parts = row['jam_selesai'].split(':')
                            jam_selesai_str = f"{parts[0]}:{parts[1]}"
                        else:
                            jam_selesai_str = row['jam_selesai']
                    else:
                        jam_selesai_str = str(row['jam_selesai'])
                
                formatted_row = {
                    'id': row['id'],
                    'tanggal': tanggal_str,
                    'jam_mulai': jam_mulai_str,
                    'jam_selesai': jam_selesai_str,
                    'wilayah': row['wilayah'],
                    'keterangan': row.get('keterangan', '') or '',
                    'status': row.get('status', 'aktif'),
                    'display_text': f"{tanggal_str} - {row['wilayah']} ({jam_mulai_str}-{jam_selesai_str})"
                }
                
                print(f"📋 Formatted row {row['id']}: {formatted_row}")
                formatted_rows.append(formatted_row)
            
            return jsonify({
                "success": True, 
                "data": formatted_rows,
                "message": f"Found {len(formatted_rows)} jadwal",
                "debug": {
                    "raw_count": len(rows),
                    "formatted_count": len(formatted_rows)
                }
            }), 200
            
    except Exception as e:
        print("❌ Error in get_all_jadwal:", str(e))
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": True, 
            "data": [],
            "message": "Error loading data",
            "error": str(e)
        }), 200
    finally:
        conn.close()

# OPTION 2: Jika ingin tetap menggunakan DATE_FORMAT di SQL, gunakan ini:
@gaji_bp.route('/jadwal2', methods=['GET'])
def get_all_jadwal_v2():
    """Versi dengan DATE_FORMAT di SQL (perbaikan escape %)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Perhatikan: %Y-%m-%d di Python menjadi %%Y-%%m-%%d
            sql = """
                SELECT 
                    id, 
                    DATE_FORMAT(tanggal, '%%Y-%%m-%%d') as tanggal,
                    TIME_FORMAT(jam_mulai, '%%H:%%i') as jam_mulai,
                    TIME_FORMAT(jam_selesai, '%%H:%%i') as jam_selesai,
                    wilayah, 
                    keterangan, 
                    COALESCE(status, 'aktif') as status
                FROM jadwal
                WHERE status = 'aktif' OR status IS NULL
                ORDER BY tanggal DESC, jam_mulai DESC
            """
            
            print("📋 Executing SQL (v2):", sql)
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            # Tambah display_text
            for row in rows:
                row['display_text'] = f"{row['tanggal']} - {row['wilayah']} ({row['jam_mulai']}-{row['jam_selesai']})"
                row['keterangan'] = row.get('keterangan', '') or ''
            
            return jsonify({
                "success": True, 
                "data": rows,
                "message": f"Found {len(rows)} jadwal"
            }), 200
            
    except Exception as e:
        print("❌ Error in get_all_jadwal_v2:", str(e))
        return jsonify({
            "success": False, 
            "message": "Server error",
            "error": str(e)
        }), 500
    finally:
        conn.close()
        
# Lanjutan dari file routes/gaji.py

@gaji_bp.route('/jadwal/<int:jadwal_id>/petugas', methods=['GET'])
def get_petugas_by_jadwal(jadwal_id):
    """Get petugas yang ditugaskan di jadwal tertentu"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Get detail jadwal
            cursor.execute("""
                SELECT id, tanggal, jam_mulai, jam_selesai, wilayah, keterangan, status
                FROM jadwal
                WHERE id = %s
            """, (jadwal_id,))
            jadwal = cursor.fetchone()
            
            if not jadwal:
                return jsonify({
                    "success": False,
                    "message": "Jadwal tidak ditemukan"
                }), 404
            
            # Format jadwal
            tanggal_str = ''
            if jadwal['tanggal']:
                if hasattr(jadwal['tanggal'], 'strftime'):
                    tanggal_str = jadwal['tanggal'].strftime('%Y-%m-%d')
                else:
                    tanggal_str = str(jadwal['tanggal'])
            
            jadwal_detail = {
                'id': jadwal['id'],
                'tanggal': tanggal_str,
                'jam_mulai': format_timedelta_to_time(jadwal['jam_mulai']) if jadwal['jam_mulai'] else '',
                'jam_selesai': format_timedelta_to_time(jadwal['jam_selesai']) if jadwal['jam_selesai'] else '',
                'wilayah': jadwal['wilayah'],
                'keterangan': jadwal.get('keterangan', '') or '',
                'status': jadwal.get('status', 'aktif')
            }
            
            # 2. Get petugas dari jadwal_petugas
            cursor.execute("""
                SELECT 
                    p.id,
                    p.nama_lengkap,
                    p.nik,
                    p.no_telepon,
                    p.alamat,
                    p.status_kerja,
                    p.gaji_per_karung,
                    jp.status_kehadiran
                FROM jadwal_petugas jp
                INNER JOIN petugas p ON jp.petugas_id = p.id
                WHERE jp.jadwal_id = %s 
                AND p.status_kerja = 'aktif'
                ORDER BY p.nama_lengkap ASC
            """, (jadwal_id,))
            petugas_data = cursor.fetchall()
            
            # Format petugas
            petugas_list = []
            for petugas in petugas_data:
                petugas_list.append({
                    'id': petugas['id'],
                    'nama_lengkap': petugas['nama_lengkap'],
                    'nik': petugas['nik'] or '',
                    'no_telepon': petugas['no_telepon'] or '',
                    'alamat': petugas['alamat'] or '',
                    'status_kerja': petugas['status_kerja'],
                    'gaji_per_karung': float(petugas['gaji_per_karung']) if petugas['gaji_per_karung'] else 0,
                    'status_kehadiran': petugas['status_kehadiran'] or 'hadir'
                })
            
            return jsonify({
                "success": True,
                "data": {
                    "jadwal": jadwal_detail,
                    "petugas": petugas_list
                },
                "message": f"Found {len(petugas_list)} petugas for this schedule"
            }), 200
            
    except Exception as e:
        print(f"Error in get_petugas_by_jadwal: {e}")
        return jsonify({
            "success": False,
            "message": "Server error",
            "error": str(e)
        }), 500
    finally:
        conn.close()

@gaji_bp.route('/simpan', methods=['POST'])
def simpan_gaji():
    """Simpan gaji - delete old data first, then insert new"""
    data = request.get_json()
    
    # Validasi sederhana
    if not data or 'jadwal_id' not in data:
        return jsonify({
            "success": False,
            "message": "Data tidak lengkap"
        }), 400
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            jadwal_id = data['jadwal_id']
            tanggal_bayar = data.get('tanggal_bayar', datetime.now().date().isoformat())
            
            # 1. HITUNG TOTAL GAJI
            total_gaji = 0
            items_to_save = []
            
            for item in data.get('items', []):
                if 'petugas_id' in item and 'gaji' in item:
                    try:
                        gaji_value = float(item['gaji'])
                        if gaji_value > 0:
                            total_gaji += gaji_value
                            items_to_save.append({
                                'petugas_id': item['petugas_id'],
                                'gaji': gaji_value,
                                'keterangan': item.get('keterangan', '')
                            })
                    except:
                        continue
            
            if total_gaji <= 0:
                return jsonify({
                    "success": False, 
                    "message": "Total gaji harus lebih dari 0"
                }), 400
            
            # 2. HAPUS DATA LAMA di riwayat_gaji
            cursor.execute("DELETE FROM riwayat_gaji WHERE jadwal_id = %s", (jadwal_id,))
            deleted_old = cursor.rowcount
            
            # 3. INSERT DATA BARU ke riwayat_gaji
            for item in items_to_save:
                cursor.execute("""
                    INSERT INTO riwayat_gaji 
                    (jadwal_id, petugas_id, tanggal_bayar, gaji, keterangan)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    jadwal_id,
                    item['petugas_id'],
                    tanggal_bayar,
                    item['gaji'],
                    item['keterangan']
                ))
            
            # 4. HANDLE PENGELUARAN
            reference_id = f"gaji_{jadwal_id}"
            
            # Cek apakah sudah ada
            cursor.execute("""
                SELECT id FROM pengeluaran 
                WHERE reference_id = %s
            """, (reference_id,))
            
            existing = cursor.fetchone()
            
            # Ambil info jadwal
            cursor.execute("SELECT wilayah FROM jadwal WHERE id = %s", (jadwal_id,))
            jadwal_info = cursor.fetchone()
            wilayah = jadwal_info['wilayah'] if jadwal_info else f"Jadwal {jadwal_id}"
            
            # Buat keterangan
            keterangan = data.get('keterangan_umum', 
                f"Gaji {len(items_to_save)} petugas - {wilayah}")
            
            if existing:
                # UPDATE yang sudah ada
                cursor.execute("""
                    UPDATE pengeluaran 
                    SET tanggal = %s, 
                        jumlah = %s, 
                        keterangan = %s
                    WHERE reference_id = %s
                """, (
                    tanggal_bayar,
                    total_gaji,
                    keterangan,
                    reference_id
                ))
                expense_action = "diperbarui"
                expense_id = existing['id']
            else:
                # INSERT baru
                cursor.execute("""
                    INSERT INTO pengeluaran 
                    (reference_id, tanggal, jumlah, kategori, keterangan)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    reference_id,
                    tanggal_bayar,
                    total_gaji,
                    "Gaji Petugas",
                    keterangan
                ))
                expense_action = "dicatat"
                expense_id = cursor.lastrowid
            
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": f"Gaji berhasil disimpan ({len(items_to_save)} petugas)",
                "data": {
                    "total_gaji": total_gaji,
                    "petugas_count": len(items_to_save),
                    "expense_id": expense_id,
                    "expense_action": expense_action,
                    "deleted_old_records": deleted_old
                }
            }), 200
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal menyimpan data",
            "error": str(e)
        }), 500
    finally:
        conn.close()

@gaji_bp.route('/riwayat', methods=['GET'])
def get_riwayat_gaji():
    """Get salary history"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    rg.*,
                    p.nama_lengkap,
                    p.nik,
                    p.no_telepon,
                    j.wilayah,
                    DATE(j.tanggal) as tanggal_jadwal
                FROM riwayat_gaji rg
                INNER JOIN petugas p ON rg.petugas_id = p.id
                LEFT JOIN jadwal j ON rg.jadwal_id = j.id
                ORDER BY rg.tanggal_bayar DESC, rg.created_at DESC
                LIMIT 50
            """)
            rows = cursor.fetchall()
            
            # Format hasil
            result = []
            for row in rows:
                tanggal_bayar = row['tanggal_bayar'].strftime('%Y-%m-%d') if row['tanggal_bayar'] else ''
                tanggal_jadwal = row['tanggal_jadwal'].strftime('%Y-%m-%d') if row['tanggal_jadwal'] else ''
                created_at = row['created_at'].strftime('%Y-%m-%d %H:%M') if row['created_at'] else ''
                
                result.append({
                    'id': row['id'],
                    'petugas_id': row['petugas_id'],
                    'jadwal_id': row['jadwal_id'],
                    'gaji': float(row['gaji']),
                    'tanggal_bayar': tanggal_bayar,
                    'keterangan': row['keterangan'] or '',
                    'nama_lengkap': row['nama_lengkap'],
                    'nik': row['nik'] or '',
                    'no_telepon': row['no_telepon'] or '',
                    'wilayah': row['wilayah'] or '',
                    'periode': tanggal_jadwal,
                    'created_at': created_at
                })
            
            return jsonify({
                "success": True,
                "data": result,
                "message": f"Found {len(result)} salary records"
            }), 200
            
    except Exception as e:
        print(f"Error in get_riwayat_gaji: {e}")
        return jsonify({
            "success": False,
            "message": "Gagal mengambil riwayat gaji"
        }), 500
    finally:
        conn.close()

@gaji_bp.route('/jadwal/<int:jadwal_id>/cek', methods=['GET'])
def cek_gaji_jadwal(jadwal_id):
    """Cek apakah sudah ada input gaji untuk jadwal ini"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    rg.petugas_id,
                    rg.gaji,
                    rg.keterangan,
                    p.nama_lengkap
                FROM riwayat_gaji rg
                INNER JOIN petugas p ON rg.petugas_id = p.id
                WHERE rg.jadwal_id = %s
            """, (jadwal_id,))
            rows = cursor.fetchall()
            
            # Konversi gaji ke float
            for row in rows:
                row['gaji'] = float(row['gaji']) if row['gaji'] else 0
            
            return jsonify({
                "success": True,
                "data": rows,
                "sudah_ada": len(rows) > 0,
                "message": f"Found {len(rows)} existing salary records"
            }), 200
            
    except Exception as e:
        print(f"Error in cek_gaji_jadwal: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
    finally:
        conn.close()
        
@gaji_bp.route('/hapus-pengeluaran/<int:jadwal_id>', methods=['DELETE'])
def hapus_pengeluaran_gaji(jadwal_id):
    """Hapus pengeluaran gaji untuk jadwal tertentu"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            reference_id = f"GJI_{jadwal_id}"
            
            cursor.execute("DELETE FROM pengeluaran WHERE reference_id = %s", (reference_id,))
            deleted_count = cursor.rowcount
            
            # Optional: hapus juga dari riwayat_gaji
            # cursor.execute("DELETE FROM riwayat_gaji WHERE jadwal_id = %s", (jadwal_id,))
            
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": f"Berhasil menghapus {deleted_count} record pengeluaran"
            }), 200
            
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()