#-*- coding: utf-8 -*-

import threading
import time
import signal
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
import time
from datetime import datetime
import faulthandler
faulthandler.enable()

import sys, os
import BlynkLib
from BlynkLib import Blynk # pip install blynk-library-python  #pip3 install blynk-library-python

#! potrebné súbory
import Nadrz
import Signalizacia
import Globalne_premenne as gp

#?######################################################################################################################################
# Inicializácia Blynk
blynk = BlynkLib.Blynk(gp.token,server='blynk.cloud')
#?######################################################################################################################################

def signal_handler(sig, frame):
    print("KeyboardInterrupt detected, stopping threads...")
    gp.stop_threads = True
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

#?######################################################################################################################################
# * Funkcie na riadenie čerpadla
def zapni_cerpadlo():
    gp.zapni_pin(gp.pin_cerpadlo) # zapnutie pinu čerpadla
    gp.setStavPinuVystupy(gp.pin_cerpadlo, 1)
    blynk.virtual_write(51, 1) # zápis stavu čerpadla do virtuálneho pinu v Blynk
    blynk.log_event("cerpadlo1", "Nádrž 1 - Čerpadlo zapnuté") # notifikácia

def vypni_cerpadlo():
    gp.vypni_pin(gp.pin_cerpadlo) # vypnutie pinu čerpadla
    gp.setStavPinuVystupy(gp.pin_cerpadlo, 0)
    blynk.virtual_write(51, 0) # zápis stavu čerpadla do virtuálneho pinu v Blynk

#?######################################################################################################################################
# ! Funkcia na signalizáciu poruchy v systéme
def chyba():
    print("\t\t- Systém prečerpávania je v poruche !")
    blynk.virtual_write(3, 1) # signalizácia neaktívnosti systému prečerpávania v Blynk
    blynk.virtual_write(90, 1) # zápis zapnutej červenej signalizácie do príslušného virtuálneho pinu v Blynk
    blynk.log_event("rpi1", "Systém prečerpávania je v poruche ! ") # notifikácia
    vypni_cerpadlo() # vypnutie čerpadla


#?######################################################################################################################################
# * Funkcia na kontrolu stavu čerpadla
def kontrola_cerpadla_vlakno():
    while not gp.stop_threads:
        print("*** Kontrola čerpadla (v nádrži 1 aj 2)")

        tlacidloRezimObsluhy = gp.read("v1")
        cerpadlo_status_blynk = gp.read("v51")  # prečítanie stavu čerpadla z Blynk

        # ? kontrola stavu čerpadiel (v nádrži 1 aj 2)

        if (gp.read("v60") == 1 or cerpadlo_status_blynk):  # ak ide nejaké čerpadlo, či už v nádrži 1 alebo 2
            blynk.virtual_write(92, 1)  # zápis zapnutej zelenej signalizácie do príslušného virtuálneho pinu v Blynk
            gp.zapni_pin(gp.pin_zelena)  # zapni zelenú signalizáciu
        else:
            blynk.virtual_write(92, 0)  # zápis vypnutej zelenej signalizácie do príslušného virtuálneho pinu v Blynk
            gp.vypni_pin(gp.pin_zelena)  # vypni zelenú signalizáciu

        # ! Porucha čerpadla
        if (gp.getStavPinuVstupy(gp.pin_motorova_ochrana) == 1):  # ak čerpadlo hlási poruchový stav
            print("\t\t- Porucha čerpadla - skontroluj motor a motorovú ochranu Q1 !")
            chyba()  # chybové hlásenie a signalizácia
        else:
            if(tlacidloRezimObsluhy == 0): # automatika
                if(gp.stav_cerpadla == 0): # ak je realne vypnute
                    if(cerpadlo_status_blynk == 0): # aj v Blynku vypnuté
                        print("\t\t- Čerpadlo je vypnuté")
                    else: # v Blynku zapnuté
                        print ("\t\t--->>> Vypínam čerpadlo")
                        vypni_cerpadlo() # ! vypnutie čerpadla
                        gp.stav_cerpadla = 0
                else: # ak je realne zapnute
                    if(cerpadlo_status_blynk == 0): # v Blynku vypnuté
                        print ("\t\t--->>> Zapínam čerpadlo")
                        zapni_cerpadlo() # ! zapnutie čerpadla
                        gp.stav_cerpadla = 1
                    else: # aj v Blynku zapnuté
                        print("\t\t- Čerpadlo je zapnuté")


            else: # manual
                if(cerpadlo_status_blynk == 0): # ak je v Blynku vypnuté
                    if(gp.stav_cerpadla == 0): # aj realne vypnuté
                        print("\t\t- Čerpadlo je vypnuté")
                    else: # realne zapnute
                        print ("\t\t--->>> Vypínam čerpadlo")
                        vypni_cerpadlo() # ! vypnutie čerpadla
                        gp.stav_cerpadla = 0

                else: # v Blynku zapnuté
                    if(gp.stav_cerpadla == 0): # realne vypnuté
                        print ("\t\t--->>> Zapínam čerpadlo")
                        zapni_cerpadlo() # ! zapnutie čerpadla
                        gp.stav_cerpadla = 1
                    else: # aj realne vypnute
                        print("\t\t- Čerpadlo je zapnuté")

        time.sleep(1)

def signalizacia_vlakno():
    while not gp.stop_threads:
        print("*** Signalizácia")
        Signalizacia.signalizacia()
        time.sleep(1)

def monitorovanie_cerpadla_vlakno():
    while not gp.stop_threads:
        print("*** Režim obsluhy")
         # prečítanie stavu tlačidiel voliacich režimy prevádzky systému z Blynk
        tlacidloRezimObsluhy = gp.read("v1")
        tlacidloRezimObdobia = gp.read("v0")

        Nadrz.monitorovanie()

        # * Monitorovanie statusu RPi2 v nádrži 2 počas leta (v zime je neaktívne)
        if(tlacidloRezimObdobia == 0): # LETO
            if(gp.read("v4") == 1): # kontrola systému zavlažovania, signalizácia jeho neaktívnosti
                    blynk.log_event("rpi2", "Systém zavlažovania je v poruche ! ") # notifikácia
                    print("- Systém zavlažovania je v poruche ! \n")

            leto(tlacidloRezimObsluhy)

        else:
            zima(tlacidloRezimObsluhy)

        time.sleep(1)

#?######################################################################################################################################
# * Funkcia pre letný režim
def leto(tlacidloRezimObsluhy):
    print("\n---> Letný režim")
    blynk.set_property(0, "color", "#F7CE46")

    # * AUTOMATICKÝ REŽIM
    if (tlacidloRezimObsluhy == 0):  # automatika
        print("\nAUTOMATICKÉ RIADNIE\n")

        # ? ----> #P1->0 P2->1 - prvá alebo druhá nádrž hlási abnormálny stav
        if ((gp.plavak1_1 == 0 and gp.plavak1_2 == 1) or (gp.plavak2_1 == 0 and gp.plavak2_2 == 1)):
            gp.stav_cerpadla = 0  # ! vypnutie čerpadla
            print("\t- ABNORMÁLNY STAV - Nádrže si vyžadujú kontrolu !")

        else:
            # ? ----> #P1->1 P2->1 - prvá nádrž je plná
            if (gp.plavak1_1 == 1 and gp.plavak1_2 == 1):
                # prvá aj druhá nádrž je plná
                if (gp.plavak2_1 == 1 and gp.plavak2_2 == 1):
                    gp.stav_cerpadla = 0  # ! vypnutie čerpadla
                    print("\t- Obe nádrže plné !!! ")

                # prvá plná, druhá po prvý plavák, môžem dočerpať
                elif (gp.plavak2_1 == 1 and gp.plavak2_2 == 0):  #
                    gp.stav_cerpadla = 1  # ! zapnutie čerpadla
                    print("\t- Nádrž 1 - plná  ")
                    print("\n\t- Nádrž 2 - v polovici ")

                # prvá plná, druhá prázdna, čerpem
                elif (gp.plavak2_1 == 0 and gp.plavak2_2 == 0):
                    gp.stav_cerpadla = 1  # ! zapnutie čerpadla
                    print("\t- Nádrž 1 - plná ")
                    print("\n\t- Nádrž 2 - prázdna  ")

            # ? ----> #P1->1 P2->0 - prvá nádrž je v polovici
            elif (gp.plavak1_1 == 1 and gp.plavak1_2 == 0):
                # v prvej je polovica, druhá je plná, nečerpem
                if (gp.plavak2_1 == 1 and gp.plavak2_2 == 1):
                    gp.stav_cerpadla = 0  # ! vypnutie čerpadla
                    print("\t- Nádrž 1 - v polovici ")
                    print("\n\t- Nádrž 2 - plná ")

                # v prvej je polovica, v druhej tiež, môžem dočerpať (ale nemusím)
                elif (gp.plavak2_1 == 1 and gp.plavak2_2 == 0):
                    gp.stav_cerpadla = 1  # ! zapnutie čerpadla
                    print("\t- Nádrž 1 - v polovici ")
                    print("\n\t- Nádrž 2 - v polovici ")

                # v prvej je polovica, druhá je prázdna, čerpem
                elif (gp.plavak2_1 == 0 and gp.plavak2_2 == 0):
                    gp.stav_cerpadla = 1  # ! zapnutie čerpadla
                    print("\t- Nádrž 1 - v polovici  ")
                    print("\n\t- Nádrž 2 - prázdna ")

            # ? ----> #P1->0 P2->0 - prvá nádrž je prázdna
            elif (gp.plavak1_1 == 0 and gp.plavak1_2 == 0):
                # prázdna prvá nádrž, nie je čo prečerpať takže nečerpem
                gp.stav_cerpadla = 0  # ! vypnutie čerpadla
                print("\t- Nádrž 1 - prázdna ")

            else:  # ? iné(?)
                chyba()  # chybové hlásenie a signalizácia
                print("\t- CHYBOVÝ STAV - Systém si vyžaduje kontrolu !")
        time.sleep(2)

        # Kontrola statusu ESP32, ak nie je v prevádzke (nemám dáta z nádrže č.2), tak nečerpem
        if (gp.read("v5") == 0):
            gp.stav_cerpadla = 0;
            blynk.virtual_write(90, 1)  # zápis zapnutej červenej signalizácie do príslušného virtuálneho pinu v Blynk
            blynk.log_event("nadrz2", "Monitorovanie nádrže 2 nie je aktívne !")  # notifikácia
            blynk.virtual_write(70, "Monitorovanie nádrže 2 nie je aktívne !")  # zápis nameranej hodnoty do príslušného virtuálneho pinu v Blynk

    # ?.............................................................................................................................
    # * MANUÁLNY REŽIM
    else:  # manual
        print("\nMANUÁLNE RIADENIE\n")

#?######################################################################################################################################
# * Funkcia pre zimný režim
def zima(tlacidloRezimObsluhy):
    print("\n---> Zimný režim")
    blynk.set_property(0, "color", "#2F6C8C")

    # * AUTOMATICKÝ REŽIM
    if (tlacidloRezimObsluhy == 0):  # automatika
        print("\nAUTOMATICKÉ RIADNIE\n")

        # ? ----> #P1->0 P2->1 - prvá alebo druhá nádrž hlási abnormálny stav plavákov
        if ((gp.plavak1_1 == 0 and gp.plavak1_2 == 1)):
            gp.stav_cerpadla = 0  # ! vypnutie čerpadla
            print("\t- ABNORMÁLNY STAV - Nádrže si vyžadujú kontrolu !")
        else:
            # ? ----> #P1->1 P2->1 - prvá nádrž plná
            if (gp.plavak1_1 == 1 and gp.plavak1_2 == 1):
                gp.stav_cerpadla = 1  # ! zapnutie čerpadla
                print("\t- Nádrž 1 - plná ")

            # ? ----> #P1->1 P2->0 - prvá nádrž v polovici
            elif (gp.plavak1_1 == 1 and gp.plavak1_2 == 0):
                gp.stav_cerpadla = 1  # ! zapnutie čerpadla
                print("\t- Nádrž 1 - v polovici ")

            # ? ----> #P1->0 P2->0 - prvá nádrž prázdna
            elif (gp.plavak1_1 == 0 and gp.plavak1_2 == 0):
                gp.stav_cerpadla = 0  # ! vypnutie čerpadla
                print("\t- Nádrž 1 - prázdna ")

            else:  # ? iné(?)
                chyba()  # chybové hlásenie a signalizácia
                print("\t- CHYBOVÝ STAV - Systém si vyžaduje kontrolu !")

    # ?.............................................................................................................................
    # * MANUÁLNY REŽIM
    else:  # manual
        print("\nMANUÁLNE RIADENIE\n")


def start_program():

    time.sleep(0.5)
    GPIO.cleanup()  # Uvolnenie GPIO pinov

    # Vystupy - signalizacne RELE pre ovladanie stĺpika a cerpadla
    for pin in gp.piny_vystupy:
        GPIO.setup(pin, GPIO.OUT)  # nastavenie pinu ako vystupny
        cerpadlo = gp.read("v51")  # precitanie aktualneho stavu cerpadla z Blynk
        if cerpadlo == 1:  # ak je cerpadlo zapnute v Blynk, tak ho nechaj zapnute
            GPIO.output(pin, GPIO.LOW)  # nastavenie na LOW voltage (vypnutie)
        else:
            GPIO.output(pin, GPIO.HIGH)  # nastavenie na HIGH voltage (zapnutie)

    # Vstupy - ovladania a istenia
    for pin in gp.piny_vstupy:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # nastavenie pinu ako vstupny s pud-down rezistorom
        gp.piny_vstupy[pin]['state'] = GPIO.input(pin)  # aktualizacia jeho aktualneho stavu v pomocnych premennych

    aktualny_cas = datetime.now()
    datehour = aktualny_cas.strftime("%d/%m/%y - %H:%M:%S")
    hour = aktualny_cas.strftime("%H:%M:%S")

    print("\n*****************************************************")
    print(datehour, "\n ")

    # Kontrola stavu RPI 2 (zavlažovanie) a aktualizacia stavu RPI 1 precerpavania
    print("*** StatusRPI")
    blynk.virtual_write(16, "ON")
    if gp.read("v3") == 1:  # ak bol system neaktivny
        blynk.log_event("rpi1", "System precerpavania je opat v prevadzke :) ")  # notifikacia

    blynk.virtual_write(3, 0)  # nastavenie virtualneho pinu statusu RPI 1 precerpavania na aktivny

    # Define threads for other functionalities
    threads = []
    threads.append(threading.Thread(target=kontrola_cerpadla_vlakno))
    threads.append(threading.Thread(target=signalizacia_vlakno))
    threads.append(threading.Thread(target=monitorovanie_cerpadla_vlakno))

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()


if __name__ == '__main__':
    start_program()