from flask import Flask
from flask_cors import CORS
from routes.warga import warga_bp
# nanti bisa import petugas_bp, jadwal_bp, laporan_bp juga
from config import DB_CONFIG
from routes.warga import warga_bp
from routes.auth import auth_bp
from routes.jadwal import jadwal_bp
from routes.laporan import laporan_bp
from routes.gaji import gaji_bp

app = Flask(__name__)
CORS(app)

# (Opsional) bisa simpan konfigurasi DB di app config juga
app.config['DB_CONFIG'] = DB_CONFIG

# Register blueprint
app.register_blueprint(warga_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(jadwal_bp)
app.register_blueprint(laporan_bp)
app.register_blueprint(gaji_bp)

@app.route('/')
def index():
    return "SPS App API is running!"

if __name__ == '__main__':
    app.run(debug=True)

