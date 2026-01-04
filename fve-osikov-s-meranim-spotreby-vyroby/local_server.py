#!/usr/bin/env python3
"""
local_server.py - iHome dashboard s plným ovládaním meniča
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
    "V72": ("PV1 prúd do batérie", "Fotovoltaika", "A", "fas fa-bolt"),
    "V73": ("PV1 napätie", "Fotovoltaika", "V", "fas fa-plug"),
    "V76": ("PV1 výkon", "Fotovoltaika", "W", "fas fa-solar-panel"),
    "V25": ("PV2 prúd do batérie", "Fotovoltaika", "A", "fas fa-bolt"),
    "V26": ("PV2 napätie", "Fotovoltaika", "V", "fas fa-plug"),
    "V27": ("PV2 výkon", "Fotovoltaika", "W", "fas fa-solar-panel"),
    "V68": ("Napätie batérie", "Batéria", "V", "fas fa-battery-half"),
    "V69": ("Prúd batérie", "Batéria", "A", "fas fa-tachometer-alt"),
    "V70": ("SOC batérie", "Batéria", "%", "fas fa-battery-full"),
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
    "V110": ("Reset skriptu", "Ovládanie", "", "fas fa-redo"),
    "indoor_temp": ("Teplota vnútri", "Senzory", "°C", "fas fa-thermometer-half"),
    "indoor_humidity": ("Vlhkosť vnútri", "Senzory", "%", "fas fa-tint"),
    "outdoor_temp": ("Teplota vonku", "Senzory", "°C", "fas fa-thermometer-half"),
    "outdoor_humidity": ("Vlhkosť vonku", "Senzory", "%", "fas fa-tint"),
    "V21": ("Nabíjanie BMS", "BMS", "", "fas fa-plug"),
    "V22": ("Vybíjanie BMS", "BMS", "", "fas fa-bolt"),

    # PZEM-004T distribúcia
    "PZEM_L1_voltage": ("Napätie L1", "Distribúcia", "V", "fas fa-bolt"),
    "PZEM_L1_current": ("Prúd L1", "Distribúcia", "A", "fas fa-tachometer-alt"),
    "PZEM_L1_power": ("Výkon L1", "Distribúcia", "W", "fas fa-plug"),
    "PZEM_L1_energy": ("Energia L1", "Distribúcia", "kWh", "fas fa-battery-full"),
    "PZEM_L1_freq": ("Frekvencia L1", "Distribúcia", "Hz", "fas fa-wave-square"),
    "PZEM_L1_pf": ("PF L1", "Distribúcia", "", "fas fa-percentage"),

    "PZEM_L2_voltage": ("Napätie L2", "Distribúcia", "V", "fas fa-bolt"),
    "PZEM_L2_current": ("Prúd L2", "Distribúcia", "A", "fas fa-tachometer-alt"),
    "PZEM_L2_power": ("Výkon L2", "Distribúcia", "W", "fas fa-plug"),
    "PZEM_L2_energy": ("Energia L2", "Distribúcia", "kWh", "fas fa-battery-full"),

    "PZEM_L3_voltage": ("Napätie L3", "Distribúcia", "V", "fas fa-bolt"),
    "PZEM_L3_current": ("Prúd L3", "Distribúcia", "A", "fas fa-tachometer-alt"),
    "PZEM_L3_power": ("Výkon L3", "Distribúcia", "W", "fas fa-plug"),
    "PZEM_L3_energy": ("Energia L3", "Distribúcia", "kWh", "fas fa-battery-full"),

    "PZEM_total_power": ("Celkový výkon", "Distribúcia", "W", "fas fa-home"),
    "PZEM_total_energy": ("Celková spotreba", "Distribúcia", "kWh", "fas fa-chart-line"),

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

  <!-- Viewport (LEN JEDEN) -->
  <meta name="viewport"
        content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">

  <title>iHome - Domáca automatizácia</title>

  <!-- Styles -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">

  <!-- Icons -->
  <link rel="apple-touch-icon" sizes="180x180" href="/static/apple-touch-icon.png">
  <link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32x32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="/static/favicon-16x16.png">

  <!-- iOS app-like -->
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="iHome">

  <!-- Android / PWA -->
  <meta name="theme-color" content="#1e1e1e">
  <link rel="manifest" href="/static/manifest.json">

  <!-- Optional UX polish -->
  <meta name="format-detection" content="telephone=no">

  <!-- Scripts -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

  <style>

    :root { --bg: #121212; --text: #e0e0e0; --card: #1e1e1e; --primary: #0dcaf0; --value-color: #ffffff; }
    [data-bs-theme="light"] { --bg: #f8f9fa; --text: #212529; --card: #ffffff; --primary: #0d6efd; --value-color: #000000; }
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
    .detail-card .key-value { color: var(--value-color) !important; font-size: 1.6rem !important; font-weight: bold; }
    .detail-card i { color: var(--primary); }
    .detail-card .text-muted { color: #aaa !important; }
    [data-bs-theme="light"] .detail-card .text-muted { color: #666 !important; }
    #bms .card { background: #2a2a2a !important; color: #e0e0e0 !important; }
    [data-bs-theme="light"] #bms .card { background: #f8f9fa !important; color: #212529 !important; }
    .energy-card { font-size: 1.1rem; padding: 12px; border-radius: 12px; background: rgba(0,0,0,0.3); }
    [data-bs-theme="light"] .energy-card { background: rgba(0,0,0,0.1); }

    /* DIAGRAM – LEN GULIČKY, LEPŠIE NA MOBILE, MENŠÍ BLESK */
    .diagram-container { position: relative; width: 100%; max-width: 900px; height: 80vh; min-height: 600px; margin: 0 auto; }
    .inverter-center {
      position: absolute;
      top: 50%; left: 50%;
      transform: translate(-50%, -50%);
      width: 180px;           /* trocha širší ako vysoký – vyzerá lepšie ako obdĺžnik */
      height: 220px;
      background: rgba(13, 202, 240, 0.25);   /* trocha jemnejší priehľadný podklad */
      border: 6px solid var(--primary);      /* o niečo tenší okraj */
      border-radius: 20px;                   /* zaoblené rohy – 20px je pekné, moderné */
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 40px rgba(13, 202, 240, 0.6);  /* jemnejší tieň */
      z-index: 10;
      padding: 10px 0;       /* trocha vnútorného priestoru hore/dole */
    }

    .inverter-center i { font-size: 2.5rem; color: var(--primary); }
    .component {
      position: absolute;
      width: 150px;
      height: 170px;
      text-align: center;
      background: var(--card);
      padding: 22px;
      border-radius: 30px;
      box-shadow: 0 12px 40px rgba(0,0,0,0.6);
      z-index: 5;
    }
    
    .flow-dot {
      position: absolute;
      width: 20px; height: 20px;
      background: var(--primary);
      border-radius: 50%;
      box-shadow: 0 0 30px var(--primary);
      animation: flow 3s linear infinite;
      display: none;
      z-index: 3;
    }

    /* Jemný hover pre celú skupinu tlačidiel */
    .btn-group:hover {
      box-shadow: 0 8px 25px rgba(13, 202, 240, 0.25);
      transform: translateY(-3px);
      transition: all 0.3s ease;
    }

    /* Ešte lepší efekt pre primárne tlačidlo vnútri */
    .btn-group .btn-primary {
      transition: all 0.3s ease;
    }
    .btn-group .btn-primary:hover {
      box-shadow: 0 6px 20px rgba(13, 202, 240, 0.4);
    }

    /* Hrubší a jasnejší modrý okraj pre outline tlačidlo */
    .custom-outline {
      border-width: 2px !important;
      border-color: var(--primary);
    }

    /* Ešte lepšia viditeľnosť pri hover/focus */
    .custom-outline:hover,
    .custom-outline:focus {
      background: rgba(13, 202, 240, 0.15);
      border-color: var(--primary);
      box-shadow: 0 0 0 0.25rem rgba(13, 202, 240, 0.3);
    }

    /* Jemný lift efekt pre všetky tlačidlá v tejto sekcii */
    #sub-control .btn {
      transition: all 0.25s ease;
    }
    #sub-control .btn:hover {
      transform: translateY(-3px);
      box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
    }

    /* Zabezpečí, že tlačidlá nebudú príliš úzke ani na mobile */
    .min-width-btn {
      min-width: 220px;
    }

    /* Jemný hover lift aj pre BMS tlačidlá – rovnako ako v Ovládaní meniča */
    #sub-bms .btn {
      transition: all 0.25s ease;
    }
    #sub-bms .btn:hover {
      transform: translateY(-3px);
      box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
    }

    @keyframes flow { 0% { transform: translate(0, 0); } 100% { transform: var(--move); } }
    @media (max-width: 768px) {
      .diagram-container { height: 75vh; min-height: 560px; }
      .inverter-center { width: 130px; height: 180px; }
      .inverter-center i { font-size: 3.6rem; }
      .component { width: 125px; padding: 16px; }
      .flow-dot { width: 16px; height: 16px; }
    }
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
          <li class="nav-item"><a class="nav-link" href="#" onclick="showMainSection('distribucia')">Distribúcia</a></li>
        </ul>
        <button id="theme-toggle" class="btn btn-outline-light"><i class="fas fa-moon"></i></button>
      </div>
    </div>
  </nav>

  <div class="container mb-4">
    <div class="info-bar text-center d-flex justify-content-center flex-wrap gap-4">
      <span>Von: <i class="fa fa-thermometer-half"></i> <strong id="outdoor-temp-value">-</strong>°C <i class="fas fa-tint me-2"></i><strong id="outdoor-hum-value">-</strong>%</span>
      <span>Dnu: <i class="fa fa-thermometer-half"></i> <strong id="indoor-temp-value">-</strong>°C <i class="fas fa-tint me-2"></i><strong id="indoor-hum-value">-</strong>%</span>
      </div>
  </div>

  <div class="container">
    <div id="home" class="section active">
      <h2 class="text-center mb-5 mt-4 text-primary fw-bold">Hlavný prehľad</h2>

      <div class="card shadow-lg mb-4 clickable-card" onclick="showMainSection('fotovoltaika'); showSubSection('home')">
        <div class="card-body py-4">
          <div class="row align-items-center">
            <div class="col-3 d-flex align-items-center justify-content-center">
              <i class="fas fa-solar-panel fa-3x text-warning"></i>
            </div>
            <div class="col-9">
              <div class="row g-3 mb-4">
                <div class="col-6"><div class="text-muted small">Spotreba domu</div><div class="fs-4 fw-bold text-info" id="home-V65">-</div></div>
                <div class="col-6"><div class="text-muted small">Solar výkon</div><div class="fs-4 fw-bold text-warning" id="home-V76">-</div></div>
                <div class="col-6"><div class="text-muted small">Batéria +/-</div><div class="fs-4 fw-bold text-primary" id="home-V75">-</div></div>
                <div class="col-6"><div class="text-muted small">Nabitá na</div><div class="fs-4 fw-bold text-success" id="home-V70">-</div></div>
              </div>
              <div class="inverter-info">
                <div class="row g-2">
                  <div class="col-6 d-flex align-items-center"><i class="fas fa-cog me-2"></i><strong id="home-mode-value" class="ms-1">-</strong></div>
                  <div class="col-6 d-flex align-items-center"><i class="fas fa-thermometer-half me-2"></i> Inv.: <strong id="home-temp-value" class="ms-1">-</strong>°C</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="card shadow-lg mb-4 clickable-card" onclick="showMainSection('topenie')">
        <div class="card-body py-4">
          <div class="row align-items-center">
            <div class="col-3 text-center"><i class="fas fa-fire fa-4x text-danger"></i></div>
            <div class="col-9"><h4 class="mb-0">Topenie</h4><p class="text-muted mb-0">Zatiaľ žiadne dáta</p></div>
          </div>
        </div>
      </div>

      <div class="card shadow-lg clickable-card" onclick="showMainSection('distribucia')">
        <div class="card-body py-4">
          <div class="row align-items-center">
            <div class="col-3 d-flex align-items-center justify-content-center">
              <i class="fas fa-plug-circle-bolt fa-3x text-primary"></i>
            </div>
            <div class="col-9">
              <div class="row g-3 mb-4">
                <div class="col-6"><div class="text-muted small">Výkon L1</div><div class="fs-4 fw-bold text-warning" id="home-L1-power">-</div></div>
                <div class="col-6"><div class="text-muted small">Výkon L2</div><div class="fs-4 fw-bold text-warning" id="home-L2-power">-</div></div>
                <div class="col-6"><div class="text-muted small">Výkon L3</div><div class="fs-4 fw-bold text-warning" id="home-L3-power">-</div></div>
                <div class="col-6"><div class="text-muted small">Celkový výkon</div><div class="fs-4 fw-bold text-info" id="home-total-power">-</div></div>
              </div>
              <div class="text-muted small">Celková spotreba: <strong id="home-total-energy">-</strong></div>
            </div>
          </div>
        </div>
      </div>

    </div>


    

    <div id="fotovoltaika" class="section">
      <div class="container mb-4">
        <ul class="nav nav-pills nav-fill shadow rounded bg-dark">
          <li class="nav-item"><a class="nav-link active" href="#" onclick="showSubSection('home')">Home</a></li>
          <li class="nav-item"><a class="nav-link" href="#" onclick="showSubSection('detail')">Detail</a></li>
          <li class="nav-item"><a class="nav-link" href="#" onclick="showSubSection('grafy')">Grafy</a></li>
          <li class="nav-item"><a class="nav-link" href="#" onclick="showSubSection('bms')">BMS</a></li>
          <li class="nav-item"><a class="nav-link" href="#" onclick="showSubSection('control')">Ovládanie</a></li>
        </ul>
      </div>

      <div id="sub-home" class="sub-section active">
        <div class="container py-4">
          <h2 class="text-center mb-5 text-primary fw-bold ">Prehľad systému</h2>
          <div class="diagram-container">

            <div class="inverter-center">
              <i class="fas fa-bolt"></i>
              <div class="mt-2 small">Inverter mode</div>
              <div class="mt-1 small text-primary fw-bold" id="inverter-mode">-</div>
              <div class="fw-bold fs-3 mt-1" id="inverter-temp">-</div>
            </div>

            <div class="component" style="top: 5%; left: 5%;">
              <div class="small fw-bold mb-1">Grid</div>
              <div id="grid-voltage" class="fs-4 text-warning">-</div>
              <i class="fas fa-plug fa-2x text-warning mt-2"></i>
            </div>

            <div class="component" style="top: 5%; right: 5%;">
              <div class="small fw-bold mb-1">PV</div>
              <div id="pv-power" class="fs-4 text-warning">0 W</div>
              <i class="fas fa-solar-panel fa-2x text-warning mt-2"></i>
            </div>

            <div class="component" style="bottom: 5%; left: 5%;">
              <div class="small fw-bold mb-1">Batéria</div>
              <div id="battery-power" class="fs-4">0 W</div>
              <div id="battery-soc" class="text-success fs-4 mt-1">-</div>
              <i id="battery-icon" class="fas fa-battery-full fa-2x text-success mt-2"></i>
            </div>

            <div class="component" style="bottom: 5%; right: 5%;">
              <div class="small fw-bold mb-1">Spotreba</div>
              <div id="load-power" class="fs-4 text-info">0 W</div>
              <i class="fas fa-home fa-2x text-info mt-2"></i>
            </div>

            <div id="grid-flow-dot" class="flow-dot" style="top: calc(50% - 10px); left: calc(50% - 10px);"></div>
            <div id="pv-flow-dot" class="flow-dot" style="top: calc(50% - 10px); left: calc(50% - 10px);"></div>
            <div id="battery-flow-dot" class="flow-dot" style="top: calc(50% - 10px); left: calc(50% - 10px);"></div>
            <div id="load-flow-dot" class="flow-dot" style="top: calc(50% - 10px); left: calc(50% - 10px);"></div>

          </div>

          <!-- Rýchle prepnutie priority výstupu -->
          <div class="mt-5">
            <h4 class="text-center text-primary mb-4 fw-bold">Rýchle prepnutie priority výstupu</h4>
            <div class="row g-3 justify-content-center">
              <div class="col-12 col-sm-4">
                <button class="btn btn-outline-warning w-100 shadow-sm rounded-pill fw-bold" 
                        onclick="quickSetPriority(0)">
                  <i class="fas fa-plug-circle-bolt me-2"></i>
                  Distribúcia<br><small>(Utility First)</small>
                </button>
              </div>
              <div class="col-12 col-sm-4">
                <button class="btn btn-outline-success w-100 shadow-sm rounded-pill fw-bold" 
                        onclick="quickSetPriority(1)">
                  <i class="fas fa-solar-panel me-2"></i>
                  Solar<br><small>(Solar First)</small>
                </button>
              </div>
              <div class="col-12 col-sm-4">
                <button class="btn btn-outline-info w-100 shadow-sm rounded-pill fw-bold" 
                        onclick="quickSetPriority(2)">
                  <i class="fas fa-battery-full me-2"></i>
                  Batéria<br><small>(SBU Priority)</small>
                </button>
              </div>
            </div>
            <div class="text-center mt-3 text-muted small">
              Okamžitá zmena priority výstupu meniča
            </div>
          </div>

        </div>
      </div>

      <div id="sub-detail" class="sub-section">
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
          <div id="energy-summary" class="row mb-5 g-4 justify-content-center">
            <div class="col-6 col-md-3">
              <div class="energy-card text-center p-4 rounded shadow-sm">
                <div class="text-warning fw-bold mb-3 fs-5">Výroba PV</div>
                <div class="d-flex justify-content-center align-items-baseline gap-2">
                  <div class="key-value fs-2 fw-bold text-warning" id="energy-pv">0</div>
                  <div class="fs-4 text-warning opacity-75">kWh</div>
                </div>
              </div>
            </div>

            <div class="col-6 col-md-3">
              <div class="energy-card text-center p-4 rounded shadow-sm">
                <div class="text-info fw-bold mb-3 fs-5">Spotreba</div>
                <div class="d-flex justify-content-center align-items-baseline gap-2">
                  <div class="key-value fs-2 fw-bold text-info" id="energy-load">0</div>
                  <div class="fs-4 text-info opacity-75">kWh</div>
                </div>
              </div>
            </div>

            <div class="col-6 col-md-3">
              <div class="energy-card text-center p-4 rounded shadow-sm">
                <div class="text-success fw-bold mb-3 fs-5">Nabíjanie</div>
                <div class="d-flex justify-content-center align-items-baseline gap-2">
                  <div class="key-value fs-2 fw-bold text-success" id="energy-charge">0</div>
                  <div class="fs-4 text-success opacity-75">kWh</div>
                </div>
              </div>
            </div>

            <div class="col-6 col-md-3">
              <div class="energy-card text-center p-4 rounded shadow-sm">
                <div class="text-danger fw-bold mb-3 fs-5">Vybíjanie</div>
                <div class="d-flex justify-content-center align-items-baseline gap-2">
                  <div class="key-value fs-2 fw-bold text-danger" id="energy-discharge">0</div>
                  <div class="fs-4 text-danger opacity-75">kWh</div>
                </div>
              </div>
            </div>
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
            <div class="col-12 col-md-9 col-lg-7"> <!-- Užšie na veľkých obrazovkách -->
              <div class="card p-4 shadow"> <!-- Karta okolo ovládania -->
                <h4 class="text-center text-primary mb-4 fw-bold">Ovládanie BMS</h4>

                <!-- Nabíjanie: ON / OFF -->
                <div class="d-flex flex-column flex-sm-row gap-3 justify-content-center align-items-center mb-4">
                  <button class="btn btn-success px-5 py-3 rounded-pill shadow-sm fw-medium flex-grow-1 flex-sm-grow-0 min-width-btn"
                          onclick="controlBMS('charge_on')">
                    <i class="fas fa-plug me-2"></i>
                    <span class="d-none d-sm-inline">Zapnúť nabíjanie</span>
                    <span class="d-inline d-sm-none">Nabíjanie ON</span>
                  </button>

                  <button class="btn btn-danger px-5 py-3 rounded-pill shadow-sm fw-medium flex-grow-1 flex-sm-grow-0 min-width-btn"
                          onclick="controlBMS('charge_off')">
                    <i class="fas fa-power-off me-2"></i>
                    <span class="d-none d-sm-inline">Vypnúť nabíjanie</span>
                    <span class="d-inline d-sm-none">Nabíjanie OFF</span>
                  </button>
                </div>

                <!-- Vybíjanie: ON / OFF -->
                <div class="d-flex flex-column flex-sm-row gap-3 justify-content-center align-items-center">
                  <button class="btn btn-info px-5 py-3 rounded-pill shadow-sm fw-medium flex-grow-1 flex-sm-grow-0 min-width-btn"
                          onclick="controlBMS('discharge_on')">
                    <i class="fas fa-bolt me-2"></i>
                    <span class="d-none d-sm-inline">Zapnúť vybíjanie</span>
                    <span class="d-inline d-sm-none">Vybíjanie ON</span>
                  </button>

                  <button class="btn btn-danger px-5 py-3 rounded-pill shadow-sm fw-medium flex-grow-1 flex-sm-grow-0 min-width-btn"
                          onclick="controlBMS('discharge_off')">
                    <i class="fas fa-power-off me-2"></i>
                    <span class="d-none d-sm-inline">Vypnúť vybíjanie</span>
                    <span class="d-inline d-sm-none">Vybíjanie OFF</span>
                  </button>
                </div>

                <div class="mt-4 text-center text-muted small opacity-75">
                  Ovládanie batériového modulu Jikong JK-BMS
                </div>
              </div>
            </div>
          
          </div>
        </div>
      </div>

      <div id="sub-control" class="sub-section">
        <div class="container">
          <h2 class="text-center mb-5 text-primary fw-bold">Ovládanie meniča</h2>

          <div class="card p-4 mb-4 shadow">
            <h4 class="mb-4 text-primary">Nastavenia batérie</h4>
            <div class="row g-4 align-items-end">
              <div class="col-md-4">
                <label>Havarijné napätie (V)</label>
                <input type="number" step="0.1" min="40" max="48" class="form-control" id="v87">
              </div>
              <div class="col-md-4">
                <label>Prepnutie na DS (V)</label>
                <input type="number" step="0.1" min="48" max="58" class="form-control" id="v96">
              </div>
              <div class="col-md-4">
                <label>Prepnutie na inverter (V)</label>
                <input type="number" step="0.1" min="48" max="58" class="form-control" id="v86">
              </div>
              <div class="col-md-6">
                <label>Nabíjacie (Bulk) napätie (V)</label>
                <input type="number" step="0.1" min="48" max="58.4" class="form-control" id="v88">
              </div>
              <div class="col-md-6">
                <label>Plávajúce (Float) napätie (V)</label>
                <input type="number" step="0.1" min="48" max="58.4" class="form-control" id="v89">
              </div>
            </div>
          </div>

          <div class="card p-4 mb-4 shadow">
            <h4 class="mb-4 text-primary">Prúdy nabíjania</h4>
            <div class="row g-4 align-items-end">
              <div class="col-md-6">
                <label>Prúd nabíjania z AC (A)</label>
                <input type="number" min="0" max="99" class="form-control" id="v91">
              </div>
              <div class="col-md-6">
                <label>Max. nabíjací prúd (A)</label>
                <input type="number" min="10" max="90" class="form-control" id="v92">
              </div>
            </div>
          </div>

          <div class="card p-4 mb-5 shadow">
            <h4 class="mb-4 text-primary">Ostatné nastavenia</h4>
            <div class="row g-4">
              <div class="col-md-6">
                <label>Typ batérie</label>
                <select class="form-select" id="v90">
                  <option value="0">AGM</option>
                  <option value="1">Flooded</option>
                  <option value="2">User</option>
                </select>
              </div>
              <div class="col-md-6">
                <label>Priorita výstupu</label>
                <select class="form-select" id="v94">
                  <option value="0">Utility First</option>
                  <option value="1">Solar First</option>
                  <option value="2">SBU priority</option>
                </select>
              </div>
              <div class="col-md-6">
                <label>Priorita nabíjania</label>
                <select class="form-select" id="v95">
                  <option value="0">Solar First</option>
                  <option value="1">Solar and Utility</option>
                  <option value="2">Solar Only</option>
                  <option value="3">Utility First</option>
                </select>
              </div>
              <div class="col-md-6">
                <label>AC výstupná frekvencia</label>
                <select class="form-select" id="v98">
                  <option value="50">50 Hz</option>
                  <option value="60">60 Hz</option>
                </select>
              </div>
              <div class="col-md-6">
                <label>Rozsah vstupného napätia</label>
                <select class="form-select" id="v93">
                  <option value="0">Appliance</option>
                  <option value="1">UPS</option>
                </select>
              </div>
            </div>
          </div>

          <div class="text-center mt-5">
            <div class="d-flex flex-column flex-md-row gap-3 justify-content-center align-items-center">
              <button class="btn btn-outline-primary px-5 py-3 rounded-pill shadow-sm fw-medium custom-outline" 
                      onclick="readSettings()">
                <i class="fas fa-download me-2"></i>
                <span class="d-none d-sm-inline">Načítať nastavenia</span>
                <span class="d-inline d-sm-none">Načítať</span>
              </button>

              <button class="btn btn-primary px-5 py-3 rounded-pill shadow fw-bold" 
                      onclick="writeSettings()">
                <i class="fas fa-upload me-2"></i>
                <span class="d-none d-sm-inline">Zapísať nastavenia</span>
                <span class="d-inline d-sm-none">Zapísať</span>
              </button>

              <button class="btn btn-danger px-5 py-3 rounded-pill shadow-sm fw-medium" 
                      onclick="restartScript()">
                <i class="fas fa-redo-alt me-2"></i>
                <span class="d-none d-sm-inline">Reštart skriptu</span>
                <span class="d-inline d-sm-none">Reštart</span>
              </button>
            </div>

            <div class="mt-3 text-muted small opacity-75">
              Ovládanie meniča a skriptu Main.py
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

    <div id="distribucia" class="section">
      <div class="container">
        <h2 class="text-center mb-4 mt-4 text-primary fw-bold">Meranie distribúcie elektrickej energie</h2>

        <div class="row g-4" id="distribucia-content">
          <!-- Dynamicky vyplnené cez JS -->
        </div>

        <div class="card mb-4 mt-5 p-4 shadow">
          <h4 class="text-center text-primary">Spolu</h4>
          <div class="row text-center">
            <div class="col-md-6">
              <div class="text-muted">Celkový výkon</div>
              <div class="fs-3 fw-bold text-info" id="dist-total-power">-</div>
            </div>
            <div class="col-md-6">
              <div class="text-muted">Celková spotreba od resetu</div>
              <div class="fs-3 fw-bold text-warning" id="dist-total-energy">-</div>
            </div>
          </div>
        </div>
        <div class="text-center mb-4">
          <button class="btn btn-danger btn-lg px-5 py-3" onclick="resetPZEMEnergy()">
            <i class="fas fa-redo me-2"></i> Resetovať celkovú spotrebu
          </button>
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
    let lastLoaded = 'today';  // Default pri načítaní stránky: 'today'
    let data = {}, info = {};
    let charts = {};

    const themeToggle = document.getElementById('theme-toggle');
    const htmlEl = document.documentElement;

    function setTheme(theme) {
      htmlEl.setAttribute('data-bs-theme', theme);
      themeToggle.innerHTML = theme === 'dark' ? '<i class="fas fa-moon"></i>' : '<i class="fas fa-sun"></i>';
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
      if (id === 'fotovoltaika') showSubSection('home');
    }

    function showSubSection(id) {
      document.querySelectorAll('#fotovoltaika .sub-section').forEach(s => s.classList.remove('active'));
      document.getElementById('sub-' + id).classList.add('active');
      document.querySelectorAll('#fotovoltaika .nav-link').forEach(l => l.classList.remove('active'));
      document.querySelector(`#fotovoltaika .nav-link[onclick*="${id}"]`).classList.add('active');
      if (id === 'grafy') {
        // Načítaj podľa posledného vybraného rozsahu (bez event, aby sa nezmenil active button)
        if (lastLoaded === 'today') {
          loadToday(null);
        } else if (lastLoaded === 'custom') {
          loadCustom();
        } else {
          loadMinutes(lastLoaded, null);
        }
      }
      if (id === 'control') readSettings();
    }

    function updateHomeSummary() {
      const v65 = data['V65'];
      const v76 = data['V76'];
      const v75 = data['V75'];
      const v70 = data['V70'];

      document.getElementById('home-V65').textContent = v65 !== undefined ? v65 + ' W' : '-';
      document.getElementById('home-V76').textContent = v76 !== undefined ? v76 + ' W' : '-';
      document.getElementById('home-V75').textContent = v75 !== undefined ? (v75 > 0 ? '+' + v75 : v75) + ' W' : '-';
      document.getElementById('home-V70').textContent = v70 !== undefined ? v70 + ' %' : '-';
      document.getElementById('home-mode-value').textContent = data['V1'] || '-';
      document.getElementById('home-temp-value').textContent = data['V71'] || '-';
    }

    function updateInfoBar() {
      document.getElementById('indoor-temp-value').textContent = data['indoor_temp'] !== undefined ? parseFloat(data['indoor_temp']).toFixed(1) : '-';
      document.getElementById('indoor-hum-value').textContent = data['indoor_humidity'] !== undefined ? Math.round(data['indoor_humidity']) : '-';
      document.getElementById('outdoor-temp-value').textContent = data['outdoor_temp'] !== undefined ? parseFloat(data['outdoor_temp']).toFixed(1) : '-';
      document.getElementById('outdoor-hum-value').textContent = data['outdoor_humidity'] !== undefined ? Math.round(data['outdoor_humidity']) : '-';
    }

    function renderDetail() {
      const c = document.getElementById('detail-content');
      c.innerHTML = '';
      const groups = {
        "Fotovoltaika PV1": ["V76", "V73", "V72"],
        "Fotovoltaika PV2": ["V27", "V26", "V25"],
        "Batéria": ["V75", "V68", "V69", "V70", "V74"],
        "Inverter / Domácnosť": ["V65", "V64", "V66", "V62", "V63", "V60", "V61", "V67"],
        "Menič": ["V71", "V1"]
      };
      Object.keys(groups).forEach(groupName => {
        const pins = groups[groupName];
        const hasData = pins.some(pin => data[pin] !== undefined);
        if (!hasData) return;
        let groupHTML = `<div class="col-12 mb-4"><div class="detail-group"><h4>${groupName}</h4><div class="row justify-content-center">`;
        pins.forEach(pin => {
          if (data[pin] !== undefined) {
            const meta = info[pin] || [pin, "", ""];
            const displayValue = pin === "V1" ? data[pin] : data[pin];
            const unit = pin === "V71" ? " °C" : (meta[2] ? ' ' + meta[2] : '');
            groupHTML += `<div class="col-lg-3 col-md-4 col-sm-6 mb-2">
              <div class="card detail-card text-center">
                <i class="${meta[3] || "fas fa-circle"} fa-1x mb-1" style="color:var(--primary)"></i>
                <div class="text-muted small">${meta[0]}</div>
                <div class="key-value">${displayValue}${unit}</div>
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

    function updateDiagram() {
      const pv = parseFloat(data['V76']) || 0;
      const load = parseFloat(data['V65']) || 0;
      const batteryRaw = parseFloat(data['V75']) || 0;
      const gridPower = Math.abs(parseFloat(data['V15']) || 0);
      const soc = parseFloat(data['V70']) || 0;
      const mode = data['V1'] || '';
      const chargePriority = parseInt(data['V95']) || 0;

      // Texty v diagrame
      document.getElementById('pv-power').textContent = pv > 0 ? pv.toFixed(0) + ' W' : '0 W';
      document.getElementById('load-power').textContent = load > 0 ? load.toFixed(0) + ' W' : '0 W';
      document.getElementById('battery-power').textContent = Math.abs(batteryRaw) > 0 ? (batteryRaw >= 0 ? '+' : '') + batteryRaw.toFixed(0) + ' W' : '0 W';
      document.getElementById('battery-soc').textContent = soc.toFixed(0) + ' %';
      document.getElementById('grid-voltage').textContent = data['V60'] ? data['V60'] + ' V' : '-';
      document.getElementById('inverter-temp').textContent = data['V71'] ? data['V71'] + ' °C' : '-';

      // Zobrazenie režimu meniča
      document.getElementById('inverter-mode').textContent = data['V1'] || '-';

      // Home summary
      document.getElementById('home-V65').textContent = load > 0 ? load.toFixed(0) + ' W' : '-';
      document.getElementById('home-V76').textContent = pv > 0 ? pv.toFixed(0) + ' W' : '-';
      document.getElementById('home-V75').textContent = batteryRaw !== 0 ? (batteryRaw > 0 ? '+' : '') + batteryRaw.toFixed(0) + ' W' : '-';
      document.getElementById('home-V70').textContent = soc.toFixed(0) + ' %';

      // Ikona batérie
      const icon = document.getElementById('battery-icon');
      if (soc < 20) icon.className = 'fas fa-battery-empty fa-2x text-danger';
      else if (soc < 40) icon.className = 'fas fa-battery-quarter fa-2x text-warning';
      else if (soc < 60) icon.className = 'fas fa-battery-half fa-2x text-warning';
      else if (soc < 80) icon.className = 'fas fa-battery-three-quarters fa-2x text-success';
      else icon.className = 'fas fa-battery-full fa-2x text-success';

     
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
      lastLoaded = 'today';  // Pamätaj si tento rozsah
      const res = await fetch('/history/today');
      const h = await res.json();
      renderEnergy(h.energy);
      updateCharts(h);
    }

    async function loadMinutes(m, event) {
      if (event) {
        document.querySelectorAll('#time-buttons .btn').forEach(b => b.classList.remove('active'));
        event.target.classList.add('active');
      }
      lastLoaded = m;  // Pamätaj si tento rozsah (číslo minút)
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
      lastLoaded = 'custom';  // Pamätaj si custom
      const res = await fetch(`/history/custom?start=${from}&end=${to}`);
      const h = await res.json();
      renderEnergy(h.energy);
      updateCharts(h);
    }

    document.getElementById('toggle-custom').addEventListener('click', () => {
      const el = document.getElementById('custom-range');
      el.style.display = el.style.display === 'none' ? 'block' : 'none';
    });

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

    async function readSettings() {
      try {
        const res = await fetch('http://192.168.3.84:8002/control/read_settings');
        const json = await res.json();
        if (json.status === "success") {
          const s = json.settings;
          document.getElementById('v86').value = s.v86 || 52.0;
          document.getElementById('v87').value = s.v87 || 47.0;
          document.getElementById('v96').value = s.v96 || 50.0;
          document.getElementById('v88').value = s.v88 || 58.4;
          document.getElementById('v89').value = s.v89 || 58.4;
          document.getElementById('v91').value = s.v91 || 10;
          document.getElementById('v92').value = s.v92 || 50;
          document.getElementById('v90').value = s.v90 || 2;
          document.getElementById('v94').value = s.v94 || 1;
          document.getElementById('v95').value = s.v95 || 1;
          document.getElementById('v98').value = s.v98 || 50;
          document.getElementById('v93').value = s.v93 || 1;
          alert("✓ Nastavenia načítané z meniča");
        } else {
          alert("✗ " + json.message);
        }
      } catch (e) {
        alert("✗ Chyba spojenia s Main.py (port 8002)");
      }
    }

    async function quickSetPriority(value) {
      // Vizálne označenie, že sa niečo deje
      const buttons = document.querySelectorAll('#sub-home button[onclick^="quickSetPriority"]');
      buttons.forEach(b => b.disabled = true);

      const settings = {
        v94: parseInt(value)
      };

      try {
        const res = await fetch('http://192.168.3.84:8002/control/write_settings', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(settings)
        });
        const json = await res.json();

        if (json.status === "success") {
          // Krátky feedback
          document.getElementById('status').textContent = `Priority zmenená: ${value === 0 ? 'Distribúcia' : value === 1 ? 'Solar' : 'Batéria'} ✓`;
          // Aktualizujeme lokálne dáta (ak máme V1 alebo iný indikátor režimu)
          data['V94'] = value;
        } else {
          document.getElementById('status').textContent = '✗ Chyba pri zmene priority';
        }
      } catch (e) {
        document.getElementById('status').textContent = '✗ Spojenie s Main.py zlyhalo';
      }

      // Po chvíli povolíme tlačidlá späť
      setTimeout(() => {
        buttons.forEach(b => b.disabled = false);
      }, 2000);
    }

    async function writeSettings() {
      if (!confirm("Naozaj chceš zapísať tieto nastavenia do meniča?")) return;

      const settings = {
        v86: parseFloat(document.getElementById('v86').value),
        v87: parseFloat(document.getElementById('v87').value),
        v96: parseFloat(document.getElementById('v96').value),
        v88: parseFloat(document.getElementById('v88').value),
        v89: parseFloat(document.getElementById('v89').value),
        v91: parseInt(document.getElementById('v91').value),
        v92: parseInt(document.getElementById('v92').value),
        v90: parseInt(document.getElementById('v90').value),
        v94: parseInt(document.getElementById('v94').value),
        v95: parseInt(document.getElementById('v95').value),
        v98: parseInt(document.getElementById('v98').value),
        v93: parseInt(document.getElementById('v93').value),
      };

      try {
        const res = await fetch('http://192.168.3.84:8002/control/write_settings', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(settings)
        });
        const json = await res.json();
        alert(json.status === "success" ? "✓ " + json.message : "✗ " + json.message);

        if (json.status === "success") {
          setTimeout(() => readSettings(), 3000);
        }
      } catch (e) {
        alert("✗ Chyba spojenia s Main.py");
      }
    }

    async function restartScript() {
      if (!confirm("Naozaj reštartovať Main.py?")) return;
      try {
        const res = await fetch('http://192.168.3.84:8002/control/restart', {method: 'POST'});
        const json = await res.json();
        alert(json.status === "success" ? "✓ " + json.message : "✗ Chyba");
      } catch (e) {
        alert("✗ Chyba spojenia s Main.py");
      }
    }

    function updateHomeDistribucia() {
      const l1 = data['PZEM_L1_power'] || 0;
      const l2 = data['PZEM_L2_power'] || 0;
      const l3 = data['PZEM_L3_power'] || 0;
      const total = data['PZEM_total_power'] || 0;
      const energy = data['PZEM_total_energy'] || 0;

      document.getElementById('home-L1-power').textContent = l1.toFixed(0) + ' W';
      document.getElementById('home-L2-power').textContent = l2.toFixed(0) + ' W';
      document.getElementById('home-L3-power').textContent = l3.toFixed(0) + ' W';
      document.getElementById('home-total-power').textContent = total.toFixed(0) + ' W';
      document.getElementById('home-total-energy').textContent = energy.toFixed(3) + ' kWh';
    }

    function renderDistribucia() {
      const container = document.getElementById('distribucia-content');
      container.innerHTML = '';

      const faze = ['L1', 'L2', 'L3'];
      faze.forEach(f => {
        const base = `PZEM_${f}`;
        const power = data[base + '_power'] || 0;
        const voltage = data[base + '_voltage'] || 0;
        const current = data[base + '_current'] || 0;
        const energy = data[base + '_energy'] || 0;

        container.innerHTML += `
          <div class="col-md-4 col-lg-4">
            <div class="card shadow text-center p-4">
              <h4 class="text-primary mb-4">Fáza ${f}</h4>
              
              <!-- Prvý riadok: Napätie | Prúd | Výkon -->
              <div class="row g-3 mb-4">
                <div class="col-4">
                  <div class="text-muted small">Napätie</div>
                  <div class="fs-4 fw-bold text-info">${voltage.toFixed(1)}<small class="fs-6"> V</small></div>
                </div>
                <div class="col-4">
                  <div class="text-muted small">Prúd</div>
                  <div class="fs-4 fw-bold text-warning">${current.toFixed(2)}<small class="fs-6"> A</small></div>
                </div>
                <div class="col-4">
                  <div class="text-muted small">Výkon</div>
                  <div class="fs-4 fw-bold text-danger">${power.toFixed(0)}<small class="fs-6"> W</small></div>
                </div>
              </div>

              <!-- Druhý riadok: Spotreba od resetu -->
              <div class="pt-3 border-top">
                <div class="text-muted small mb-1">Spotreba od resetu</div>
                <div class="fs-3 fw-bold text-success">${energy.toFixed(3)} kWh</div>
              </div>
            </div>
          </div>`;
      });

      // Súčty dole
      document.getElementById('dist-total-power').textContent = 
        (data['PZEM_total_power'] || 0).toFixed(0) + ' W';
      document.getElementById('dist-total-energy').textContent = 
        (data['PZEM_total_energy'] || 0).toFixed(3) + ' kWh';
    }

    // Reset cez Blynk V11 – simulácia (ak nechceš priamo volať ESP)
    async function resetPZEMEnergy() {
      if (!confirm("Naozaj resetovať celkovú spotrebu na PZEM meraniach?")) return;
      // Tu môžeš buď poslať na Blynk V11, alebo priamo na ESP ak máš endpoint
      alert("Reset odoslaný (funguje cez Blynk tlačidlo V11)");
      // Alebo priamo:
      // await fetch('http://IP_PZEM_ESP/blynk?V11=1');
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
        updateDiagram();
        updateHomeDistribucia();
          if (document.getElementById('distribucia')?.classList.contains('active')) {
            renderDistribucia();
          }
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
    return render_template_string(HTML_TEMPLATE)

if __name__ == "__main__":
    print("iHome dashboard beží na http://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)