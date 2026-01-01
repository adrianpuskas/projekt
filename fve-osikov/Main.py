import time
import sys, os
import subprocess
import datetime
import queue
import threading
from globals import initializePort, closePort
import get_function as get
import set_function as set
#from Watchdog_GPT import main_process
from blynkSender import blynk_write, blynk_read

stop_event = threading.Event()
exception_queue = queue.Queue()

def restart_script2():
    print("-> BLYNK RESTART ...")
    #restart_script()
    closePort()
    blynk_write(110, 0)
    proc.kill()
    #break
    # Reštartujeme skript
    os.execv(sys.executable, ['python'] + sys.argv)

def signal_handler(sig, frame):
    print("KeyboardInterrupt detected, stopping threads...")
    stop_event.set()
    sys.exit(0)



def monitoring():
    
    if blynk_read("v110") == '1':
        restart_script2()
        
    if blynk_read("v6") != blynk_read ("v94"):
        blynk_write(94, blynk_read ("v6"))
        set.zmen_nastavenia()
        #blynk_write(3, "1")
        print("!! Nastavujem prioritu výstupu cez zrýchlené nastavenie !!")
        time.sleep(2)

    if blynk_read("v2") == '1':
        print("-> Aktualizujem nastavené dáta ...")
        set.nastavene_hodnoty_update()
        
    """
    if blynk_read("v0") == '1':
        print("-> Ukladám nastavenia ...")
        set.skontroluj_posuvace()
    """
    
    if blynk_read("v3") == '1':
        print("-> Ukladám nastavenia ...")
        set.zmen_nastavenia()

        while True:
            blynk_write(3, 0)
            if (blynk_read("v3") == '0'):
                break
            blynk_write(3, 0)
            time.sleep(1)

        get.nastaveneData()

    try:
        print("\n" + datetime.datetime.now().strftime("%H:%M:%S"))
        get.mode_zariadenia()
        get.aktualneData()
        #get.upozornenia()

        #time.sleep(0.1)

    except Exception as e:
        print(f"Error: {e}, killing Main.py...")
        exception_queue.put(e)
        #restart_script2()

def main():
    initializePort()
    blynk_write(3, 0)
    blynk_write(2, 0)

    #create_directories()

    #get.FW_version()
    #get.nastavenia_menica()	#posuvace
    ### KOMENT SKUSKA ### get.nastaveneData()			#Nastavene ciselne hodnoty baterie a pod.
    """
    threads = [
        threading.Thread(target=csvRW_thread, args=(stop_event,)),
        threading.Thread(target=write_to_pins_thread, args=(stop_event,))
    ]
    for thread in threads:
        thread.start()
    """
    try:
        while not stop_event.is_set():
            try:
                monitoring()
            except KeyboardInterrupt:
                stop_event.set()
                print("Keyboard interrupt detected, stopping all threads...")
                break

    finally:
        for thread in threads:
            thread.join()

        while True:
            try:
                raise exception_queue.get_nowait()
            except queue.Empty:
                break


if __name__ == "__main__":
    main()

