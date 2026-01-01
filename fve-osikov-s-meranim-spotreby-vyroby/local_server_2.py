#!/usr/bin/env python3
"""
local_server.py - Lokálny dashboard s jednoduchým prepínaním sekcií (bez problematických Bootstrap tabov)
"""

from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
import threading

app = Flask(__name__)

# ============================
# Mapovanie virtuálnych pinov
# ============================
VPINS = {
    # PV1
    "V72": ("PV1 prúd do batérie", "Fotovoltaika", "A"),
    "V73": ("PV1 napätie", "Fotovoltaika", "V"),
    "V76": ("PV1 výkon", "Fotovoltaika", "W"),

    # PV2
    "V25": ("PV2 prúd do batérie", "Fotovoltaika", "A"),
    "V26": ("PV2 napätie", "Fotovoltaika", "V"),
    "V27": ("PV2 výkon", "Fotovoltaika", "W"),

    # Batéria
    "V68": ("Napätie batérie", "Fotovoltaika", "V"),
    "V69": ("Prúd batérie", "Fotovoltaika", "A"),
    "V70": ("Kapacita batérie (SOC)", "Fotovoltaika", "%"),
    "V74": ("Napätie batérie (SCC)", "Fotovoltaika", "V"),
    "V75": ("Výkon batérie", "Fotovoltaika", "W"),

    # Inverter / Domácnosť
    "V60": ("Sieťové napätie", "Fotovoltaika", "V"),
    "V61": ("Sieťová frekvencia", "Fotovoltaika", "Hz"),
    "V62": ("Výstupné napätie", "Fotovoltaika", "V"),
    "V65": ("Výstupný výkon (domácnosť)", "Fotovoltaika", "W"),
    "V66": ("Zaťaženie invertera", "Fotovoltaika", "%"),
    "V71": ("Teplota invertera", "Fotovoltaika", "°C"),

    # Grid
    "V15": ("Celkový výkon zo/do siete", "Fotovoltaika", "W"),
    "V12": ("Celková spotreba energie (3F)", "Fotovoltaika", "kWh"),

    # Ovládanie
    "V1": ("Režim zariadenia", "Ovládanie", ""),
    "V2": ("Čítať dáta z invertera", "Ovládanie", ""),
    "V3": ("Zapísať nastavenia do invertera", "Ovládanie", ""),
    "V7": ("Výkon bojlera", "Ovládanie", "%"),
    "V8": ("Automatický ohrev", "Ovládanie", ""),
    "V110": ("Reset skriptu", "Ovládanie", ""),
    "V0": ("Tlačidlo zápis posúvača", "Ovládanie", ""),

    # Senzory
    "V4": ("Vonkajšia teplota", "Senzory", "°C"),
    "V9": ("Teplota TÚV", "Senzory", "°C"),

    # Ostatné
    "V13": ("BMS dáta", "Ostatné", ""),
    "V99": ("Indikátor zápisu", "Ostatné", ""),
    "V101": ("Reťazec výroba/spotreba", "Ostatné", ""),
}

# Kľúčové metriky pre Home
KEY_METRICS = {
    "V76": "Celkový výkon PV",
    "V70": "Kapacita batérie",
    "V15": "Výkon zo/do siete",
    "V65": "Spotreba domácnosti",
}

# ============================
# Úložisko dát
# ============================
local_data = {}
data_lock = threading.Lock()

def _store_value(pin: str, value, device: str = "main"):
    with data_lock:
        local_data[pin] = {"value": value, "ts": datetime.utcnow().isoformat(), "device": device}

def _get_snapshot():
    with data_lock:
        return {pin: info["value"] for pin, info in local_data.items()}

# ============================
# API
# ============================
@app.route('/write', methods=['POST'])
def write_pin():
    data = request.get_json(silent=True) or {}
    pin = data.get("pin")
    value = data.get("value")
    if pin is None:
        return jsonify({"status": "error", "message": "missing 'pin'"}), 400
    if isinstance(pin, int): pin = f"V{pin}"
    elif isinstance(pin, str) and not pin.upper().startswith("V"): pin = "V" + pin.upper()
    pin = pin.upper()
    _store_value(pin, value)
    return jsonify({"status": "ok", "pin": pin, "value": value})

@app.route('/data', methods=['GET'])
def get_data():
    return jsonify(_get_snapshot())

@app.route('/vpin_info', methods=['GET'])
def vpin_info():
    return jsonify(VPINS)

# ============================
# HTML Dashboard s jednoduchým JS prepínaním
# ============================
HTML_TEMPLATE = r"""
<!doctype html>
<html lang="sk">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lokálny Dashboard - Domáca Fotovoltaika</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background: #f4f6f9; }
    .navbar-brand { font-weight: bold; color: #0d6efd !important; }
    .nav-link { cursor: pointer; }
    .nav-link.active { font-weight: bold; }
    .section { display: none; }
    .section.active { display: block; }
    .key-card { text-align: center; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 1rem; }
    .key-value { font-size: 2rem; font-weight: bold; color: #0d6efd; }
    .key-label { font-size: 1rem; color: #555; margin-top: 8px; }
    .card { transition: transform 0.2s; }
    .card:hover { transform: translateY(-5px); }
    .btn-control { width: 100%; margin-bottom: 10px; }
  </style>
</head>
<body>
  <nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
    <div class="container-fluid">
      <a class="navbar-brand" href="#">? Domáca Fotovoltaika</a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav ms-auto">
          <li class="nav-item"><a class="nav-link active" onclick="showSection('home')">Home</a></li>
          <li class="nav-item"><a class="nav-link" onclick="showSection('fv')">Fotovoltaika</a></li>
          <li class="nav-item"><a class="nav-link" onclick="showSection('control')">Ovládanie</a></li>
          <li class="nav-item"><a class="nav-link" onclick="showSection('sensors')">Senzory</a></li>
          <li class="nav-item"><a class="nav-link" onclick="showSection('other')">Ostatné</a></li>
        </ul>
      </div>
    </div>
  </nav>

  <div class="container">
    <!-- HOME -->
    <div id="home" class="section active">
      <h2 class="text-center mb-4">Hlavný prehľad</h2>
      <div class="row" id="home-cards"></div>
    </div>

    <!-- FOTOVOLTAIKA -->
    <div id="fv" class="section">
      <h2 class="text-center mb-4">Detail fotovoltaiky (PV, batéria, inverter, grid)</h2>
      <div class="row" id="fv-content"></div>
    </div>

    <!-- OVLÁDANIE -->
    <div id="control" class="section">
      <h2 class="text-center mb-4">Ovládanie systému</h2>
      <div class="row justify-content-center">
        <div class="col-md-6">
          <button class="btn btn-success btn-lg btn-control" onclick="sendCmd('V2',1)">Čítať dáta z invertera</button>
          <button class="btn btn-warning btn-lg btn-control" onclick="sendCmd('V3',1)">Zapísať nastavenia</button>
          <button class="btn btn-info btn-lg btn-control" onclick="sendCmd('V110',1)">Reset skriptu</button>
          <button class="btn btn-primary btn-lg btn-control" onclick="sendCmd('V7',100)">Bojler 100%</button>
          <button class="btn btn-secondary btn-lg btn-control" onclick="sendCmd('V7',0)">Bojler vypnúť</button>
        </div>
      </div>
      <div class="row mt-4" id="control-values"></div>
    </div>

    <!-- SENZORY -->
    <div id="sensors" class="section">
      <h2 class="text-center mb-4">Senzory</h2>
      <div class="row" id="sensors-content"></div>
    </div>

    <!-- OSTATNÉ -->
    <div id="other" class="section">
      <h2 class="text-center mb-4">Ostatné údaje</h2>
      <div class="row" id="other-content"></div>
    </div>
  </div>

  <footer class="bg-light text-center py-3 mt-5">
    <small id="status">Načítavam dáta...</small>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    const REFRESH = 1000;
    let data = {};
    let info = {};
    const keyMetrics = {{ key_metrics | tojson }};

    function showSection(id) {
      document.querySelectorAll('.section').forEach(sec => sec.classList.remove('active'));
      document.getElementById(id).classList.add('active');
      document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
      document.querySelector(`.nav-link[onclick="showSection('${id}')"]`).classList.add('active');
    }

    function format(value, unit) {
      if (value === undefined || value === null) return "-";
      if (!isNaN(value)) {
        let n = Number(value);
        let digits = Math.abs(n) < 10 ? 2 : Math.abs(n) < 100 ? 1 : 0;
        return n.toLocaleString('sk-SK', {minimumFractionDigits: 0, maximumFractionDigits: digits}) + (unit ? " " + unit : "");
      }
      return value + (unit ? " " + unit : "");
    }

    function createHomeCard(pin, label, value, unit) {
      return `
        <div class="col-lg-3 col-md-4 col-sm-6 mb-4">
          <div class="card key-card bg-white">
            <div class="card-body">
              <div class="key-label">${label} <small class="text-muted">(${pin})</small></div>
              <div class="key-value">${format(value, unit)}</div>
            </div>
          </div>
        </div>`;
    }

    function createDetailCard(pin, name, value, unit) {
      return `
        <div class="col-md-4 col-sm-6 mb-4">
          <div class="card bg-white">
            <div class="card-body">
              <h6 class="card-title">${name} <small class="text-muted">(${pin})</small></h6>
              <p class="key-value mb-0">${format(value, unit)}</p>
            </div>
          </div>
        </div>`;
    }

    function renderHome() {
      const container = document.getElementById('home-cards');
      container.innerHTML = '';
      Object.keys(keyMetrics).forEach(pin => {
        if (data[pin] !== undefined) {
          const meta = info[pin] || ["", "", ""];
          container.innerHTML += createHomeCard(pin, keyMetrics[pin], data[pin], meta[2]);
        }
      });
    }

    function renderSection(containerId, sectionName) {
      const container = document.getElementById(containerId);
      container.innerHTML = '';
      const pins = Object.keys(data).filter(p => info[p] && info[p][1] === sectionName);
      if (pins.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">Žiadne dáta</p>';
        return;
      }
      pins.sort((a,b) => (info[a][0] || "").localeCompare(info[b][0] || ""));
      pins.forEach(pin => {
        const meta = info[pin];
        container.innerHTML += createDetailCard(pin, meta[0], data[pin], meta[2]);
      });
    }

    function renderAll() {
      renderHome();
      renderSection('fv-content', 'Fotovoltaika');
      renderSection('control-values', 'Ovládanie');
      renderSection('sensors-content', 'Senzory');
      renderSection('other-content', 'Ostatné');
    }

    async function sendCmd(pin, value) {
      try {
        await fetch('/write', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({pin, value})});
        alert(`Príkaz odoslaný: ${pin} = ${value}`);
      } catch (e) { alert("Chyba pri odoslaní"); }
    }

    async function load() {
      try {
        const [d, i] = await Promise.all([fetch('/data'), fetch('/vpin_info')]);
        data = await d.json();
        info = await i.json();
        renderAll();
        document.getElementById('status').textContent = `Aktualizované: ${new Date().toLocaleTimeString('sk-SK')}`;
      } catch (e) {
        document.getElementById('status').textContent = 'Chyba pri načítaní dát';
      }
    }

    load();
    setInterval(load, REFRESH);
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, key_metrics=KEY_METRICS)

if __name__ == "__main__":
    print("Dashboard beží na http://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)