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

app = Flask(__name__)
CORS(app)

app.config['DB_CONFIG'] = DB_CONFIG

# Register blueprint
app.register_blueprint(warga_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(jadwal_bp)
app.register_blueprint(laporan_bp)
app.register_blueprint(gaji_bp)
app.register_blueprint(riwayat_bp)
app.register_blueprint(pemasukan_bp)

@app.route('/')
def index():
    return "SPS App API is running!"

if __name__ == '__main__':
    app.run(debug=True)

