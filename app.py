from flask import Flask, jsonify, render_template
from database import init_db, save_scan, get_latest_devices, get_stats
from scanner import scan_local_network

app = Flask(__name__)
init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def status():
    return jsonify(get_stats())

@app.route("/api/devices")
def devices():
    return jsonify(get_latest_devices())

@app.route("/api/scan", methods=["POST"])
def scan():
    results, network = scan_local_network()
    save_scan(results)
    return jsonify({"network": network, "devices": results, "count": len(results)})

if __name__ == "__main__":
    # Acesso somente pelo próprio computador por padrão.
    app.run(host="127.0.0.1", port=5000, debug=False)
