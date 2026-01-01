import time
import sys
import datetime
import queue
import threading
import globals as gp
from globals import initializePort, closePort
import get_function as get
import set_function as set
from blynkSender import blynk_write, blynk_read

# === PRIAME OVLÁDANIE BMS cez lokálny HTTP server (port 8001) ===
from flask import Flask, request, jsonify
from flask_cors import CORS
import JKBMS as BMS

bms_control_app = Flask(__name__)
CORS(bms_control_app)

@bms_control_app.route('/bms/control', methods=['POST'])
def bms_direct_control():
    print(f"\n--- BMS príkaz prijatý z {request.remote_addr} ---")
    try:
        data = request.get_json(force=True)
        if data is None:
            print("Chyba: Žiadne JSON dáta")
            return jsonify({"status": "error", "message": "Žiadne dáta"}), 400
            
        action = data.get('action')
        print(f"Prijatá akcia: {action}")

        if action == 'charge_on':
            BMS.onChargeCommandBMS()
            print(">>> Nabíjanie ZAPNUTÉ")
            return jsonify({"status": "success", "message": "Nabíjanie ZAPNUTÉ"})
        elif action == 'charge_off':
            BMS.offChargeCommandBMS()
            print(">>> Nabíjanie VYPNUTÉ")
            return jsonify({"status": "success", "message": "Nabíjanie VYPNUTÉ"})
        elif action == 'discharge_on':
            BMS.onDischargeCommandBMS()
            print(">>> Vybíjanie ZAPNUTÉ")
            return jsonify({"status": "success", "message": "Vybíjanie ZAPNUTÉ"})
        elif action == 'discharge_off':
            BMS.offDischargeCommandBMS()
            print(">>> Vybíjanie VYPNUTÉ")
            return jsonify({"status": "success", "message": "Vybíjanie VYPNUTÉ"})
        else:
            print(f"Neznáma akcia: {action}")
            return jsonify({"status": "error", "message": "Neznáma akcia"}), 400
            
    except Exception as e:
        print(f"CHYBA v BMS control: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

def run_bms_control_server():
    print("BMS priame ovládanie beží na http://192.168.3.84:8001/bms/control (s CORS)")
    bms_control_app.run(host='0.0.0.0', port=8001, debug=False, use_reloader=False, threaded=True)

def start_bms_control_server():
    threading.Thread(target=run_bms_control_server, daemon=True).start()

# === PRIAME OVLÁDANIE MENIČA z dashboardu (port 8002) ===
control_app = Flask(__name__)
CORS(control_app)

# Globálna premenná na uloženie posledných načítaných nastavení
current_settings = {}

@control_app.route('/control/read_settings', methods=['GET'])
def api_read_settings():
    try:
        settings = get.nastaveneData()  # vráti dict
        if settings is None:
            settings = {}
        return jsonify({
            "status": "success",
            "settings": settings,
            "message": "Nastavenia načítané z meniča"
        })
    except Exception as e:
        print(f"CHYBA v read_settings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@control_app.route('/control/write_settings', methods=['POST'])
def api_write_settings():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Žiadne dáta"}), 400

        print(">>> Prijaté nastavenia z dashboardu:", data)

        # Načítame aktuálny stav z meniča
        response = gp.run_command_get(b'QPIRI')
        if response is None:
            return jsonify({"status": "error", "message": "Chyba pri QPIRI"}), 500

        values = response.strip().split()
        decoded = [v.decode('latin-1').lstrip("b'(").rstrip("'") for v in values]

        response2 = gp.run_command_get(b'QDI')
        decoded2 = []
        if response2:
            values2 = response2.strip().split()
            decoded2 = [v.decode('latin-1').lstrip("b'(").rstrip("'") for v in values2]

        changes = []

        # Pomocná funkcia na odoslanie príkazu
        def send_command(command, value=None):
            try:
                if value is not None:
                    resp = gp.run_command_set(command, str(value))
                else:
                    resp = gp.run_command_set(command)
                if b'ACK' in resp:
                    print(f"\t✓ Úspešne nastavené: {command.decode()} {value or ''}")
                    return True
                else:
                    print(f"\t✗ Zlyhalo: {command.decode()} {value or ''} -> {resp}")
                    return False
            except Exception as e:
                print(f"\tChyba pri odosielaní {command.decode()}: {e}")
                return False

        # v96 - Battery re-charge voltage (PBCV)
        if "v96" in data and abs(float(decoded[8]) - float(data["v96"])) > 0.01:
            if send_command(b'PBCV', data["v96"]):
                changes.append("v96")

        # v87 - Battery under voltage (PSDV)
        if "v87" in data and abs(float(decoded[9]) - float(data["v87"])) > 0.01:
            if send_command(b'PSDV', data["v87"]):
                changes.append("v87")

        # v88 - Bulk (PCVV)
        if "v88" in data and abs(float(decoded[10]) - float(data["v88"])) > 0.01:
            if send_command(b'PCVV', data["v88"]):
                changes.append("v88")

        # v89 - Float (PBFT)
        if "v89" in data and abs(float(decoded[11]) - float(data["v89"])) > 0.01:
            if send_command(b'PBFT', data["v89"]):
                changes.append("v89")

        # v90 - Battery type (PBT)
        if "v90" in data and int(decoded[12]) != int(data["v90"]):
            value = f"0{data['v90']}"
            if send_command(b'PBT', value):
                changes.append("v90")

        # v91 - Max AC charging (MUCHGC)
        if "v91" in data and int(decoded[13]) != int(data["v91"]):
            value = f"{data['v91']:03d}"  # 010, 020, atď.
            if send_command(b'MUCHGC', value):
                changes.append("v91")

        # v92 - Max charging (MNCHGC)
        if "v92" in data and int(decoded[14]) != int(data["v92"]):
            value = f"{data['v92']:03d}"  # 010, 020, ..., 090
            if send_command(b'MNCHGC', value):
                changes.append("v92")

        # v93 - Input range (PGR)
        if "v93" in data and int(decoded[15]) != int(data["v93"]):
            if send_command(b'PGR', f"0{data['v93']}"):
                changes.append("v93")

        # v94 - Output source priority
        if "v94" in data:
            desired = int(data["v94"])

            if desired == 0:  # Utility First
                print("-> Nastavujem Output source priority na Utility First (POP00)")
                if send_command(b'POP0', '0'):
                    changes.append("v94")

            elif desired == 1:  # Solar First
                print("-> Nastavujem Output source priority na Solar First (POP01)")
                if send_command(b'POP0', '1'):
                    changes.append("v94")

            elif desired == 2:  # SBU priority
                print("-> Nastavujem Output source priority na SBU priority (POP02)")
                try:
                    resp = gp.run_command_set_POP02()
                    if b'ACK' in resp:
                        print("\t✓ Úspešne nastavené: SBU priority (POP02)")
                        changes.append("v94")
                    else:
                        print(f"\t✗ Zlyhalo SBU priority: {resp}")
                except Exception as e:
                    print(f"\tChyba pri POP02: {e}")

        # v95 - Charger priority (PCP)
        if "v95" in data and int(decoded[17]) != int(data["v95"]):
            if send_command(b'PCP', f"0{data['v95']}"):
                changes.append("v95")

        # v86 - Battery re-discharge (PBDV)
        if "v86" in data and abs(float(decoded[22]) - float(data["v86"])) > 0.01:
            if send_command(b'PBDV', data["v86"]):
                changes.append("v86")

        # v98 - Frequency (F)
        if "v98" in data and len(decoded2) > 1 and abs(float(decoded2[1]) - float(data["v98"])) > 0.01:
            if send_command(b'F', int(data["v98"])):
                changes.append("v98")

        if changes:
            return jsonify({"status": "success", "message": f"Zapísané: {', '.join(changes)}"})
        else:
            return jsonify({"status": "success", "message": "Žiadne zmeny potrebné"})

    except Exception as e:
        print(f"CHYBA pri zápise: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@control_app.route('/control/restart', methods=['POST'])
def api_restart():
    print(">>> REŠTART SKRIPTU spustený z dashboardu")
    threading.Thread(target=restart_script).start()
    return jsonify({"status": "success", "message": "Reštart spustený"})

# Spustenie API vo vlákne
def start_control_api():
    print("API pre dashboard beží na http://192.168.3.84:8002/control/...")
    control_app.run(host='0.0.0.0', port=8002, debug=False, use_reloader=False, threaded=True)

threading.Thread(target=start_control_api, daemon=True).start()

# === KONIEC API ===

stop_event = threading.Event()
exception_queue = queue.Queue()

def restart_script():
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\t-> ZAČÍNAM REŠTART PROGRAMU ...", flush=True)
    try:
        closePort()
        print(f"\tSériový port zatvorený.", flush=True)
    except Exception as e:
        print(f"\tChyba pri zatváraní portu: \n{e}\n", flush=True)
    try:
        blynk_write(110, 0)  # Reset tlačidla V110
        print(f"\tV110 resetované na 0.", flush=True)
    except Exception as e:
        print(f"\tChyba pri odoslaní do Blynku (restart): \n{e}\n", flush=True)
    print(f"\t...Prebieha reštart...", flush=True)
    stop_event.set()

def data_collection_thread():
    while not stop_event.is_set():
        start_time = time.time()
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tZber dát...", flush=True)
        try:
            get.aktualneData()
        except Exception as e:
            print(f"\tChyba v data_collection_thread: \n{e}\n", flush=True)
            try:
                closePort()
                time.sleep(3)
                initializePort()
            except Exception as e2:
                print(f"\tChyba pri reinicializácii portu: \n{e2}\n", flush=True)
                time.sleep(5)
        elapsed_time = time.time() - start_time
        sleep_time = max(0, 5 - elapsed_time)
        time.sleep(sleep_time)

def monitoring():
    print(f"\n\t...Monitorovanie...", flush=True)
    try:
        if blynk_read("v110") == '1':
            restart_script()
        
        if blynk_read("v6") != blynk_read("v94"):
            blynk_write(94, blynk_read("v6"))
            try:
                set.zmen_nastavenia()
                print(f"\t!! Nastavujem prioritu výstupu cez zrýchlené nastavenie !!", flush=True)
            except Exception as e:
                print(f"\tChyba pri zmene nastavení: \n{e}\n", flush=True)
            time.sleep(2)

        if blynk_read("v2") == '1':
            print(f"\t-> Aktualizujem nastavené dáta ...", flush=True)
            try:
                set.nastavene_hodnoty_update()
            except Exception as e:
                print(f"\tChyba pri aktualizácii nastavení: \n{e}\n", flush=True)
        
        if blynk_read("v3") == '1':
            print(f"\t-> Ukladám nastavenia ...", flush=True)
            try:
                set.zmen_nastavenia()
                while True:
                    blynk_write(3, 0)
                    if blynk_read("v3") == '0':
                        break
                    blynk_write(3, 0)
                    time.sleep(1)
                get.nastaveneData()
            except Exception as e:
                print(f"\tChyba pri ukladaní nastavení: \n{e}\n", flush=True)
        
        try:
            get.mode_zariadenia()
            get.bmsControl()
        except Exception as e:
            print(f"\tChyba pri volaní mode_zariadenia: \n{e}\n", flush=True)
            try:
                closePort()
                time.sleep(2)
                initializePort()
            except Exception as e2:
                print(f"\tChyba pri reinicializácii portu: \n{e2}\n", flush=True)
                time.sleep(2)
    except Exception as e:
        print(f"\tChyba v monitoring: {e}", flush=True)
        restart_script()
        try:
            closePort()
            time.sleep(2)
            initializePort()
        except Exception as e2:
            print(f"\tChyba pri reinicializácii portu: \n{e2}\n", flush=True)
            time.sleep(2)

def main():
    try:
        initializePort()
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Inicializujem port.", flush=True)

        # Spustenie serverov
        start_bms_control_server()

        # Spustenie API pre meniča priamo
        threading.Thread(target=control_app.run, kwargs={
            'host': '0.0.0.0',
            'port': 8002,
            'debug': False,
            'use_reloader': False,
            'threaded': True
        }, daemon=True).start()
        print("API pre ovládanie meniča beží na http://192.168.3.84:8002")

    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Chyba pri inicializácii portu: \n\t{e}\n", flush=True)
        sys.exit(1)

    data_thread = threading.Thread(target=data_collection_thread)
    data_thread.start()

    try:
        while not stop_event.is_set():
            monitoring()
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tKeyboard interrupt detekovaný, ukončujem všetky vlákna...", flush=True)
        stop_event.set()
    finally:
        data_thread.join(timeout=2.0)
        try:
            closePort()
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tSériový port zatvorený pri ukončení.", flush=True)
        except Exception as e:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tChyba pri zatváraní portu: {e}", flush=True)
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tMain.py ukončený.", flush=True)

if __name__ == "__main__":
    main()