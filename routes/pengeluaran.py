from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG
from datetime import datetime

pengeluaran_bp = Blueprint('pengeluaran', __name__, url_prefix='/api/pengeluaran')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

"""
ini bagian penegluaran : yang biaya operasioanl sama gaji 
"""
@pengeluaran_bp.route('/', methods=['GET'])
def get_all_pengeluaran():
    jenis = request.args.get('jenis')
    tanggal = request.args.get('tanggal') 

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # GANTI SQL untuk ambil tanggal dengan format YYYY-MM-DD saja
            sql = """
                SELECT id, kategori, keterangan,
                       jumlah,
                       DATE_FORMAT(tanggal, '%%Y-%%m-%%d') as tanggal  # ← PAKAI DATE_FORMAT
                FROM pengeluaran
                WHERE 1=1
            """
            params = []

            if jenis:
                sql += " AND kategori = %s"
                params.append(jenis)

            if tanggal:
                sql += " AND DATE(tanggal) = %s"
                params.append(tanggal)

            sql += " ORDER BY tanggal DESC, id DESC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

        # HAPUS bagian ini karena sudah diformat di SQL
        # for r in rows:
        #     if r.get("tanggal"):
        #         r["tanggal"] = r["tanggal"].strftime("%Y-%m-%d %H:%M:%S")

        return jsonify({"success": True, "data": rows}), 200
    except Exception as e:
        print("get_all_pengeluaran error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()


@pengeluaran_bp.route('/<int:pengeluaran_id>', methods=['GET'])
def get_pengeluaran_by_id(pengeluaran_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Sama, pakai DATE_FORMAT
            sql = """
                SELECT id, kategori, keterangan,
                       jumlah,
                       DATE_FORMAT(tanggal, '%%Y-%%m-%%d') as tanggal
                FROM pengeluaran
                WHERE id = %s
            """
            cursor.execute(sql, (pengeluaran_id,))
            row = cursor.fetchone()

        if not row:
            return jsonify({"success": False, "message": "Data pengeluaran tidak ditemukan"}), 404

        # HAPUS konversi tanggal manual
        # if row.get("tanggal"):
        #     row["tanggal"] = row["tanggal"].strftime("%Y-%m-%d %H:%M:%S")

        return jsonify({"success": True, "data": row}), 200
    except Exception as e:
        print("get_pengeluaran_by_id error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

@pengeluaran_bp.route('/', methods=['POST'])
def create_pengeluaran():
    data = request.json or {}

    kategori = data.get('kategori')
    keterangan = data.get('keterangan')
    jumlah = data.get('jumlah')
    tanggal_str = data.get('tanggal') 

    if not kategori or not keterangan:
        return jsonify({"success": False, "message": "kategori dan keterangan wajib diisi"}), 400
    if jumlah is None:
        return jsonify({"success": False, "message": "jumlah wajib diisi"}), 400

    allowed_jenis = ['operasional', 'gaji', 'lainnya']
    if kategori not in allowed_jenis:
        return jsonify({
            "success": False,
            "message": "kategori harus salah satu dari: operasional, gaji, atau lainnya"
        }), 400

    tanggal_val = None
    if tanggal_str:
        try:
            # Format YYYY-MM-DD (sama seperti pemasukan)
            tanggal_val = datetime.strptime(tanggal_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({
                "success": False,
                "message": "Format tanggal harus 'YYYY-MM-DD'"
            }), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            if tanggal_val:
                sql = """
                    INSERT INTO pengeluaran
                        (kategori, keterangan, jumlah, tanggal)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    kategori,
                    keterangan,
                    jumlah,
                    tanggal_val
                ))
            else:
                sql = """
                    INSERT INTO pengeluaran
                        (kategori, keterangan, jumlah)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (
                    kategori,
                    keterangan,
                    jumlah
                ))

            conn.commit()
            new_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "message": "Data pengeluaran berhasil dicatat",
            "pengeluaran_id": new_id
        }), 201

    except Exception as e:
        print("create_pengeluaran error:", e)
        conn.rollback()
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

# Jangan lupa tambahkan PUT dan DELETE seperti sebelumnya
        
@pengeluaran_bp.route('/<int:id>', methods=['PUT'])
def update_pengeluaran(id):
    data = request.json or {}
    
    tanggal = data.get('tanggal')
    jumlah = data.get('jumlah')
    kategori = data.get('kategori')
    keterangan = data.get('keterangan')
    
    if not all([tanggal, jumlah, kategori, keterangan]):
        return jsonify({"success": False, "message": "Semua field wajib diisi"}), 400
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Cek apakah data ada
            cursor.execute("SELECT id FROM pengeluaran WHERE id = %s", (id,))
            if not cursor.fetchone():
                return jsonify({"success": False, "message": "Data tidak ditemukan"}), 404
            
            sql = """
                UPDATE pengeluaran 
                SET tanggal = %s, jumlah = %s, kategori = %s, keterangan = %s
                WHERE id = %s
            """
            cursor.execute(sql, (tanggal, jumlah, kategori, keterangan, id))
            conn.commit()
            
        return jsonify({
            "success": True,
            "message": "Pengeluaran berhasil diperbarui"
        }), 200
    except Exception as e:
        conn.rollback()
        print("update_pengeluaran error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

@pengeluaran_bp.route('/<int:id>', methods=['DELETE'])
def delete_pengeluaran(id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Cek apakah data ada
            cursor.execute("SELECT id FROM pengeluaran WHERE id = %s", (id,))
            if not cursor.fetchone():
                return jsonify({"success": False, "message": "Data tidak ditemukan"}), 404
            
            cursor.execute("DELETE FROM pengeluaran WHERE id = %s", (id,))
            conn.commit()
            
        return jsonify({
            "success": True,
            "message": "Pengeluaran berhasil dihapus"
        }), 200
    except Exception as e:
        conn.rollback()
        print("delete_pengeluaran error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()