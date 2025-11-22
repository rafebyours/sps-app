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
            sql = """
                SELECT id, jenis_pengeluaran, nama_pengeluaran,
                       jumlah_pengeluaran, tanggal
                FROM pengeluaran
                WHERE 1=1
            """
            params = []

            if jenis:
                sql += " AND jenis_pengeluaran = %s"
                params.append(jenis)

            if tanggal:
                sql += " AND DATE(tanggal) = %s"
                params.append(tanggal)

            sql += " ORDER BY tanggal DESC, id DESC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

        for r in rows:
            if r.get("tanggal"):
                r["tanggal"] = r["tanggal"].strftime("%Y-%m-%d %H:%M:%S")

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
            sql = """
                SELECT id, jenis_pengeluaran, nama_pengeluaran,
                       jumlah_pengeluaran, tanggal
                FROM pengeluaran
                WHERE id = %s
            """
            cursor.execute(sql, (pengeluaran_id,))
            row = cursor.fetchone()

        if not row:
            return jsonify({"success": False, "message": "Data pengeluaran tidak ditemukan"}), 404

        if row.get("tanggal"):
            row["tanggal"] = row["tanggal"].strftime("%Y-%m-%d %H:%M:%S")

        return jsonify({"success": True, "data": row}), 200
    except Exception as e:
        print("get_pengeluaran_by_id error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

@pengeluaran_bp.route('/', methods=['POST'])
def create_pengeluaran():
    data = request.json or {}

    jenis_pengeluaran = data.get('jenis_pengeluaran')
    nama_pengeluaran = data.get('nama_pengeluaran')
    jumlah_pengeluaran = data.get('jumlah_pengeluaran')
    tanggal_str = data.get('tanggal') 

    if not jenis_pengeluaran or not nama_pengeluaran:
        return jsonify({"success": False, "message": "jenis_pengeluaran dan nama_pengeluaran wajib diisi"}), 400
    if jumlah_pengeluaran is None:
        return jsonify({"success": False, "message": "jumlah_pengeluaran wajib diisi"}), 400

    allowed_jenis = ['operasional', 'gaji', 'lainnya']
    if jenis_pengeluaran not in allowed_jenis:
        return jsonify({
            "success": False,
            "message": "jenis_pengeluaran harus salah satu dari: operasional, gaji, atau lainnya"
        }), 400

    tanggal_val = None
    if tanggal_str:
        try:
            tanggal_val = datetime.strptime(tanggal_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return jsonify({
                "success": False,
                "message": "Format tanggal harus 'YYYY-MM-DD HH:MM:SS'"
            }), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            if tanggal_val:
                sql = """
                    INSERT INTO pengeluaran
                        (jenis_pengeluaran, nama_pengeluaran, jumlah_pengeluaran, tanggal)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    jenis_pengeluaran,
                    nama_pengeluaran,
                    jumlah_pengeluaran,
                    tanggal_val
                ))
            else:
                sql = """
                    INSERT INTO pengeluaran
                        (jenis_pengeluaran, nama_pengeluaran, jumlah_pengeluaran)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (
                    jenis_pengeluaran,
                    nama_pengeluaran,
                    jumlah_pengeluaran
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
