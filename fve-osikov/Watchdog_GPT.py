import os
import subprocess
import time
import threading
import globals as gp
import sys
from blynkSender import wait_for_internet_connection


stop_event = threading.Event()  # Stop event for graceful shutdown

# Funkcia monitoruje vlákna a kontroluje ich stav.
def monitor_threads(threads):
    """Funkcia monitoruje vlákna a kontroluje ich stav."""
    while not stop_event.is_set():
        for thread in threads:
            if not thread.is_alive():
                print(f"Vlákno {thread.name} prestalo fungovať.")
                gp.closePort()
                stop_event.set()  # Zastavíme všetky vlákna
                os.execv(__file__, ['pytcd F    hon'] + sys.argv)  # Reštartujeme skript
        time.sleep(1)

def main_process():
    """Funkcia sleduje stav hlavného procesu."""
    while not stop_event.is_set():
        print("Starting Main.py...")

        # Čakáme na internetové pripojenie pred spustením hlavného procesu
        wait_for_internet_connection()

        env = os.environ.copy()
        env['PYTHONPATH'] = '/usr/lib/python3/dist-packages/RPi.GPIO'  # Path to the RPi.GPIO module
        proc = subprocess.Popen(["C:/Users/adria/AppData/Local/Programs/Python/Python312/python", "Main.py"],
                                stdin=subprocess.PIPE, env=env)

        while not stop_event.is_set():
            if proc.poll() is not None:
                print(f"Main.py exited with code {proc.returncode}")
                break

            try:
                proc.stdin.write(b'\x00')  # Sending dummy byte to check process status
                proc.stdin.flush()

            except Exception as e:
                print(f"Error occurred: {e}, killing Main.py...")
                gp.closePort()
                proc.kill()
                break

            time.sleep(1)

        time.sleep(0.1)

def start_threads():
    """Funkcia spúšťa jednotlivé vlákna."""
    threads = []

    # Spustenie hlavného procesu vo vlákne
    thread_main = threading.Thread(target=main_process, name="MainProcess")
    thread_main.start()
    threads.append(thread_main)

    # Spustenie watchdog vlákna na monitorovanie ostatných vlákien
    thread_watchdog = threading.Thread(target=monitor_threads, args=(threads,), name="Watchdog")
    thread_watchdog.start()
    threads.append(thread_watchdog)

    return threads

try:
    threads = start_threads()

    while not stop_event.is_set():
        # Tu môžeš pridať ďalšie kontroly stavu

        time.sleep(0.5)

except KeyboardInterrupt:
    print("Keyboard interrupt detected, stopping script...")
    stop_event.set()
    gp.closePort()

# Čakáme na ukončenie všetkých vlákien
for thread in threads:
    thread.join()
