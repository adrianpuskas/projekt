#!/usr/bin/env python3
"""
local_server.py - iHome dashboard - nová štruktúra Domov / Fotovoltaika / Topenie
"""
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import threading
import sqlite3
import os

app = Flask(__name__)

KEY_METRICS = {
    "V76": ("Výkon PV", "fas fa-solar-panel"),
    "V70": ("Kapacita batérie", "fas fa-battery-full"),
    "V65": ("Spotreba domu", "fas fa-home"),
    "V15": ("Sieť +/-", "fas fa-exchange-alt"),
    "V4": ("Vonku", "fas fa-thermometer-half"),
    "V9": ("Teplota TÚV", "fas fa-tint"),
    "V7": ("Bojler", "fas fa-burn"),
}

VPINS = {
    "V72": ("PV1 prúd", "Fotovoltaika", "A", "fas fa-bolt"),
    "V73": ("PV1 napätie", "Fotovoltaika", "V", "fas fa-plug"),
    "V76": ("PV1 výkon", "Fotovoltaika", "W", "fas fa-solar-panel"),
    "V25": ("PV2 prúd", "Fotovoltaika", "A", "fas fa-bolt"),
    "V26": ("PV2 napätie", "Fotovoltaika", "V", "fas fa-plug"),
    "V27": ("PV2 výkon", "Fotovoltaika", "W", "fas fa-solar-panel"),
    "V68": ("Napätie batérie", "Batéria", "V", "fas fa-battery-half"),
    "V69": ("Prúd batérie", "Batéria", "A", "fas fa-tachometer-alt"),
    "V70": ("Kapacita batérie", "Batéria", "%", "fas fa-battery-full"),
    "V74": ("Napätie batérie (SCC)", "Batéria", "V", "fas fa-battery-half"),
    "V75": ("Výkon batérie", "Batéria", "W", "fas fa-car-battery"),
    "V60": ("Sieťové napätie", "Sieť", "V", "fas fa-plug-circle-bolt"),
    "V61": ("Sieťová frekvencia", "Sieť", "Hz", "fas fa-wave-square"),
    "V62": ("Výstupné napätie", "Inverter", "V", "fas fa-bolt"),
    "V63": ("Výstupná frekvencia", "Inverter", "Hz", "fas fa-wave-square"),
    "V64": ("Príkon domácnosti", "Domácnosť", "VA", "fas fa-home"),
    "V65": ("Spotreba domácnosti", "Domácnosť", "W", "fas fa-home"),
    "V66": ("Zaťaženie invertera", "Inverter", "%", "fas fa-tachometer-alt"),
    "V67": ("BUS DC napätie", "Inverter", "V", "fas fa-bolt"),
    "V71": ("Teplota meniča", "Inverter", "°C", "fas fa-thermometer-half"),
    "V15": ("Výkon zo/do siete", "Sieť", "W", "fas fa-exchange-alt"),
    "V12": ("Celková spotreba energie (3F)", "Sieť", "kWh", "fas fa-bolt"),
    "V1": ("Režim meniča", "Ovládanie", "", "fas fa-cog"),
    "V2": ("Čítať dáta z meniča", "Ovládanie", "", "fas fa-download"),
    "V3": ("Zapísať nastavenia", "Ovládanie", "", "fas fa-upload"),
    "V7": ("Výkon bojlera", "Ovládanie", "%", "fas fa-burn"),
    "V8": ("Automatika ohrevu", "Ovládanie", "", "fas fa-robot"),
    "V110": ("Reset skriptu", "Ovládanie", "", "fas fa-redo"),
    "V0": ("Zápis posúvača", "Ovládanie", "", "fas fa-sliders-h"),
    "V4": ("Vonkajšia teplota", "Senzory", "°C", "fas fa-thermometer-half"),
    "indoor_temp": ("Teplota vnútri", "Senzory", "°C", "fas fa-thermometer-half"),
    "indoor_humidity": ("Vlhkosť vnútri", "Senzory", "%", "fas fa-tint"),
    "V9": ("Teplota TÚV", "Senzory", "°C", "fas fa-tint"),
    "V21": ("Nabíjanie BMS", "BMS", "", "fas fa-plug"),
    "V22": ("Vybíjanie BMS", "BMS", "", "fas fa-bolt"),
    "V13": ("Výpis BMS", "BMS", "", "fas fa-microchip"),
    "V99": ("Indikátor zápisu", "Ostatné", "", "fas fa-save"),
    "V101": ("Výroba/spotreba reťazec", "Ostatné", "", "fas fa-chart-line"),
    "topenie_water_temp": ("Teplota vody", "Topenie", "°C", "fas fa-tint"),
    "topenie_boiler_temp": ("Teplota kotla", "Topenie", "°C", "fas fa-thermometer-full"),
    "topenie_smoke_temp": ("Teplota dymovodu", "Topenie", "°C", "fas fa-cloud"),
    "topenie_manual_mode": ("Manuálny režim", "Topenie", "", "fas fa-hand-paper"),
    "topenie_pump": ("Čerpadlo", "Topenie", "", "fas fa-fan"),
    "topenie_valve_tuv": ("Ventil TUV", "Topenie", "", "fas fa-valve"),
    "topenie_valve_radiator": ("Ventil radiatorov", "Topenie", "", "fas fa-valve"),
    "topenie_pump_min": ("Čerpadlo min", "Topenie", "", "fas fa-sliders-h"),
    "topenie_pump_max": ("Čerpadlo max", "Topenie", "", "fas fa-sliders-h"),
    "topenie_smoke_target": ("Cieľová teplota dymovodu", "Topenie", "°C", "fas fa-thermometer-half"),
    "topenie_priority": ("Priorita", "Topenie", "", "fas fa-exclamation-triangle"),
    "topenie_tuv_target": ("Cieľová teplota TUV", "Topenie", "°C", "fas fa-thermometer-half"),
    "topenie_tuv_tolerance": ("Tolerancia TUV", "Topenie", "", "fas fa-sliders-h"),
    "topenie_boiler_target": ("Cieľová teplota kotla", "Topenie", "°C", "fas fa-thermometer-half"),
    "topenie_boiler_tuv_target": ("Cieľová teplota kotla TUV", "Topenie", "°C", "fas fa-thermometer-half"),
    "topenie_door_position": ("Poloha dvierok", "Topenie", "%", "fas fa-door-open"),
    "topenie_door_slider": ("Slider dvierok", "Topenie", "", "fas fa-sliders-h"),
    "topenie_door_close_button": ("Tlačidlo zatvoriť dvierka", "Topenie", "", "fas fa-door-closed"),
    "topenie_init": ("Inicializácia", "Topenie", "", "fas fa-sync"),
    "topenie_status": ("Stav", "Topenie", "", "fas fa-info-circle"),
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
    key = data.get("key") or data.get("pin")
    value = data.get("value")
    if not key:
        return jsonify({"status": "error", "message": "no key/pin"}), 400

    if str(key).startswith("V") or str(key).startswith("v"):
        key = str(key).upper()
        if not key.startswith("V"):
            key = "V" + key

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
<html lang="sk" data-bs-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>iHome - Domáca automatizácia</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #121212;
      --text: #e0e0e0;
      --card: #1e1e1e;
      --primary: #0dcaf0;
      --value-color: #ffffff;
    }
    [data-bs-theme="light"] {
      --bg: #f8f9fa;
      --text: #212529;
      --card: #ffffff;
      --primary: #0d6efd;
      --value-color: #000000;
    }

    body { background: var(--bg); color: var(--text); min-height: 100vh; }
    .navbar { background: #1f1f1f !important; }
    [data-bs-theme="light"] .navbar { background: #343a40 !important; }

    .card { background: var(--card); border: none; border-radius: 16px; box-shadow: 0 8px 25px rgba(0,0,0,0.3); }
    .chart-container { background: var(--card); border-radius: 12px; padding: 20px; margin-bottom: 20px; height: 500px; }
    .info-bar { background: rgba(30,30,30,0.8); padding: 10px 15px; border-radius: 12px; font-size: 0.95rem; }
    [data-bs-theme="light"] .info-bar { background: rgba(255,255,255,0.9); }

    .detail-group { border: 2px solid var(--primary); border-radius: 16px; padding: 12px; margin-bottom: 25px; background: rgba(30,30,30,0.6); }
    [data-bs-theme="light"] .detail-group { background: rgba(255,255,255,0.7); }

    .detail-group h4 { color: var(--primary); border-bottom: 1px solid var(--primary); padding-bottom: 8px; margin-bottom: 12px; text-align: center; font-size: 1.2rem; }

    .section, .sub-section { display: none; }
    .section.active, .sub-section.active { display: block; }

    .clickable-card { cursor: pointer; transition: all 0.3s ease; }
    .clickable-card:hover { transform: translateY(-5px); box-shadow: 0 15px 30px rgba(0,0,0,0.4) !important; border: 2px solid var(--primary); }

    .detail-card .key-value {
      color: var(--value-color) !important;
      font-size: 1.6rem !important;
      font-weight: bold;
    }

    .detail-card i { color: var(--primary); }
    .detail-card .text-muted { color: #aaa !important; }
    [data-bs-theme="light"] .detail-card .text-muted { color: #666 !important; }

    #bms .card { background: #2a2a2a !important; color: #e0e0e0 !important; }
    [data-bs-theme="light"] #bms .card { background: #f8f9fa !important; color: #212529 !important; }
    #bms .text-muted { color: #bbbbbb !important; }
    [data-bs-theme="light"] #bms .text-muted { color: #666 !important; }

    .energy-card { font-size: 1.1rem; padding: 12px; border-radius: 12px; background: rgba(0,0,0,0.3); }
    [data-bs-theme="light"] .energy-card { background: rgba(0,0,0,0.1); }

    .bms-pill-btn i { font-size: 2.5rem; margin-bottom: 8px; }
  </style>
</head>
<body>
  <nav class="navbar navbar-expand-lg navbar-dark mb-3 shadow">
    <div class="container-fluid">
      <a class="navbar-brand" href="#" onclick="showMainSection('home')"><strong>iHome</strong></a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav me-auto">
          <li class="nav-item"><a class="nav-link active" href="#" onclick="showMainSection('home')">Domov</a></li>
          <li class="nav-item"><a class="nav-link" href="#" onclick="showMainSection('fotovoltaika')">Fotovoltaika</a></li>
          <li class="nav-item"><a class="nav-link" href="#" onclick="showMainSection('topenie')">Topenie</a></li>
        </ul>
        <button id="theme-toggle" class="btn btn-outline-light"><i class="fas fa-moon"></i></button>
      </div>
    </div>
  </nav>

  <div class="container mb-4">
    <div class="info-bar text-center d-flex justify-content-center flex-wrap gap-4">
      <span><i class="fas fa-home me-2"></i> Vnútri: <strong id="indoor-temp-value">-</strong>°C</span>
      <span><i class="fas fa-tint me-2"></i> Vlhkosť: <strong id="indoor-hum-value">-</strong>%</span>
      <span><i class="fas fa-cog me-2"></i> Režim: <strong id="mode-value">-</strong></span>
      <span><i class="fas fa-thermometer-half me-2"></i> Menič: <strong id="temp-value">-</strong>°C</span>
    </div>
  </div>

  <div class="container">
    <div id="home" class="section active">
      <h2 class="text-center mb-5 mt-4 text-primary fw-bold">Hlavný prehľad</h2>

      <div class="card shadow-lg mb-4 clickable-card" onclick="showMainSection('fotovoltaika'); showSubSection('detail')">
        <div class="card-body py-4">
          <div class="row align-items-center">
            <div class="col-3 text-center">
              <i class="fas fa-solar-panel fa-4x text-warning"></i>
            </div>
            <div class="col-9">
              <div class="row g-2">
                <div class="col-6">
                  <div class="text-muted small">Spotreba domu</div>
                  <div class="fs-4 fw-bold text-info" id="home-V65">-</div>
                </div>
                <div class="col-6">
                  <div class="text-muted small">Výkon PV</div>
                  <div class="fs-4 fw-bold text-warning" id="home-V76">-</div>
                </div>
                <div class="col-6">
                  <div class="text-muted small">Batéria +/-</div>
                  <div class="fs-4 fw-bold text-primary" id="home-V75">-</div>
                </div>
                <div class="col-6">
                  <div class="text-muted small">Batéria</div>
                  <div class="fs-4 fw-bold text-success" id="home-V70">-</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="card shadow-lg clickable-card" onclick="showMainSection('topenie')">
        <div class="card-body py-4">
          <div class="row align-items-center">
            <div class="col-3 text-center">
              <i class="fas fa-fire fa-4x text-danger"></i>
            </div>
            <div class="col-9">
              <h4 class="mb-0">Topenie</h4>
              <p class="text-muted mb-0">Zatiaľ žiadne dáta</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div id="fotovoltaika" class="section">
      <div class="container mb-4">
        <ul class="nav nav-pills nav-fill shadow rounded bg-dark">
          <li class="nav-item"><a class="nav-link active" href="#" onclick="showSubSection('detail')">Detail</a></li>
          <li class="nav-item"><a class="nav-link" href="#" onclick="showSubSection('grafy'); loadToday()">Grafy</a></li>
          <li class="nav-item"><a class="nav-link" href="#" onclick="showSubSection('bms')">BMS</a></li>
          <li class="nav-item"><a class="nav-link" href="#" onclick="showSubSection('control')">Ovládanie</a></li>
        </ul>
      </div>

      <div id="sub-detail" class="sub-section active">
        <div class="container">
          <h2 class="text-center mb-4">Detailné hodnoty</h2>
          <div class="row" id="detail-content"></div>
        </div>
      </div>

      <div id="sub-grafy" class="sub-section">
        <div class="container">
          <h2 class="text-center mb-4">Grafy a energie</h2>
          <div class="btn-group mb-4 flex-wrap" role="group" id="time-buttons">
            <button class="btn btn-primary active" onclick="loadToday(event)">Dnes</button>
            <button class="btn btn-primary" onclick="loadMinutes(30, event)">30 min</button>
            <button class="btn btn-primary" onclick="loadMinutes(60, event)">1h</button>
            <button class="btn btn-primary" onclick="loadMinutes(180, event)">3h</button>
            <button class="btn btn-primary" onclick="loadMinutes(360, event)">6h</button>
            <button class="btn btn-primary" onclick="loadMinutes(720, event)">12h</button>
            <button class="btn btn-primary" onclick="loadMinutes(1440, event)">24h</button>
            <button class="btn btn-primary" onclick="loadMinutes(10080, event)">7 dní</button>
            <button class="btn btn-primary" onclick="loadMinutes(43200, event)">30 dní</button>
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
            <div class="col-6"><div class="energy-card text-warning"><strong>Výroba PV</strong><span class="key-value" id="energy-pv">0</span> kWh</div></div>
            <div class="col-6"><div class="energy-card text-info"><strong>Spotreba domu</strong><span class="key-value" id="energy-load">0</span> kWh</div></div>
            <div class="col-6"><div class="energy-card text-success"><strong>Nabíjanie batérie</strong><span class="key-value" id="energy-charge">0</span> kWh</div></div>
            <div class="col-6"><div class="energy-card text-danger"><strong>Vybíjanie batérie</strong><span class="key-value" id="energy-discharge">0</span> kWh</div></div>
          </div>
          <div class="row">
            <div class="col-12"><div class="chart-container"><canvas id="chartPower"></canvas></div></div>
            <div class="col-12"><div class="chart-container"><canvas id="chartSOC"></canvas></div></div>
          </div>
        </div>
      </div>

      <div id="sub-bms" class="sub-section">
        <div class="container">
          <h2 class="text-center mb-4">JK-BMS – Jednotlivé články</h2>

          <div class="row mb-4 g-3 justify-content-center">
            <div class="col-6 col-md-3">
              <div class="card text-center p-3 shadow bms-card">
                <div class="text-muted small">Celkové napätie</div>
                <div class="fs-3 fw-bold" id="bms-total-voltage">-</div>
              </div>
            </div>
            <div class="col-6 col-md-3">
              <div class="card text-center p-3 shadow bms-card">
                <div class="text-muted small">Prúd</div>
                <div class="fs-3 fw-bold" id="bms-current">-</div>
              </div>
            </div>
            <div class="col-6 col-md-3">
              <div class="card text-center p-3 shadow bms-card">
                <div class="text-muted small">SOC</div>
                <div class="fs-3 fw-bold" id="bms-soc">-</div>
              </div>
            </div>
            <div class="col-6 col-md-3">
              <div class="card text-center p-3 shadow bms-card">
                <div class="text-muted small">Delta U</div>
                <div class="fs-3 fw-bold text-warning" id="bms-delta">-</div>
              </div>
            </div>
          </div>

          <div class="row mb-4 g-3 justify-content-center">
            <div class="col-6 col-md-3">
              <div class="card text-center p-2 bms-card">
                <div class="text-muted small">Temp FET / T1</div>
                <div class="fs-4" id="bms-temp1">-</div>
              </div>
            </div>
            <div class="col-6 col-md-3">
              <div class="card text-center p-2 bms-card">
                <div class="text-muted small">Temp 2</div>
                <div class="fs-4" id="bms-temp2">-</div>
              </div>
            </div>
          </div>

          <div class="card p-3 shadow">
            <h4 class="text-center text-primary mb-3">Napätia článkov</h4>
            <div class="row g-2" id="bms-cells"></div>
          </div>

          <div class="row justify-content-center mt-5">
            <div class="col-12 col-md-10 col-lg-8">
              <h4 class="text-center text-primary mb-5 fw-bold">Ovládanie BMS</h4>
              <div class="row g-3 mb-4 justify-content-center">
                <div class="col-5">
                  <button class="btn btn-success w-100 py-3 rounded-pill shadow d-flex flex-column align-items-center justify-content-center"
                          onclick="controlBMS('charge_on')">
                    <i class="fas fa-plug fa-3x mb-2 text-white"></i>
                    <div class="fw-bold">Nabíjanie</div>
                    <small>ZAPNÚŤ</small>
                  </button>
                </div>
                <div class="col-5">
                  <button class="btn btn-danger w-100 py-3 rounded-pill shadow d-flex flex-column align-items-center justify-content-center"
                          onclick="controlBMS('charge_off')">
                    <i class="fas fa-power-off fa-3x mb-2 text-white"></i>
                    <div class="fw-bold">Nabíjanie</div>
                    <small>VYPNÚŤ</small>
                  </button>
                </div>
              </div>
              <div class="row g-3 justify-content-center">
                <div class="col-5">
                  <button class="btn btn-info w-100 py-3 rounded-pill shadow d-flex flex-column align-items-center justify-content-center"
                          onclick="controlBMS('discharge_on')">
                    <i class="fas fa-bolt fa-3x mb-2 text-white"></i>
                    <div class="fw-bold">Vybíjanie</div>
                    <small>ZAPNÚŤ</small>
                  </button>
                </div>
                <div class="col-5">
                  <button class="btn btn-danger w-100 py-3 rounded-pill shadow d-flex flex-column align-items-center justify-content-center"
                          onclick="controlBMS('discharge_off')">
                    <i class="fas fa-power-off fa-3x mb-2 text-white"></i>
                    <div class="fw-bold">Vybíjanie</div>
                    <small>VYPNÚŤ</small>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div id="sub-control" class="sub-section">
        <div class="container">
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
    </div>

    <div id="topenie" class="section">
      <div class="container">
        <h2 class="text-center mt-5 text-primary">Topenie</h2>
        <p class="text-center text-muted mt-4">Zatiaľ žiadne dáta k dispozícii.</p>
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

    const themeToggle = document.getElementById('theme-toggle');
    const htmlEl = document.documentElement;

    function setTheme(theme) {
      htmlEl.setAttribute('data-bs-theme', theme);
      themeToggle.innerHTML = theme === 'dark' 
        ? '<i class="fas fa-moon"></i>' 
        : '<i class="fas fa-sun"></i>';
      localStorage.setItem('theme', theme);
    }

    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);

    themeToggle.addEventListener('click', () => {
      const current = htmlEl.getAttribute('data-bs-theme');
      setTheme(current === 'dark' ? 'light' : 'dark');
    });

    function showMainSection(id) {
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
      document.getElementById(id).classList.add('active');
      document.querySelectorAll('.navbar .nav-link').forEach(l => l.classList.remove('active'));
      document.querySelector(`.navbar .nav-link[onclick="showMainSection('${id}')"]`)?.classList.add('active');
      if (id === 'fotovoltaika') showSubSection('detail');
    }

    function showSubSection(id) {
      document.querySelectorAll('#fotovoltaika .sub-section').forEach(s => s.classList.remove('active'));
      document.getElementById('sub-' + id).classList.add('active');
      document.querySelectorAll('#fotovoltaika .nav-link').forEach(l => l.classList.remove('active'));
      document.querySelector(`#fotovoltaika .nav-link[onclick*="${id}"]`).classList.add('active');
      if (id === 'grafy') loadToday();
    }

    function updateHomeSummary() {
      document.getElementById('home-V65').textContent = data['V65'] !== undefined ? data['V65'] + ' W' : '-';
      document.getElementById('home-V76').textContent = data['V76'] !== undefined ? data['V76'] + ' W' : '-';
      document.getElementById('home-V75').textContent = data['V75'] !== undefined ? (data['V75'] > 0 ? '+' : '') + data['V75'] + ' W' : '-';
      document.getElementById('home-V70').textContent = data['V70'] !== undefined ? data['V70'] + ' %' : '-';
    }

    function updateInfoBar() {
      document.getElementById('indoor-temp-value').textContent = data['indoor_temp'] !== undefined ? parseFloat(data['indoor_temp']).toFixed(1) : '-';
      document.getElementById('indoor-hum-value').textContent = data['indoor_humidity'] !== undefined ? Math.round(data['indoor_humidity']) : '-';
      document.getElementById('mode-value').textContent = data['V1'] || '-';
      document.getElementById('temp-value').textContent = data['V71'] || '-';
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
        let groupHTML = `<div class="col-12 mb-4"><div class="detail-group"><h4>${groupName}</h4><div class="row justify-content-center">`;
        pins.forEach(pin => {
          if (data[pin] !== undefined) {
            const meta = info[pin] || [pin, "", ""];
            const displayValue = pin === "V7" ? (data[pin] > 0 ? data[pin] + "%" : "Vypnutý") : data[pin];
            groupHTML += `<div class="col-lg-3 col-md-4 col-sm-6 mb-2">
              <div class="card detail-card text-center">
                <i class="${meta[3] || "fas fa-circle"} fa-1x mb-1" style="color:var(--primary)"></i>
                <div class="text-muted small">${meta[0]}</div>
                <div class="key-value" style="color:var(--value-color); font-size:1.4rem;">${displayValue}${meta[2] ? ' ' + meta[2] : ''}</div>
              </div>
            </div>`;
          }
        });
        groupHTML += `</div></div></div>`;
        c.innerHTML += groupHTML;
      });
    }

    function renderBMSPage() {
      const totalV   = data['V230'] || '-';
      const current  = data['V231'] || '-';
      const soc      = data['V232'] || '-';
      const delta    = data['V233'] || '-';
      const minCell  = data['V234'] || null;
      const maxCell  = data['V236'] || null;
      const temp1    = data['V238'] || '-';
      const temp2    = data['V239'] || '-';

      document.getElementById('bms-total-voltage').textContent = totalV + ' V';
      document.getElementById('bms-current').textContent = current + ' A';
      document.getElementById('bms-soc').textContent = soc + ' %';
      document.getElementById('bms-delta').textContent = delta + ' V';
      document.getElementById('bms-temp1').textContent = temp1 + ' °C';
      document.getElementById('bms-temp2').textContent = temp2 + ' °C';

      const container = document.getElementById('bms-cells');
      container.innerHTML = '';
      for (let i = 0; i < 24; i++) {
        const pin = `V${240 + i}`;
        const value = data[pin];
        if (value === undefined || value === '-') continue;

        const volt = parseFloat(value);
        let bgClass = 'bg-dark text-white';
        let label = 'normal';

        if (i + 1 == minCell) { bgClass = 'bg-danger text-white'; label = 'minimum'; }
        if (i + 1 == maxCell) { bgClass = 'bg-success text-white'; label = 'maximum'; }

        container.innerHTML += `
          <div class="col-4 col-sm-3 col-md-2">
            <div class="card text-center p-2 ${bgClass}">
              <div class="small">Čl. ${i+1}</div>
              <div class="fs-5 fw-bold">${volt.toFixed(3)} V</div>
              <div class="tiny">${label}</div>
            </div>
          </div>`;
      }
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
            { label: 'Výkon PV (W)', data: h.pv, borderColor: '#ffc107', backgroundColor: '#ffc10730', tension: 0.3, fill: true },
            { label: 'Spotreba domu (W)', data: h.load, borderColor: '#0dcaf0', backgroundColor: '#0dcaf030', tension: 0.3, fill: true },
            { label: 'Batéria +/- (W)', data: h.grid, borderColor: '#dc3545', backgroundColor: '#dc354530', tension: 0.3, fill: true }
          ]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { x: { ticks: { maxTicksLimit: 15 } } } }
      });

      const ctxSOC = document.getElementById('chartSOC').getContext('2d');
      if (charts.soc) charts.soc.destroy();
      charts.soc = new Chart(ctxSOC, {
        type: 'line',
        data: { labels: h.timestamps, datasets: [{ label: 'SOC batérie (%)', data: h.soc, borderColor: '#28a745', backgroundColor: '#28a74530', tension: 0.3, fill: true }] },
        options: { responsive: true, maintainAspectRatio: false, scales: { x: { ticks: { maxTicksLimit: 15 } } } }
      });
    }

    async function loadToday(event) {
      if (event) {
        document.querySelectorAll('#time-buttons .btn').forEach(b => b.classList.remove('active'));
        event.target.classList.add('active');
      }
      const res = await fetch('/history/today');
      const h = await res.json();
      renderEnergy(h.energy);
      updateCharts(h);
    }

    async function loadMinutes(m, event) {
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

    document.getElementById('toggle-custom').addEventListener('click', () => {
      const el = document.getElementById('custom-range');
      el.style.display = el.style.display === 'none' ? 'block' : 'none';
    });

    async function sendCmd(key, value) {
      await fetch('/write', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({key: key, value: value})});
      load();
    }

    async function controlBMS(action) {
      try {
        const response = await fetch('http://192.168.3.84:8001/bms/control', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({action: action})
        });
        const result = await response.json();
        if (result.status === "success") {
          alert("✓ " + result.message);
        } else {
          alert("✗ Chyba: " + result.message);
        }
      } catch (e) {
        alert("✗ Nepodarilo sa spojiť s BMS ovládačom. Je Main.py spustený?");
      }
      load();
    }

    async function load() {
      try {
        const [d, i] = await Promise.all([fetch('/data'), fetch('/vpin_info')]);
        data = await d.json();
        info = await i.json();
        renderDetail();
        renderBMSPage();
        updateHomeSummary();
        updateInfoBar();
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
    print("iHome dashboard beží na http://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)