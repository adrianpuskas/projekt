#!/usr/bin/env python3
"""
local_server.py - iHome dashboard - kompaktnejšie energie na mobile
"""
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import threading
import sqlite3
import os

app = Flask(__name__)

KEY_METRICS = {
    "V76": ("Výkon PV", "fas fa-solar-panel"),
    "V70": ("SOC batérie", "fas fa-battery-full"),
    "V65": ("Spotreba domu", "fas fa-home"),
    "V15": ("Sieť +/-", "fas fa-exchange-alt"),
    "V4": ("Vonku", "fas fa-thermometer-half"),
    "V9": ("Teplota TÚV", "fas fa-tint"),
    "V7": ("Bojler", "fas fa-burn"),
}

VPINS = {
    # PV1
    "V72": ("PV1 prúd do batérie", "Fotovoltaika", "A", "fas fa-bolt"),
    "V73": ("PV1 napätie", "Fotovoltaika", "V", "fas fa-plug"),
    "V76": ("PV1 výkon", "Fotovoltaika", "W", "fas fa-solar-panel"),
    # PV2
    "V25": ("PV2 prúd do batérie", "Fotovoltaika", "A", "fas fa-bolt"),
    "V26": ("PV2 napätie", "Fotovoltaika", "V", "fas fa-plug"),
    "V27": ("PV2 výkon", "Fotovoltaika", "W", "fas fa-solar-panel"),
    # Batéria
    "V68": ("Napätie batérie", "Batéria", "V", "fas fa-battery-half"),
    "V69": ("Prúd batérie", "Batéria", "A", "fas fa-tachometer-alt"),
    "V70": ("SOC batérie", "Batéria", "%", "fas fa-battery-full"),
    "V74": ("Napätie batérie (SCC)", "Batéria", "V", "fas fa-battery-half"),
    "V75": ("Výkon batérie", "Batéria", "W", "fas fa-car-battery"),
    # Inverter / Domácnosť
    "V60": ("Sieťové napätie", "Sieť", "V", "fas fa-plug-circle-bolt"),
    "V61": ("Sieťová frekvencia", "Sieť", "Hz", "fas fa-wave-square"),
    "V62": ("Výstupné napätie", "Inverter", "V", "fas fa-bolt"),
    "V63": ("Výstupná frekvencia", "Inverter", "Hz", "fas fa-wave-square"),
    "V64": ("Príkon domácnosti", "Domácnosť", "VA", "fas fa-home"),
    "V65": ("Spotreba domácnosti", "Domácnosť", "W", "fas fa-home"),
    "V66": ("Zaťaženie invertera", "Inverter", "%", "fas fa-tachometer-alt"),
    "V67": ("BUS DC napätie", "Inverter", "V", "fas fa-bolt"),
    "V71": ("Teplota meniča", "Inverter", "°C", "fas fa-thermometer-half"),
    # Grid
    "V15": ("Výkon zo/do siete", "Sieť", "W", "fas fa-exchange-alt"),
    "V12": ("Celková spotreba energie (3F)", "Sieť", "kWh", "fas fa-bolt"),
    # Ovládanie
    "V1": ("Režim meniča", "Ovládanie", "", "fas fa-cog"),
    "V2": ("Čítať dáta z meniča", "Ovládanie", "", "fas fa-download"),
    "V3": ("Zapísať nastavenia", "Ovládanie", "", "fas fa-upload"),
    "V7": ("Výkon bojlera", "Ovládanie", "%", "fas fa-burn"),
    "V8": ("Automatika ohrevu", "Ovládanie", "", "fas fa-robot"),
    "V110": ("Reset skriptu", "Ovládanie", "", "fas fa-redo"),
    "V0": ("Zápis posúvača", "Ovládanie", "", "fas fa-sliders-h"),
    # Senzory
    "V4": ("Vonkajšia teplota", "Senzory", "°C", "fas fa-thermometer-half"),
    "indoor_temp": ("Teplota vnútri (DHT21)", "Senzory", "°C", "fas fa-thermometer-half"),
    "indoor_humidity": ("Vlhkosť vnútri (DHT21)", "Senzory", "%", "fas fa-tint"),
    "V9": ("Teplota TÚV", "Senzory", "°C", "fas fa-tint"),
    # BMS
    "V21": ("Nabíjanie BMS", "BMS", "", "fas fa-plug"),
    "V22": ("Vybíjanie BMS", "BMS", "", "fas fa-bolt"),
    # Ostatné
    "V13": ("Výpis BMS", "BMS", "", "fas fa-microchip"),
    "V99": ("Indikátor zápisu", "Ostatné", "", "fas fa-save"),
    "V101": ("Výroba/spotreba reťazec", "Ostatné", "", "fas fa-chart-line"),
}

local_data = {}
data_lock = threading.Lock()
DB_PATH = "solar_data.db"

def _store_value(key: str, value):
    with data_lock:
        local_data[key] = {"value": value, "ts": datetime.utcnow().isoformat()}

def _get_snapshot():
    with data_lock:
        return {k: v["value"] for k, v in local_data.items()}

def get_history_and_energy(minutes=1440):
    if not os.path.exists(DB_PATH):
        return {"timestamps": [], "pv": [], "soc": [], "load": [], "grid": [], "energy": {"pv": 0, "load": 0, "charge": 0, "discharge": 0}}
   
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
   
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=minutes)
   
    c.execute("""
        SELECT timestamp, pv_input_power, pv2_input_power, battery_capacity,
               ac_output_power, battery_power
        FROM solar_data
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    """, (start_time, end_time))
   
    rows = c.fetchall()
    conn.close()
   
    if not rows:
        return {"timestamps": [], "pv": [], "soc": [], "load": [], "grid": [], "energy": {"pv": 0, "load": 0, "charge": 0, "discharge": 0}}
   
    if minutes <= 720:
        timestamps = [r[0][11:16] for r in rows]
    else:
        timestamps = [r[0][5:16] for r in rows]
   
    pv = [round((float(r[1] or 0) + float(r[2] or 0))) for r in rows]
    soc = [float(r[3] or 0) for r in rows]
    load = [float(r[4] or 0) for r in rows]
    battery_powers = [float(r[5] or 0) for r in rows]
   
    interval_kwh = 5 / 3600000.0
    pv_kwh = sum(pv) * interval_kwh
    load_kwh = sum(load) * interval_kwh
    charge_kwh = sum(bp for bp in battery_powers if bp > 0) * interval_kwh
    discharge_kwh = sum(-bp for bp in battery_powers if bp < 0) * interval_kwh
   
    step = max(1, len(rows) // 150)
   
    return {
        "timestamps": timestamps[::step],
        "pv": pv[::step],
        "soc": soc[::step],
        "load": load[::step],
        "grid": battery_powers[::step],
        "energy": {
            "pv": round(pv_kwh, 3),
            "load": round(load_kwh, 3),
            "charge": round(charge_kwh, 3),
            "discharge": round(discharge_kwh, 3),
        }
    }

@app.route('/history/today', methods=['GET'])
def history_today():
    now = datetime.now()
    start_time = datetime(now.year, now.month, now.day, 0, 0, 0)
    end_time = now
    minutes_diff = int((end_time - start_time).total_seconds() / 60)
    return jsonify(get_history_and_energy(minutes_diff))

@app.route('/history/custom', methods=['GET'])
def history_custom():
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    if not start_str or not end_str:
        return jsonify({"error": "missing dates"}), 400
    try:
        start_time = datetime.strptime(start_str, "%Y-%m-%d")
        end_time = datetime.strptime(end_str, "%Y-%m-%d") + timedelta(days=1)
        minutes_diff = int((end_time - start_time).total_seconds() / 60)
        return jsonify(get_history_and_energy(minutes_diff))
    except:
        return jsonify({"error": "invalid format"}), 400

@app.route('/write', methods=['POST'])
def write_pin():
    data = request.get_json(silent=True) or {}
    key = data.get("key") or data.get("pin")  # ← podpora pre "key" z ESP01
    value = data.get("value")
    if not key:
        return jsonify({"status": "error", "message": "no key/pin"}), 400

    # Ak je to klasický V-pin (napr. z invertera), spracuj ho ako predtým
    if str(key).startswith("V") or str(key).startswith("v"):
        key = str(key).upper()
        if not key.startswith("V"):
            key = "V" + key
    # Ak je to nový názov ako "indoor_temp", nechaj ho tak

    _store_value(key, value)
    return jsonify({"status": "ok", "key": key, "value": value})

@app.route('/data', methods=['GET'])
def get_data():
    return jsonify(_get_snapshot())

@app.route('/vpin_info', methods=['GET'])
def vpin_info():
    return jsonify(VPINS)

@app.route('/history/<int:minutes>', methods=['GET'])
def history_endpoint(minutes):
    valid = {30:30, 60:60, 180:180, 360:360, 720:720, 1440:1440, 10080:10080, 43200:43200}
    minutes = valid.get(minutes, 1440)
    return jsonify(get_history_and_energy(minutes))

HTML_TEMPLATE = r"""
<!doctype html>
<html lang="sk">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>iHome - Domáca automatizácia</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root { --bg: #121212; --text: #e0e0e0; --card: #1e1e1e; --primary: #0dcaf0; }
    [data-bs-theme="light"] { --bg: #f8f9fa; --text: #212529; --card: #ffffff; --primary: #0d6efd; }
    body { background: var(--bg); color: var(--text); min-height: 100vh; }
    .navbar { background: #1f1f1f !important; }
    [data-bs-theme="light"] .navbar { background: #343a40 !important; }
    .card { background: var(--card); border: none; border-radius: 16px; box-shadow: 0 8px 25px rgba(0,0,0,0.3); }
    .key-value { font-size: 2.8rem; font-weight: bold; color: var(--primary); }
    .chart-container {
      background: var(--card);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
      height: 500px;
    }
    .energy-card {
      background: var(--card);
      border-radius: 12px;
      padding: 10px;
      text-align: center;
      font-size: 0.9rem;
    }
    .energy-card strong {
      font-size: 1rem;
      display: block;
      margin-bottom: 5px;
    }
    .energy-card .key-value {
      font-size: 1.8rem !important;
    }
    .info-bar { background: rgba(30,30,30,0.8); padding: 10px 15px; border-radius: 12px; font-size: 0.95rem; }
    .bms-terminal {
      background: #000;
      color: #0f0;
      padding: 20px;
      border-radius: 12px;
      font-family: monospace;
      font-size: 1.1rem;
      line-height: 1.5;
      white-space: pre-wrap;
      height: 700px;
      overflow-y: auto;
      border: 2px solid #0f0;
      box-shadow: 0 0 10px rgba(0, 255, 0, 0.3);
    }
    .detail-group {
      border: 2px solid var(--primary);
      border-radius: 16px;
      padding: 12px;
      margin-bottom: 25px;
      background: rgba(30,30,30,0.6);
    }
    .detail-group h4 {
      color: var(--primary);
      border-bottom: 1px solid var(--primary);
      padding-bottom: 8px;
      margin-bottom: 12px;
      text-align: center;
      font-size: 1.2rem;
    }
    .detail-card {
      padding: 6px 4px !important;
      margin-bottom: 6px;
    }
    .detail-card i {
      font-size: 1.5rem !important;
    }
    .detail-card .text-muted {
      font-size: 0.75rem;
    }
    .detail-card .key-value {
      font-size: 1.4rem !important;
      line-height: 1.2;
    }
    .section { display: none; }
    .section.active { display: block; }
  </style>
</head>
<body>
  <nav class="navbar navbar-expand-lg navbar-dark mb-3 shadow">
    <div class="container-fluid">
      <a class="navbar-brand" href="#" onclick="showSection('home')"><strong>iHome</strong></a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav me-auto">
          <li class="nav-item"><a class="nav-link active" onclick="showSection('home')">Home</a></li>
          <li class="nav-item"><a class="nav-link" onclick="showSection('detail')">Detail</a></li>
          <li class="nav-item"><a class="nav-link" onclick="showSection('grafy')">Grafy</a></li>
          <li class="nav-item"><a class="nav-link" onclick="showSection('bms')">BMS</a></li>
          <li class="nav-item"><a class="nav-link" onclick="showSection('control')">Ovládanie</a></li>
        </ul>
        <button id="theme-toggle" class="btn btn-outline-light"><i class="fas fa-moon"></i></button>
      </div>
    </div>
  </nav>
  <div class="container mb-4">
    <div class="info-bar text-center d-flex justify-content-center flex-wrap gap-4">
      <!-- NOVÉ: Vnútorná teplota a vlhkosť ako prvé -->
      <span><i class="fas fa-home me-2"></i> Vnútri: <strong id="indoor-temp-value">-</strong>°C</span>
      <span><i class="fas fa-tint me-2"></i> Vlhkosť: <strong id="indoor-hum-value">-</strong>%</span>
      <!-- Pôvodné -->
      <span><i class="fas fa-cog me-2"></i> Režim: <strong id="mode-value">-</strong></span>
      <span><i class="fas fa-thermometer-half me-2"></i> Menič FVE: <strong id="temp-value">-</strong>°C</span>
    </div>
  </div>
  <div class="container">
    <!-- zvyšok HTML je úplne rovnaký ako v tvojom origináli -->
    <div id="home" class="section active">
      <h2 class="text-center mb-4">Hlavný prehľad</h2>
      <div class="row" id="home-cards"></div>
    </div>
    <div id="detail" class="section">
      <h2 class="text-center mb-4">Detailné hodnoty</h2>
      <div class="row" id="detail-content"></div>
    </div>
    <div id="grafy" class="section">
      <h2 class="text-center mb-4">Grafy a energie</h2>
      <div class="btn-group mb-4 flex-wrap" role="group" id="time-buttons">
        <button class="btn btn-primary active" onclick="loadToday()">Dnes</button>
        <button class="btn btn-primary" onclick="loadMinutes(30)">30 min</button>
        <button class="btn btn-primary" onclick="loadMinutes(60)">1h</button>
        <button class="btn btn-primary" onclick="loadMinutes(180)">3h</button>
        <button class="btn btn-primary" onclick="loadMinutes(360)">6h</button>
        <button class="btn btn-primary" onclick="loadMinutes(720)">12h</button>
        <button class="btn btn-primary" onclick="loadMinutes(1440)">24h</button>
        <button class="btn btn-primary" onclick="loadMinutes(10080)">7 dní</button>
        <button class="btn btn-primary" onclick="loadMinutes(43200)">30 dní</button>
      </div>
      <div class="mb-4" id="custom-range" style="display:none;">
        <div class="row g-3 align-items-end">
          <div class="col-md-5"><label>Od:</label><input type="date" id="date-from" class="form-control"></div>
          <div class="col-md-5"><label>Do:</label><input type="date" id="date-to" class="form-control"></div>
          <div class="col-md-2"><button class="btn btn-success w-100" onclick="loadCustom()">Zobraziť</button></div>
        </div>
      </div>
      <button class="btn btn-outline-info mb-4" id="toggle-custom">Vlastný rozsah</button>
      <div id="energy-summary" class="row mb-4 g-2">
        <div class="col-6">
          <div class="energy-card text-warning">
            <strong>Výroba PV</strong>
            <span class="key-value" id="energy-pv">0</span> kWh
          </div>
        </div>
        <div class="col-6">
          <div class="energy-card text-info">
            <strong>Spotreba domu</strong>
            <span class="key-value" id="energy-load">0</span> kWh
          </div>
        </div>
        <div class="col-6">
          <div class="energy-card text-success">
            <strong>Nabíjanie batérie</strong>
            <span class="key-value" id="energy-charge">0</span> kWh
          </div>
        </div>
        <div class="col-6">
          <div class="energy-card text-danger">
            <strong>Vybíjanie batérie</strong>
            <span class="key-value" id="energy-discharge">0</span> kWh
          </div>
        </div>
      </div>
      <div class="row">
        <div class="col-12">
          <div class="chart-container">
            <canvas id="chartPower"></canvas>
          </div>
        </div>
        <div class="col-12">
          <div class="chart-container">
            <canvas id="chartSOC"></canvas>
          </div>
        </div>
      </div>
    </div>
    <div id="bms" class="section">
      <h2 class="text-center mb-4">BMS - JKBMS</h2>
      <div class="row justify-content-center">
        <div class="col-lg-11">
          <pre id="bms-terminal" class="bms-terminal">Načítavam BMS dáta...</pre>
        </div>
      </div>
      <div class="row justify-content-center mt-4">
        <div class="col-md-8">
          <button class="btn btn-success btn-lg w-100 mb-3" onclick="sendCmd('V21',0)">Nabíjanie ZAP</button>
          <button class="btn btn-danger btn-lg w-100 mb-3" onclick="sendCmd('V21',1)">Nabíjanie VYP</button>
          <button class="btn btn-success btn-lg w-100 mb-3" onclick="sendCmd('V22',0)">Vybíjanie ZAP</button>
          <button class="btn btn-danger btn-lg w-100 mb-3" onclick="sendCmd('V22',1)">Vybíjanie VYP</button>
        </div>
      </div>
    </div>
    <div id="control" class="section">
      <h2 class="text-center mb-4">Ovládanie systému</h2>
      <div class="row justify-content-center">
        <div class="col-md-6">
          <button class="btn btn-success btn-lg w-100 mb-3" onclick="sendCmd('V2',1)">Čítať dáta z meniča</button>
          <button class="btn btn-warning btn-lg w-100 mb-3" onclick="sendCmd('V3',1)">Zapísať nastavenia</button>
          <button class="btn btn-info btn-lg w-100 mb-3" onclick="sendCmd('V110',1)">Reset skriptu</button>
          <button class="btn btn-danger btn-lg w-100 mb-3" onclick="sendCmd('V7',100)">Bojler 100%</button>
          <button class="btn btn-secondary btn-lg w-100 mb-3" onclick="sendCmd('V7',0)">Bojler VYP</button>
        </div>
      </div>
    </div>
  </div>
  <footer class="text-center py-3 mt-5">
    <small id="status">Načítavam...</small>
  </footer>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    const REFRESH = 3000;
    let data = {}, info = {};
    let charts = {};
    const keyMetrics = {{ key_metrics | tojson }};
    const themeToggle = document.getElementById('theme-toggle');
    const currentTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-bs-theme', currentTheme);
    themeToggle.innerHTML = currentTheme === 'dark' ? '<i class="fas fa-moon"></i>' : '<i class="fas fa-sun"></i>';
    themeToggle.addEventListener('click', () => {
      const newTheme = document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-bs-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      themeToggle.innerHTML = newTheme === 'dark' ? '<i class="fas fa-moon"></i>' : '<i class="fas fa-sun"></i>';
    });
    function showSection(id) {
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
      document.getElementById(id).classList.add('active');
      document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
      document.querySelector(`.nav-link[onclick="showSection('${id}')"]`).classList.add('active');
      if (id === 'grafy') loadToday();
    }
    document.getElementById('toggle-custom').addEventListener('click', () => {
      const el = document.getElementById('custom-range');
      el.style.display = el.style.display === 'none' ? 'block' : 'none';
    });
    function updateInfoBar() {
      // NOVÉ: správne čítanie indoor_temp a indoor_humidity
      const temp = data['indoor_temp'];
      const hum = data['indoor_humidity'];
      document.getElementById('indoor-temp-value').textContent = temp !== undefined ? Number(temp).toFixed(1) : '-';
      document.getElementById('indoor-hum-value').textContent = hum !== undefined ? Math.round(hum) : '-';

      // Pôvodné
      document.getElementById('mode-value').textContent = data['V1'] || '-';
      document.getElementById('auto-value').textContent = data['V8'] == 1 ? 'ÁNO' : 'NIE';
      document.getElementById('boiler-value').textContent = data['V7'] > 0 ? data['V7'] + '%' : 'VYP';
      document.getElementById('temp-value').textContent = data['V71'] || '-';
    }
    function renderBMS() {
      let rawText = data['V13'] || 'Žiadne dáta z BMS';
      rawText = rawText.replace(/\\\\n/g, '\n').replace(/\\n/g, '\n').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
      rawText = rawText.trim();
      if (rawText === '') rawText = 'Žiadne aktuálne dáta z BMS';
      document.getElementById('bms-terminal').textContent = rawText;
    }
    function createCard(pin, label, value, unit, icon) {
      let color = "var(--primary)";
      if (pin === "V70") color = value > 50 ? "#28a745" : value > 20 ? "#ffc107" : "#dc3545";
      if (pin === "V15") color = value > 50 ? "#dc3545" : value < -50 ? "#28a745" : "#adb5bd";
      if (pin === "V7") color = value > 0 ? "#dc3545" : "#6c757d";
      let displayValue = pin === "V7" ? (value > 0 ? value + "%" : "Vypnutý") : value;
      return `
        <div class="col-lg-3 col-md-4 col-sm-6 mb-2">
          <div class="card detail-card text-center">
            <i class="${icon} fa-1x mb-1" style="color:${color}"></i>
            <div class="text-muted small">${label}</div>
            <div class="key-value" style="color:${color}; font-size:1.4rem;">${displayValue}${unit ? ' ' + unit : ''}</div>
          </div>
        </div>`;
    }
    function renderHome() {
      const c = document.getElementById('home-cards');
      c.innerHTML = '';
      Object.keys(keyMetrics).forEach(pin => {
        if (data[pin] !== undefined) {
          const meta = info[pin] || ["", "", ""];
          c.innerHTML += createCard(pin, keyMetrics[pin][0], data[pin], meta[2], keyMetrics[pin][1]);
        }
      });
      updateInfoBar();
    }
    function renderDetail() {
      const c = document.getElementById('detail-content');
      c.innerHTML = '';
      const groups = {
        "Fotovoltaika PV1": ["V76", "V73", "V72"],
        "Fotovoltaika PV2": ["V27", "V26", "V25"],
        "Batéria": ["V75", "V68", "V69", "V70", "V74"],
        "Inverter / Domácnosť": ["V65", "V64", "V66", "V62", "V63", "V60", "V61", "V67", "V71"]
      };
      Object.keys(groups).forEach(groupName => {
        const pins = groups[groupName];
        const hasData = pins.some(pin => data[pin] !== undefined);
        if (!hasData) return;
        let groupHTML = `<div class="col-12 mb-4">
          <div class="detail-group">
            <h4>${groupName}</h4>
            <div class="row justify-content-center">`;
        pins.forEach(pin => {
          if (data[pin] !== undefined) {
            const meta = info[pin] || [pin, "", ""];
            const displayValue = pin === "V7" ? (data[pin] > 0 ? data[pin] + "%" : "Vypnutý") : data[pin];
            groupHTML += createCard(pin, meta[0], displayValue, meta[2], meta[3] || "fas fa-circle");
          }
        });
        groupHTML += `</div></div></div>`;
        c.innerHTML += groupHTML;
      });
    }
    function renderEnergy(energy) {
      document.getElementById('energy-pv').textContent = energy.pv;
      document.getElementById('energy-load').textContent = energy.load;
      document.getElementById('energy-charge').textContent = energy.charge;
      document.getElementById('energy-discharge').textContent = energy.discharge;
    }
    async function updateCharts(h) {
      const ctxPower = document.getElementById('chartPower').getContext('2d');
      if (charts.power) charts.power.destroy();
      charts.power = new Chart(ctxPower, {
        type: 'line',
        data: {
          labels: h.timestamps,
          datasets: [
            {
              label: 'Výkon PV (W)',
              data: h.pv,
              borderColor: '#ffc107',
              backgroundColor: '#ffc10730',
              tension: 0.3,
              fill: true
            },
            {
              label: 'Spotreba domu (W)',
              data: h.load,
              borderColor: '#0dcaf0',
              backgroundColor: '#0dcaf030',
              tension: 0.3,
              fill: true
            },
            {
              label: 'Batéria +/- (W)',
              data: h.grid,
              borderColor: '#dc3545',
              backgroundColor: '#dc354530',
              tension: 0.3,
              fill: true
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: { x: { ticks: { maxTicksLimit: 15 } } }
        }
      });
      const ctxSOC = document.getElementById('chartSOC').getContext('2d');
      if (charts.soc) charts.soc.destroy();
      charts.soc = new Chart(ctxSOC, {
        type: 'line',
        data: {
          labels: h.timestamps,
          datasets: [{
            label: 'SOC batérie (%)',
            data: h.soc,
            borderColor: '#28a745',
            backgroundColor: '#28a74530',
            tension: 0.3,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: { x: { ticks: { maxTicksLimit: 15 } } }
        }
      });
    }
    async function loadToday() {
      document.querySelectorAll('#time-buttons .btn').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      const res = await fetch('/history/today');
      const h = await res.json();
      renderEnergy(h.energy);
      updateCharts(h);
    }
    async function loadMinutes(m) {
      document.querySelectorAll('#time-buttons .btn').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      const res = await fetch(`/history/${m}`);
      const h = await res.json();
      renderEnergy(h.energy);
      updateCharts(h);
    }
    async function loadCustom() {
      const from = document.getElementById('date-from').value;
      const to = document.getElementById('date-to').value;
      if (!from || !to) { alert("Vyber oba dátumy"); return; }
      document.querySelectorAll('#time-buttons .btn').forEach(b => b.classList.remove('active'));
      const res = await fetch(`/history/custom?start=${from}&end=${to}`);
      const h = await res.json();
      renderEnergy(h.energy);
      updateCharts(h);
    }
    async function sendCmd(pin, value) {
      await fetch('/write', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({pin, value})});
    }
    async function load() {
      try {
        const [d, i] = await Promise.all([fetch('/data'), fetch('/vpin_info')]);
        data = await d.json();
        info = await i.json();
        renderHome();
        renderDetail();
        updateInfoBar();
        renderBMS();
        document.getElementById('status').textContent = `Aktualizované: ${new Date().toLocaleTimeString('sk-SK')}`;
      } catch (e) {
        console.error("Chyba:", e);
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
    print("iHome dashboard - kompaktnejšie energie na mobile beží na http://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)