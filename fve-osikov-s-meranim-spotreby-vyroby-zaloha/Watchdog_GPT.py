import os
import subprocess
import time
import threading
import globals as gp
import sys
from datetime import datetime
from blynkSender import wait_for_internet_connection, blynk_write

stop_event = threading.Event()
blynk_initialized = False  # Globálna premenná na sledovanie inicializácie Blynku

def initialize_blynk():
    global blynk_initialized
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Čakám na pripojenie k internetu...", flush=True)
    wait_for_internet_connection()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Pripojenie obnovené!", flush=True)
    try:
        blynk_write(3, 0)
        blynk_write(2, 0)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Blynk inicializovaný.", flush=True)
        blynk_initialized = True
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Chyba pri inicializácii Blynku: {e}", flush=True)
        blynk_initialized = False

def main_process():
    global blynk_initialized
    while not stop_event.is_set():
        initialize_blynk()  # Inicializácia Blynku pred každým spustením Main.py

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Spúšťam Main.py...", flush=True)
        env = os.environ.copy()
        env['PYTHONPATH'] = '/usr/lib/python3/dist-packages/RPi.GPIO'
        try:
            proc = subprocess.Popen([sys.executable, "Main.py"],
                                    stdin=subprocess.PIPE, env=env)
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Chyba pri spúšťaní Main.py: {e}", flush=True)
            time.sleep(5)  # Počkaj pred ďalším pokusom
            continue

        while not stop_event.is_set():
            if proc.poll() is not None:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Main.py ukončený s kódom {proc.returncode}", flush=True)
                try:
                    gp.closePort()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sériový port zatvorený pred reštartom.", flush=True)
                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Chyba pri zatváraní portu pred reštartom: {e}", flush=True)
                blynk_initialized = False  # Reset Blynk inicializácie pre nový pokus
                break  # Vyskočí z vnútornej slučky a znova spustí Main.py
            try:
                proc.stdin.write(b'\x00')
                proc.stdin.flush()
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Chyba pri komunikácii s Main.py: {e}", flush=True)
                try:
                    gp.closePort()
                    proc.terminate()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Main.py ukončený.", flush=True)
                except Exception as e2:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Chyba pri ukončení Main.py: {e2}", flush=True)
                blynk_initialized = False  # Reset Blynk inicializácie
                break  # Vyskočí z vnútornej slučky a znova spustí Main.py
            time.sleep(1)

def start_threads():
    threads = []
    thread_main = threading.Thread(target=main_process, name="MainProcess")
    thread_main.start()
    threads.append(thread_main)
    return threads

try:
    threads = start_threads()
    while not stop_event.is_set():
        time.sleep(0.5)
except KeyboardInterrupt:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Keyboard interrupt detekovaný, ukončujem skript...", flush=True)
    stop_event.set()
    try:
        gp.closePort()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Sériový port zatvorený.", flush=True)
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Chyba pri zatváraní portu: {e}", flush=True)
finally:
    for thread in threads:
        thread.join(timeout=2.0)  # Čakáme maximálne 2 sekundy na ukončenie vlákien
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Program ukončený.", flush=True)
    sys.exit(0)
