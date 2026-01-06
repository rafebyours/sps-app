from flask import Flask
from flask_cors import CORS
from routes.warga import warga_bp
from config import DB_CONFIG
from routes.warga import warga_bp
from routes.auth import auth_bp
from routes.jadwal import jadwal_bp
from routes.laporan import laporan_bp
from routes.gaji import gaji_bp
from routes.riwayat import riwayat_bp
from routes.pemasukan import pemasukan_bp
from routes.pengeluaran import pengeluaran_bp
from routes.lokasi import lokasi_bp
from routes.petugas import petugas_bp
from routes.riwayat_admin import riwayat_admin_bp
from routes.keuangan import keuangan_bp
from routes.log import log_bp
from routes.dashboard import dashboard_bp
from routes.pengambilan import pengambilan_bp
from routes.transaksi import transaksi_bp

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "http://localhost:9000",
        "supports_credentials": True
    }
})


app.config['DB_CONFIG'] = DB_CONFIG

# Register blueprint
app.register_blueprint(warga_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(jadwal_bp)
app.register_blueprint(laporan_bp)
app.register_blueprint(gaji_bp)
app.register_blueprint(riwayat_bp)
app.register_blueprint(pemasukan_bp)
app.register_blueprint(pengeluaran_bp)
app.register_blueprint(lokasi_bp)
app.register_blueprint(petugas_bp)
app.register_blueprint(riwayat_admin_bp)
app.register_blueprint(keuangan_bp)
app.register_blueprint(log_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(pengambilan_bp)
app.register_blueprint(transaksi_bp)
@app.route('/')
def index():
    return "SPS App API is running!"

if __name__ == '__main__':
    app.run(debug=True)
