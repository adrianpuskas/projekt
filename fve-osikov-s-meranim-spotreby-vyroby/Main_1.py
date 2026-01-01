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

stop_event = threading.Event()
exception_queue = queue.Queue()

def restart_script():
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\t-> ZACINAM RESTART PROGRAMU ...", flush=True)
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
    stop_event.set()  # Signalizujeme ukončenie, Watchdog_GPT.py spracuje reštart

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
        sleep_time = max(0, 5 - elapsed_time)  # Presná 5-sekundová perióda
        time.sleep(sleep_time)

def monitoring():
    print(f"\n\t...Monitorovanie...", flush=True)
    try:
        ### Blynk tlacidlo restart programu
        if blynk_read("v110") == '1':
            restart_script()
        
        ### Blynk tlacidlo rycheho navolenia OUTPUT SOURCE PRIORITY
        if blynk_read("v6") != blynk_read("v94"):
            blynk_write(94, blynk_read("v6"))
            try:
                set.zmen_nastavenia()
                print(f"\t!! Nastavujem prioritu výstupu cez zrýchlené nastavenie !!", flush=True)
            except Exception as e:
                print(f"\tChyba pri zmene nastavení: \n{e}\n", flush=True)
            time.sleep(2)

        ### Blynk tlacidlo na precitanie dat z meniča
        if blynk_read("v2") == '1':
            print(f"\t-> Aktualizujem nastavené dáta ...", flush=True)
            try:
                set.nastavene_hodnoty_update()
            except Exception as e:
                print(f"\tChyba pri aktualizácii nastavení: \n{e}\n", flush=True)
        
        ### Blynk tlacidlo na poziadavku nahrat nove nastavene data do meniča
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
        
        ### Zakladny beh programu, 
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
        restart_script()   ## PRIDANE NA TEST V PRIPADE TOHO ZE TO SPADNE ....
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
    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Chyba pri inicializácii portu: \n\t{e}\n", flush=True)
        sys.exit(1)

    # Spustenie vlákna na zber dát
    data_thread = threading.Thread(target=data_collection_thread)
    data_thread.start()

    try:
        while not stop_event.is_set():
            monitoring()
            time.sleep(1)  # Monitorovanie Blynku každú sekundu
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