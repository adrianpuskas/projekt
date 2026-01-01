#!/usr/bin/env python3
"""
local_server.py

Jednosúborový lokálny "mini-Blynk" dashboard.
Spustenie: python3 local_server.py
Otvor v prehliadači: http://<tvoja_IP>:8000

POST /write
    JSON body: {"pin": "V73", "value": 158.2}

GET /data       -> vsetky ulozene hodnoty
GET /vpin_info  -> mapovanie Vpin -> (name, section, unit)
GET /           -> HTML dashboard (auto-refresh 0.5s)
"""

from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
import threading

app = Flask(__name__)

# ----------------------------
# VPIN mapovanie: pin -> (názov, sekcia, jednotka)
# ----------------------------
VPINS = {
    # GRID / AC monitoring (3f)
    "V30": ("L1 Voltage", "Grid (3F)", "V"),
    "V31": ("L1 Current", "Grid (3F)", "A"),
    "V32": ("L1 Power", "Grid (3F)", "W"),
    "V33": ("L1 Energy", "Grid (3F)", "kWh"),
    "V34": ("L1 Frequency", "Grid (3F)", "Hz"),
    "V35": ("L1 PF", "Grid (3F)", ""),

    "V40": ("L2 Voltage", "Grid (3F)", "V"),
    "V41": ("L2 Current", "Grid (3F)", "A"),
    "V42": ("L2 Power", "Grid (3F)", "W"),
    "V43": ("L2 Energy", "Grid (3F)", "kWh"),
    "V44": ("L2 Frequency", "Grid (3F)", "Hz"),
    "V45": ("L2 PF", "Grid (3F)", ""),

    "V50": ("L3 Voltage", "Grid (3F)", "V"),
    "V51": ("L3 Current", "Grid (3F)", "A"),
    "V52": ("L3 Power", "Grid (3F)", "W"),
    "V53": ("L3 Energy", "Grid (3F)", "kWh"),
    "V54": ("L3 Frequency", "Grid (3F)", "Hz"),
    "V55": ("L3 PF", "Grid (3F)", ""),

    "V12": ("Celkova spotreba energie 3F", "Grid (3F)", "kWh"),
    "V15": ("Súčet 3F výkonov", "Grid (3F)", "W"),

    # INVERTER / QPIGS
    "V60": ("QPIGS_B_GRID_VOLTAGE", "Inverter", "V"),
    "V61": ("QPIGS_C_GRID_FREQUENCY", "Inverter", "Hz"),
    "V62": ("QPIGS_D_OUT_VOLTAGE", "Inverter", "V"),
    "V63": ("QPIGS_E_OUT_FREQUENCY", "Inverter", "Hz"),
    "V64": ("QPIGS_F_OUT_APPARENT_POWER", "Inverter", "VA"),
    "V65": ("QPIGS_G_OUT_ACTIVE_POWER", "Inverter", "W"),
    "V66": ("QPIGS_H_OUT_LOAD_PERCENTAGE", "Inverter", "%"),
    "V67": ("QPIGS_I_BUS_VOLTAGE", "Inverter", "V"),
    "V68": ("QPIGS_J_BATTERY_VOLTAGE", "Battery", "V"),
    "V69": ("QPIGS_K_BATTERY_CURRENT", "Battery", "A"),
    "V70": ("QPIGS_O_BATTERY_CAPACITY", "Battery", "%"),
    "V71": ("QPIGS_T_INVERTER_TEMPERATURE", "Inverter", "°C"),

    "V72": ("QPIGS_R_PV_CURRENT_FOR_BATTERY", "PV", "A"),
    "V73": ("QPIGS_T_PV_VOLTAGE", "PV", "V"),
    "V74": ("QPIGS_U_BATT_VOLTAGE_FROM_SCC", "Battery", "V"),
    "V75": ("QPIGS_W_BATTERY_POWER", "Battery", "W"),
    "V76": ("QPIGS_PV_WATTS", "PV", "W"),

    # PV2
    "V25": ("QPIGS2_R_PV2_CURRENT_FOR_BATTERY", "PV2", "A"),
    "V26": ("QPIGS2_T_PV2_VOLTAGE", "PV2", "V"),
    "V27": ("QPIGS2_PV2_WATTS", "PV2", "W"),

    # PZEM / other sensors
    "V10": ("pzem1fStringData", "PZEM 1F", ""),
    "V11": ("Reset PZEM 3f", "PZEM 3F", ""),
    "V99": ("Indikator_zapis_posuvace", "Controls", ""),

    # Controls / Buttons
    "V1": ("DEVICE_MODE", "Controls", ""),
    "V2": ("Button_Read_Inverter_Data", "Controls", ""),
    "V3": ("Button_Write_Data_To_Inverter", "Controls", ""),
    "V7": ("Vykon Bojlera", "Controls", "%"),
    "V8": ("Automatika_Ohrev", "Controls", ""),

    # Sensors
    "V4": ("Vonkajsia_teplota", "Sensors", "°C"),
    "V9": ("teplotaTUV", "Sensors", "°C"),
    "V101": ("VyrobaSpotrebaString", "Sensors", ""),

    # BMS / info
    "V13": ("BMS_DATA", "BMS", ""),

    # Settings
    "V5": ("Set_Type_Battery", "Settings", ""),
    "V6": ("rychle_nastavenie_vystupu", "Settings", ""),
    "V102": ("NastavenieRoka", "Settings", ""),
    "V103": ("NastavenieMesiaca", "Settings", ""),
    "V104": ("NastavenieDna", "Settings", ""),

    # extras (unknowns will still be shown)
    "V110": ("Reset_sciptu", "Controls", ""),
    "V20": ("Prebytky 1", "Controls", ""),
    "V0": ("tlacidlo_zapis_posuvace", "Controls", ""),
    "V77": ("QPIRI_FLAGS_OverloadBypass", "Flags", ""),
    "V79": ("QPIRI_FLAGS_OverloadRestart", "Flags", ""),
    "V80": ("QPIRI_FLAGS_OverTemperatureRestart", "Flags", ""),
    "V81": ("QPIRI_FLAGS_Backlight", "Flags", ""),
    "V83": ("QPIRI_FLAGS_SilenceBuzzer", "Flags", ""),
    "V85": ("QPIRI_FLAGS_AlarmOnPrimaryInterrupt", "Flags", ""),
    "V86": ("QPIRI_Batt_recharge_voltage", "Battery settings", "V"),
    "V87": ("QPIRI_under_voltage", "Battery settings", "V"),
    "V88": ("QPIRI_Batt_bulk_voltage", "Battery settings", "V"),
    "V89": ("QPIRI_Batt_float_voltage", "Battery settings", "V"),
    # ... môžeš doplniť ďalšie podľa potreby
}

# ----------------------------
# Úložisko: aktuálne hodnoty + timestamp
# local_data: { "V73": {"value": 158.2, "ts": "2025-11-24T12:34:56"} }
# ----------------------------
local_data = {}

data_lock = threading.Lock()


# ----------------------------
# Pomocné funkcie
# ----------------------------
def _store_value(pin: str, value):
    with data_lock:
        local_data[pin] = {"value": value, "ts": datetime.utcnow().isoformat()}


def _get_snapshot():
    with data_lock:
        # vrátime iba pin -> value (zjednodušene pre front-end)
        return {pin: info["value"] for pin, info in local_data.items()}


# ----------------------------
# API endpoints
# ----------------------------

@app.route('/write', methods=['POST'])
def write_pin():
    """
    POST JSON: {"pin": "V73", "value": 158.2}
    (ak príde 'pin' bez prefixu V, nevadí - doplníme)
    """
    data = request.get_json(silent=True) or {}
    pin = data.get("pin")
    value = data.get("value")

    if pin is None:
        return jsonify({"status": "error", "message": "missing 'pin' in json"}), 400

    # ak užívateľ poslal len číslo (napr. "73" alebo 73) -> upravíme na V73
    if isinstance(pin, int):
        pin = f"V{pin}"
    elif isinstance(pin, str) and not pin.upper().startswith("V"):
        pin = "V" + pin

    # uložíme
    _store_value(pin.upper(), value)
    return jsonify({"status": "ok", "pin": pin.upper(), "value": value})


@app.route('/data', methods=['GET'])
def get_all():
    """Vráti iba hodnoty pinov vo forme { "V73": 158.2, ... }"""
    return jsonify(_get_snapshot())


@app.route('/vpin_info', methods=['GET'])
def vpin_info():
    """Vráti mapovanie VPINS (name, section, unit)"""
    return jsonify(VPINS)


# ----------------------------
# HTML dashboard (single-file template)
# ----------------------------
HTML_TEMPLATE = r"""
<!doctype html>
<html lang="sk">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Lokálny Blynk - Dashboard</title>
  <style>
    :root {
      --bg: #0d1117;
      --card: #0f1720;
      --muted: #9aa4b2;
      --accent: #00c853;
      --accent2: #40c4ff;
    }
    body { margin:0; font-family: Inter, Roboto, Arial; background: var(--bg); color: #e6eef6; }
    header { padding: 18px 24px; border-bottom: 1px solid rgba(255,255,255,0.03); display:flex; align-items:center; gap:16px; }
    header h1 { margin:0; font-size:20px; color:var(--accent); letter-spacing:0.2px; }
    header .meta { color:var(--muted); font-size:13px; }
    main { padding:18px; display:flex; gap:18px; flex-wrap:wrap; }
    .section { min-width:260px; max-width:420px; background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); border-radius:10px; padding:12px; border:1px solid rgba(255,255,255,0.03); }
    .section h2 { margin:0 0 8px 0; font-size:15px; color:var(--accent2); }
    .pin-card { background:var(--card); padding:10px; border-radius:8px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; gap:8px; border-left:4px solid rgba(0,200,83,0.12); }
    .pin-left { display:flex; flex-direction:column; }
    .pin-name { font-size:13px; color:#dbe9f7; font-weight:600; }
    .pin-pin { font-size:12px; color:var(--muted); }
    .pin-value { font-size:18px; font-weight:700; color:var(--accent2); min-width:120px; text-align:right; }
    .ts { font-size:11px; color:var(--muted); margin-top:3px; }
    footer { padding:12px 18px; color:var(--muted); font-size:13px; border-top:1px solid rgba(255,255,255,0.02); }
    .no-data { color:var(--muted); padding:18px; }
    @media (max-width:900px) {
      main { flex-direction:column; }
      .section { max-width:100%; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Lokálny Blynk — Dashboard</h1>
      <div class="meta">Aktualizuje sa automaticky každých 0.5 s · Lokálne ukladanie hodnôt</div>
    </div>
  </header>

  <main id="main">
    <div class="no-data">Načítavam dáta...</div>
  </main>

  <footer>
    <div id="status">Status: ? Načítavam...</div>
  </footer>

<script>
const REFRESH_MS = 500;
let vpinInfo = {};
let lastSnapshot = {};

function niceFormat(value, unit) {
    if (value === null || value === undefined) return "-";
    // ak je číslo, pekne na 1-3 desatinné miesta podľa veľkosti
    if (!isNaN(value) && value !== "") {
        let num = Number(value);
        // rozhodni format
        let digits = Math.abs(num) < 10 ? 2 : (Math.abs(num) < 100 ? 1 : 0);
        // použij locale pre čiarku bodka podľa prehliadača
        return num.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: digits }) + (unit ? " " + unit : "");
    }
    return String(value) + (unit ? " " + unit : "");
}

function render(snapshot, info) {
    const main = document.getElementById("main");
    main.innerHTML = "";

    // zložíme pins do sekcií
    let sections = {};
    for (let pin in snapshot) {
        let value = snapshot[pin];
        let meta = info[pin] || null;
        let name = meta ? meta[0] : ("Neznámy pin " + pin);
        let section = meta ? meta[1] : "Other";
        let unit = meta ? meta[2] : "";

        if (!sections[section]) sections[section] = [];
        sections[section].push({pin, name, unit, value});
    }

    // poradie sekcií (ak sú v mape)
    const preferredOrder = ["PV","PV2","Battery","Inverter","Grid (3F)","Grid","PZEM 1F","PZEM 3F","Sensors","Controls","Flags","Settings","Other"];
    const orderedSections = Object.keys(sections).sort((a,b)=>{
        let ai = preferredOrder.indexOf(a);
        let bi = preferredOrder.indexOf(b);
        if (ai === -1) ai = 999;
        if (bi === -1) bi = 999;
        if (ai === bi) return a.localeCompare(b);
        return ai - bi;
    });

    // ak nie je žiadne data
    if (orderedSections.length === 0) {
        main.innerHTML = '<div class="no-data">Žiadne lokálne uložené hodnoty (čaká sa na POST /write)</div>';
        return;
    }

    for (let sec of orderedSections) {
        const secDiv = document.createElement("div");
        secDiv.className = "section";
        secDiv.innerHTML = `<h2>${sec}</h2>`;
        // zorad pins v sekcii podľa názvu
        sections[sec].sort((a,b)=>a.name.localeCompare(b.name));
        for (let p of sections[sec]) {
            // vytvor element
            const card = document.createElement("div");
            card.className = "pin-card";
            const left = document.createElement("div");
            left.className = "pin-left";
            left.innerHTML = `<div class="pin-name">${p.name}</div><div class="pin-pin">(${p.pin})</div>`;

            const right = document.createElement("div");
            right.style.display = "flex";
            right.style.flexDirection = "column";
            right.style.alignItems = "flex-end";
            right.innerHTML = `<div class="pin-value">${niceFormat(p.value, p.unit)}</div><div class="ts" id="ts_${p.pin}"></div>`;

            card.appendChild(left);
            card.appendChild(right);
            secDiv.appendChild(card);
        }
        main.appendChild(secDiv);
    }
}

async function fetchData() {
    try {
        const [r1, r2] = await Promise.all([fetch('/data'), fetch('/vpin_info')]);
        if (!r1.ok || !r2.ok) throw new Error("Network error");
        const snapshot = await r1.json();
        const info = await r2.json();
        vpinInfo = info;
        lastSnapshot = snapshot;
        render(snapshot, info);
        const status = document.getElementById("status");
        status.textContent = "Status: ? Online · " + new Date().toLocaleTimeString();
    } catch (e) {
        // pri chybe len updatni status (server bezi lokalne; ak nie je dostupny, zobraz chybu)
        document.getElementById("status").textContent = "Status: ?? Chyba pri získavaní dát (" + e.message + ")";
    }
}

// poll
fetchData();
setInterval(fetchData, REFRESH_MS);
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


# ----------------------------
# Spustenie
# ----------------------------
if __name__ == "__main__":
    # spustíme debug=false pre produkčné použitie
    print("Starting local_server on http://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000, debug=False)
