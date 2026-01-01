import os
import time
import threading
import requests

def wait_for_internet_connection():
    """Funkcia počká, kým sa zariadenie nepripojí k internetu."""
    while True:
        try:
            # Pokus o pripojenie k Blynk serveru (alebo inej stránke)
            response = requests.get("https://blynk.cloud", timeout=5)
            if response.status_code == 200:
                print("Pripojenie obnovené!")
                return
        except requests.ConnectionError:
            print("Čakám na obnovenie pripojenia k internetu...")
            time.sleep(5)

def start_main_script():
    """Funkcia na spustenie hlavného skriptu Main_Multithread.py."""
    print("Starting Main_Multithread.py...")
    os.system("python3 Main_Multithread.py")

def watchdog():
    """Funkcia watchdog, ktorá sa bude vykonávať v inom vlákne."""
    while True:
        # Sem môžeš pridať logiku na sledovanie, napríklad kontrolu pamäte, CPU, alebo niečo iné
        print("Watchdog beží...")
        time.sleep(10)

if __name__ == "__main__":
    print("Kontrolujem pripojenie k internetu...")
    wait_for_internet_connection()

    # Po obnovení pripojenia sa spustí hlavný skript
    threading.Thread(target=start_main_script).start()

    # Spustenie watchdogu vo vlákne
    threading.Thread(target=watchdog).start()