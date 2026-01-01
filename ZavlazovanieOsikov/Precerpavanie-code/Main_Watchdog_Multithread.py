import threading
import time
import signal
import RPi.GPIO as GPIO
import os

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

import time
from datetime import datetime
import faulthandler
faulthandler.enable()

import sys, os
import BlynkLib
from BlynkLib import Blynk
import Nadrz
import Signalizacia
import Globalne_premenne as gp

# Inicializácia Blynk
blynk = BlynkLib.Blynk(gp.token, server='blynk.cloud')

# Signal handler for safe shutdown
def signal_handler(sig, frame):
    print("KeyboardInterrupt detected, stopping threads...")
    gp.stop_threads = True
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Funkcie na riadenie čerpadla
def zapni_cerpadlo():
    gp.zapni_pin(gp.pin_cerpadlo)
    gp.setStavPinuVystupy(gp.pin_cerpadlo, 1)
    blynk.virtual_write(51, 1)
    blynk.log_event("cerpadlo1", "Nádrž 1 - Čerpadlo zapnuté")

def vypni_cerpadlo():
    gp.vypni_pin(gp.pin_cerpadlo)
    gp.setStavPinuVystupy(gp.pin_cerpadlo, 0)
    blynk.virtual_write(51, 0)

def chyba():
    print("\t\t- Systém prečerpávania je v poruche !")
    blynk.virtual_write(3, 1)
    blynk.virtual_write(90, 1)
    blynk.log_event("rpi1", "Systém prečerpávania je v poruche !")
    vypni_cerpadlo()

# Funkcia na kontrolu stavu čerpadla
def kontrola_cerpadla_vlakno():
    while not gp.stop_threads:
        print("*** Kontrola čerpadla (v nádrži 1 aj 2)")
        # Kontrola čerpadla, hlásenie porúch...
        time.sleep(1)

def signalizacia_vlakno():
    while not gp.stop_threads:
        print("*** Signalizácia")
        Signalizacia.signalizacia()
        time.sleep(1)

def monitorovanie_cerpadla_vlakno():
    while not gp.stop_threads:
        print("*** Režim obsluhy")
        Nadrz.monitorovanie()
        time.sleep(1)

# Funkcia pre letný režim
def leto(tlacidloRezimObsluhy):
    print("\n---> Letný režim")
    blynk.set_property(0, "color", "#F7CE46")
    # Režim riadenia nádrží...

# Funkcia pre zimný režim
def zima(tlacidloRezimObsluhy):
    print("\n---> Zimný režim")
    blynk.set_property(0, "color", "#2F6C8C")
    # Režim riadenia nádrží...

# Funkcia na inicializáciu watchdogu
def setup_watchdog():
    watchdog_fd = os.open("/dev/watchdog", os.O_WRONLY)
    return watchdog_fd

# Funkcia na pingovanie watchdogu
def ping_watchdog(watchdog_fd):
    try:
        os.write(watchdog_fd, b'\0')
    except OSError as e:
        print(f"Failed to ping watchdog: {e}")
        cleanup_watchdog(watchdog_fd)

# Funkcia na uvoľnenie watchdogu
def cleanup_watchdog(watchdog_fd):
    print("Stopping watchdog...")
    os.write(watchdog_fd, b'V')
    os.close(watchdog_fd)

def start_program():
    time.sleep(0.5)
    GPIO.cleanup()

    # Vystupy - signalizacne RELE pre ovladanie stĺpika a cerpadla
    for pin in gp.piny_vystupy:
        GPIO.setup(pin, GPIO.OUT)

    for pin in gp.piny_vstupy:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    print("\n*****************************************************")
    print(datetime.now().strftime("%d/%m/%y - %H:%M:%S"))

    print("*** StatusRPI")
    blynk.virtual_write(16, "ON")

    watchdog_fd = setup_watchdog()

    try:
        # Threads for various tasks
        threads = []
        threads.append(threading.Thread(target=kontrola_cerpadla_vlakno))
        threads.append(threading.Thread(target=signalizacia_vlakno))
        threads.append(threading.Thread(target=monitorovanie_cerpadla_vlakno))

        for thread in threads:
            thread.start()

        while True:
            ping_watchdog(watchdog_fd)
            time.sleep(10)  # Periodically ping watchdog

    except KeyboardInterrupt:
        print("Program interrupted. Cleaning up...")
    finally:
        cleanup_watchdog(watchdog_fd)
        for thread in threads:
            thread.join()

if __name__ == '__main__':
    start_program()