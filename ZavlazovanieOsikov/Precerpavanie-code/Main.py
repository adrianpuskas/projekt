#-*- coding: utf-8 -*-
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
import time
import datetime
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
def kontrola_cerpadla(tlacidloRezimObsluhy,cerpadlo_status_blynk):
    print("*** Kontrola čerpadla (v nádrži 1 aj 2)")

    # ? kontrola stavu čerpadiel (v nádrži 1 aj 2)
    if (gp.read("v60") == 1 or cerpadlo_status_blynk == 1):  # ak ide nejaké čerpadlo, či už v nádrži 1 alebo 2
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




#?######################################################################################################################################
# * Funkcia pre letný režim
def leto(tlacidloRezimObsluhy, cerpadlo_status_blynk):
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
                    print("\t- Nádrž 1 - plná -> ", gp.objem_vody, "litrov ")
                    print("\n\t- Nádrž 2 - v polovici -> ", gp.objem_vody2, "litrov  ")

                # prvá plná, druhá prázdna, čerpem
                elif (gp.plavak2_1 == 0 and gp.plavak2_2 == 0):
                    gp.stav_cerpadla = 1  # ! zapnutie čerpadla
                    print("\t- Nádrž 1 - plná -> ", gp.objem_vody, "litrov ")
                    print("\n\t- Nádrž 2 - prázdna -> ", gp.objem_vody2, "litrov ")

            # ? ----> #P1->1 P2->0 - prvá nádrž je v polovici
            elif (gp.plavak1_1 == 1 and gp.plavak1_2 == 0):
                # v prvej je polovica, druhá je plná, nečerpem
                if (gp.plavak2_1 == 1 and gp.plavak2_2 == 1):
                    gp.stav_cerpadla = 0  # ! vypnutie čerpadla
                    print("\t- Nádrž 1 - v polovici -> ", gp.objem_vody, "litrov ")
                    print("\n\t- Nádrž 2 - plná -> ", gp.objem_vody2, "litrov ")

                # v prvej je polovica, v druhej tiež, môžem dočerpať (ale nemusím)
                elif (gp.plavak2_1 == 1 and gp.plavak2_2 == 0):
                    gp.stav_cerpadla = 1  # ! zapnutie čerpadla
                    print("\t- Nádrž 1 - v polovici -> ", gp.objem_vody, "litrov ")
                    print("\n\t- Nádrž 2 - v polovici -> ", gp.objem_vody2, "litrov ")

                # v prvej je polovica, druhá je prázdna, čerpem
                elif (gp.plavak2_1 == 0 and gp.plavak2_2 == 0):
                    gp.stav_cerpadla = 1  # ! zapnutie čerpadla
                    print("\t- Nádrž 1 - v polovici -> ", gp.objem_vody, "litrov ")
                    print("\n\t- Nádrž 2 - prázdna -> ", gp.objem_vody2, "litrov ")

            # ? ----> #P1->0 P2->0 - prvá nádrž je prázdna
            elif (gp.plavak1_1 == 0 and gp.plavak1_2 == 0):
                # prázdna prvá nádrž, nie je čo prečerpať takže nečerpem
                gp.stav_cerpadla = 0  # ! vypnutie čerpadla
                print("\t- Nádrž 1 - prázdna -> ", gp.objem_vody, "litrov ")

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

    kontrola_cerpadla(tlacidloRezimObsluhy, cerpadlo_status_blynk)

#?######################################################################################################################################
# * Funkcia pre zimný režim
def zima(tlacidloRezimObsluhy,cerpadlo_status_blynk):
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
                print("\t- Nádrž 1 - plná -> ", gp.objem_vody, "litrov ")

            # ? ----> #P1->1 P2->0 - prvá nádrž v polovici
            elif (gp.plavak1_1 == 1 and gp.plavak1_2 == 0):
                gp.stav_cerpadla = 1  # ! zapnutie čerpadla
                print("\t- Nádrž 1 - v polovici -> ", gp.objem_vody, "litrov ")

            # ? ----> #P1->0 P2->0 - prvá nádrž prázdna
            elif (gp.plavak1_1 == 0 and gp.plavak1_2 == 0):
                gp.stav_cerpadla = 0  # ! vypnutie čerpadla
                print("\t- Nádrž 1 - prázdna -> ", gp.objem_vody, "litrov ")

            else:  # ? iné(?)
                chyba()  # chybové hlásenie a signalizácia
                print("\t- CHYBOVÝ STAV - Systém si vyžaduje kontrolu !")

    # ?.............................................................................................................................
    # * MANUÁLNY REŽIM
    else:  # manual
        print("\nMANUÁLNE RIADENIE\n")

    kontrola_cerpadla(tlacidloRezimObsluhy,cerpadlo_status_blynk)

#?######################################################################################################################################
# * Funkcia monitorujúca zmeny v stave hladiny vody v nádrži č.2 (6000L), obsluhujúca čerpadlo na základe nameraných dát z oboch nádrží
def monitorovanie_cerpadla():
    print("*** Režim obsluhy")
    # prečítanie stavu tlačidiel voliacich režimy prevádzky systému z Blynk
    tlacidloRezimObsluhy = gp.read("v1")
    tlacidloRezimObdobia = gp.read("v0")

    Nadrz.monitorovanie()

    cerpadlo_status_blynk = gp.read("v51")  # prečítanie stavu čerpadla z Blynk

    # * Monitorovanie statusu RPi2 v nádrži 2 počas leta (v zime je neaktívne)
    if(tlacidloRezimObdobia == 0): # LETO
        if(gp.read("v4") == 1): # kontrola systému zavlažovania, signalizácia jeho neaktívnosti
                blynk.log_event("rpi2", "Systém zavlažovania je v poruche ! ") # notifikácia
                print("- Systém zavlažovania je v poruche ! \n")

        leto(tlacidloRezimObsluhy,cerpadlo_status_blynk)

    else:
        zima(tlacidloRezimObsluhy,cerpadlo_status_blynk)
#?_________________________________________________________________________________________________________________________________



#?#############################################################################################

def start_program():
    time.sleep(0.5)
    GPIO.cleanup() # uvoľnenie GPIO pinov

    # * Vystupy - signalizačné RELE pre ovladanie stĺpika a čerpadla
    for pin in gp.piny_vystupy:
        GPIO.setup(pin, GPIO.OUT) # nastavenie pinu ako výstupý
        cerpadlo = gp.read("v51") # prečítanie aktuálneho stavu čerpadla z Blynk
        if (cerpadlo == 1): #ak je čerpadlo zapnuté v Blynk, tak ho nechaj zapnuté
            GPIO.output(pin, GPIO.LOW) # nastavenie na LOW voltage (vypnutie)
        else:
            GPIO.output(pin, GPIO.HIGH) # nastavenie na HIGH voltage (zapnutie)


    while True:
        # časové obmedzenie
        aktualny_cas = datetime.now()
        datehour = aktualny_cas.strftime("%d/%m/%y - %H:%M:%S")
        hour = aktualny_cas.strftime("%H:%M:%S")

        print("\n*****************************************************")
        print(datehour, "\n ")

        # * Vstupy - ovládania a istenia
        for pin in gp.piny_vstupy:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # nastavenie pinu ako vstupný s pud-down rezistorom
            gp.piny_vstupy[pin]['state'] = GPIO.input(pin) # aktualizácia jeho aktuálneho stavu v pomocných premnenných

        # * Kontrola stavu RPI 2 (zavlažovanie) a aktualizácia stavu RPI 1 prečerpávania
        print("*** StatusRPI")
        blynk.virtual_write(16, "ON")
        if(gp.read("v3") == 1): # ak bol systém neaktívny
            blynk.log_event("rpi1", "Systém prečerpávania je opäť v prevádzke :) ") # notifikácia

        blynk.virtual_write(3,0) # nastavenie virtuálneho pinu statusu RPI 1 prečerpávania na aktívny

        print("*** Signalizácia")
        # * Kontrola a akutializácia stavu stignalizačného stĺpika
        Signalizacia.signalizacia()

        print("*** Monitorovanie systému")
        # * Hlavná logika monitorovania a ovládania čerpadla v systéme
        monitorovanie_cerpadla()


#?######################################################################################################################################
# * Main funcia
if __name__ == '__main__':
    start_program()