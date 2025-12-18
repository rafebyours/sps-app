from flask import Blueprint, request, jsonify
import pymysql
from config import DB_CONFIG

petugas_bp = Blueprint('petugas', __name__, url_prefix='/api/petugas')

def get_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)

def map_status_for_ui(db_status: str) -> str:
    # laporan_sampah.status: menunggu | dijemput | selesai
    if db_status == 'menunggu':
        return 'Belum diambil'
    # dijemput/selesai dianggap sudah diambil (sesuai UI kamu)
    return 'Sudah diambil'

@petugas_bp.route('/tugas', methods=['GET'])
def get_tugas_petugas():
    """
    Query params:
      - date: YYYY-MM-DD  (ambil berdasarkan DATE(laporan_sampah.jadwal_pengambilan))
      - petugas_id: int   (opsional; kalau ada, filter berdasarkan jadwal.wilayah di tanggal itu)
    """
    q_date = request.args.get('date')          # "2025-10-19"
    petugas_id = request.args.get('petugas_id')

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1) Ambil wilayah penugasan petugas (opsional)
            wilayah = None
            if petugas_id and q_date:
                cursor.execute("""
                    SELECT wilayah
                    FROM jadwal
                    WHERE id_petugas = %s AND tanggal = %s AND status = 'aktif'
                    ORDER BY id DESC
                    LIMIT 1
                """, (petugas_id, q_date))
                row = cursor.fetchone()
                wilayah = row["wilayah"] if row else None

            # 2) Ambil tugas dari laporan_sampah + warga
            # Gunakan alamat dari laporan_sampah kalau ada, fallback ke warga.alamat
            sql = """
                SELECT
                    ls.id AS id,
                    w.nama_warga AS name,
                    COALESCE(ls.alamat, w.alamat) AS address,
                    ls.status AS status_db,
                    ls.jadwal_pengambilan AS jadwal_pengambilan
                FROM laporan_sampah ls
                JOIN warga w ON w.id = ls.id_warga
                WHERE ls.jadwal_pengambilan IS NOT NULL
            """
            params = []

            if q_date:
                sql += " AND DATE(ls.jadwal_pengambilan) = %s"
                params.append(q_date)

            # Tampilkan yang relevan untuk “tugas pengambilan”
            sql += " AND ls.status IN ('menunggu','dijemput','selesai')"

            # 3) Filter wilayah kalau jadwal petugas bukan "Seluruh"
            # Catatan: di DB warga ada kolom `lokasi` (varchar)
            # Kita pakai lokasi dulu; kalau kosong, bisa fallback ke address LIKE.
            if wilayah and wilayah.lower() != 'seluruh':
                sql += " AND (w.lokasi = %s OR COALESCE(ls.alamat, w.alamat) LIKE %s)"
                params.extend([wilayah, f"%{wilayah}%"])

            sql += " ORDER BY ls.jadwal_pengambilan ASC, ls.id DESC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

        # Bentuk response sesuai kebutuhan frontend
        data = []
        for r in rows:
            data.append({
                "id": r["id"],
                "name": r["name"],
                "address": r["address"],
                "status": map_status_for_ui(r["status_db"]),
                # frontend kamu filter date, jadi kita kirim format YYYY-MM-DD
                "date": r["jadwal_pengambilan"].strftime("%Y-%m-%d") if r["jadwal_pengambilan"] else None,
                "jadwal_pengambilan": r["jadwal_pengambilan"].strftime("%Y-%m-%d %H:%M:%S") if r["jadwal_pengambilan"] else None,
                "status_db": r["status_db"],
            })

        return jsonify({"success": True, "data": data}), 200

    except Exception as e:
        print("get_tugas_petugas error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

@petugas_bp.route('/tugas/<int:laporan_id>/ambil', methods=['POST'])
def ambil_tugas(laporan_id):
    """
    Body:
      - petugas_id (wajib)
      - jumlah_karung (opsional; kalau belum tahu bisa null)
    """
    data = request.json or {}
    petugas_id = data.get("petugas_id")
    jumlah_karung = data.get("jumlah_karung")  # opsional

    if not petugas_id:
        return jsonify({"success": False, "message": "petugas_id wajib"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Ambil id_warga dari laporan
            cursor.execute("SELECT id_warga, status FROM laporan_sampah WHERE id = %s", (laporan_id,))
            laporan = cursor.fetchone()
            if not laporan:
                return jsonify({"success": False, "message": "Laporan tidak ditemukan"}), 404

            # Update status laporan jadi dijemput (kalau masih menunggu)
            cursor.execute("""
                UPDATE laporan_sampah
                SET status = 'dijemput'
                WHERE id = %s AND status = 'menunggu'
            """, (laporan_id,))

            # Catat riwayat
            cursor.execute("""
                INSERT INTO riwayat_aktivitas (id_warga, id_petugas, jumlah_karung, status)
                VALUES (%s, %s, %s, 'diambil')
            """, (laporan["id_warga"], petugas_id, jumlah_karung))

        conn.commit()
        return jsonify({"success": True, "message": "Status diperbarui menjadi dijemput"}), 200

    except Exception as e:
        conn.rollback()
        print("ambil_tugas error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

@petugas_bp.route('/rekap', methods=['GET'])
def rekap_pengambilan():
    q_date = request.args.get('date')  # YYYY-MM-DD
    petugas_id = request.args.get('petugas_id')  # opsional

    if not q_date:
        return jsonify({"success": False, "message": "date wajib (YYYY-MM-DD)"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Ambil wilayah (opsional) dari jadwal petugas untuk tanggal tsb
            wilayah = None
            if petugas_id:
                cursor.execute("""
                    SELECT wilayah
                    FROM jadwal
                    WHERE id_petugas = %s AND tanggal = %s AND status = 'aktif'
                    ORDER BY id DESC
                    LIMIT 1
                """, (petugas_id, q_date))
                row = cursor.fetchone()
                wilayah = row["wilayah"] if row else None

            # Filter wilayah: pakai warga.lokasi atau alamat LIKE
            wilayah_sql = ""
            wilayah_params = []
            if wilayah and wilayah.lower() != 'seluruh':
                wilayah_sql = " AND (w.lokasi = %s OR COALESCE(ls.alamat, w.alamat) LIKE %s) "
                wilayah_params = [wilayah, f"%{wilayah}%"]

            # 1) Detail transaksi
            cursor.execute(f"""
                SELECT
                    ls.id AS id_laporan,
                    w.nama_warga AS nama,
                    ls.jumlah_karung,
                    ls.jenis_pembayaran,
                    ls.status AS status_laporan,
                    COALESCE(p.jumlah_pembayaran, 0) AS jumlah_pembayaran,
                    COALESCE(p.kekurangan, 0) AS kekurangan
                FROM laporan_sampah ls
                JOIN warga w ON w.id = ls.id_warga
                LEFT JOIN pemasukan p ON p.id_laporan = ls.id
                WHERE ls.jadwal_pengambilan IS NOT NULL
                  AND DATE(ls.jadwal_pengambilan) = %s
                {wilayah_sql}
                ORDER BY ls.jadwal_pengambilan ASC, ls.id DESC
            """, [q_date] + wilayah_params)

            rows = cursor.fetchall()

            # 2) Ringkasan
            pemasukan_hari_ini = 0.0
            total_tunggak_rp = 0.0
            jumlah_pengambilan = len(rows)
            jumlah_tunggak_kasus = 0

            detail = []
            for r in rows:
                pemasukan_hari_ini += float(r["jumlah_pembayaran"] or 0)
                total_tunggak_rp += float(r["kekurangan"] or 0)
                if float(r["kekurangan"] or 0) > 0:
                    jumlah_tunggak_kasus += 1

                # mapping agar cocok UI kamu
                metode = r["jenis_pembayaran"]
                if metode == 'transfer':
                    metode_ui = 'Transfer bank'
                elif metode == 'saldo':
                    metode_ui = 'Saldo'
                else:
                    metode_ui = 'Cash'

                status_ui = 'Lunas' if float(r["kekurangan"] or 0) == 0 else 'Belum'

                detail.append({
                    "nama": r["nama"],
                    "jumlah_karung": r["jumlah_karung"],
                    "pembayaran": metode_ui,
                    "status": status_ui,
                    "id_laporan": r["id_laporan"],
                    "kekurangan": float(r["kekurangan"] or 0),
                    "jumlah_pembayaran": float(r["jumlah_pembayaran"] or 0),
                })

        return jsonify({
            "success": True,
            "data": {
                "tanggal": q_date,
                "pemasukan_hari_ini": pemasukan_hari_ini,
                "total_tunggak_rp": total_tunggak_rp,
                "total_tunggak_kasus": jumlah_tunggak_kasus,
                "pengambilan_sampah": jumlah_pengambilan,
                "detail": detail
            }
        }), 200

    except Exception as e:
        print("rekap_pengambilan error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

@petugas_bp.route('/by-user/<int:user_id>', methods=['GET'])
def get_petugas_by_user(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, user_id, nama_petugas, no_telp, alamat, status
                FROM petugas
                WHERE user_id = %s
                LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()

        if not row:
            return jsonify({"success": False, "message": "Petugas tidak ditemukan"}), 404

        return jsonify({"success": True, "data": row}), 200

    except Exception as e:
        print("get_petugas_by_user error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

def map_payment_ui(jenis: str) -> str:
    # laporan_sampah.jenis_pembayaran: cash | saldo | transfer
    if jenis == 'transfer':
        return 'Transfer bank'
    if jenis == 'saldo':
        return 'Saldo'
    return 'Cash'

@petugas_bp.route('/pendapatan', methods=['GET'])
def pendapatan_petugas():
    """
    GET /api/petugas/pendapatan?date=YYYY-MM-DD&petugas_id=1

    Return:
    {
      success: true,
      data: {
        tanggal,
        bonus,
        total_income,
        total_akhir,
        detail: [
          { id, name, bags, payment, amount, status, date }
        ]
      }
    }
    """

    q_date = request.args.get('date')          # wajib: YYYY-MM-DD
    petugas_id = request.args.get('petugas_id')  # wajib

    if not q_date:
        return jsonify({"success": False, "message": "date wajib (YYYY-MM-DD)"}), 400
    if not petugas_id:
        return jsonify({"success": False, "message": "petugas_id wajib"}), 400

    # Samakan dengan frontend kamu:
    KOMISI_PER_KARUNG = 5000   # jika komisi per karung berbeda, ubah di sini
    BONUS_HARIAN = 2500        # sesuai frontend (bonus = 2500)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Ambil aktivitas petugas hari itu dari riwayat_aktivitas
            # Sekalian ambil metode pembayaran dari laporan_sampah (laporan terakhir warga pada tanggal tsb)
            sql = """
                SELECT
                    ra.id AS id,
                    w.nama_warga AS name,
                    COALESCE(ra.jumlah_karung, 0) AS bags,
                    ra.status AS status_aktivitas,
                    ra.tanggal AS tanggal_aktivitas,
                    ls.jenis_pembayaran AS jenis_pembayaran
                FROM riwayat_aktivitas ra
                JOIN warga w ON w.id = ra.id_warga
                LEFT JOIN laporan_sampah ls
                    ON ls.id = (
                        SELECT ls2.id
                        FROM laporan_sampah ls2
                        WHERE ls2.id_warga = ra.id_warga
                          AND ls2.jadwal_pengambilan IS NOT NULL
                          AND DATE(ls2.jadwal_pengambilan) = %s
                        ORDER BY ls2.id DESC
                        LIMIT 1
                    )
                WHERE ra.id_petugas = %s
                  AND DATE(ra.tanggal) = %s
                  AND ra.status IN ('diambil','selesai')
                ORDER BY ra.tanggal DESC, ra.id DESC
            """
            cursor.execute(sql, (q_date, petugas_id, q_date))
            rows = cursor.fetchall()

        detail = []
        total_income = 0

        for r in rows:
            bags = int(r.get("bags") or 0)

            # Amount/komisi per task
            amount = bags * KOMISI_PER_KARUNG

            payment_ui = map_payment_ui(r.get("jenis_pembayaran"))

            # status untuk frontend (kalau mau dipakai)
            status_ui = 'Sudah diambil'

            detail.append({
                "id": int(r["id"]),
                "name": r.get("name") or "-",
                "bags": bags,
                "payment": payment_ui,       # "Cash" / "Saldo" / "Transfer bank"
                "amount": amount,            # angka (frontend kamu pakai toLocaleString)
                "status": status_ui,
                "date": q_date               # YYYY-MM-DD (biar gampang filter)
            })

            total_income += amount

        data = {
            "tanggal": q_date,
            "bonus": BONUS_HARIAN,
            "total_income": total_income,
            "total_akhir": total_income + BONUS_HARIAN,
            "detail": detail
        }

        return jsonify({"success": True, "data": data}), 200

    except Exception as e:
        print("pendapatan_petugas error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()