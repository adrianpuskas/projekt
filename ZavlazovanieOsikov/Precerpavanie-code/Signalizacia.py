# Signalizacia.py
# Import potrebných modulov
import RPi.GPIO as GPIO
import time
import datetime
from datetime import datetime
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

#! potrebné súbory
import Globalne_premenne as gp
import BlynkLib  # pip install blynk-library-python  #pip3 install blynk-library-python

#?###########################################################
# Inicializácia Blynk
blynk = BlynkLib.Blynk(gp.token,server='blynk.cloud')
#?###########################################################

# * Funkcia na ovládanie signalizačného stĺpika
def signalizacia():

    # odčítanie akutálnych hodnôt vitruálnych pinov signalizačného stľpika z Blynk
    abnormal = gp.read("v7")
    oranzova = gp.read("v91")
    cervena = gp.read("v90")
    modra = gp.read("v93")

    # Ak je nameraná vonkajšia teplota <=0 spustí sa modrá signalizácia
    aktualna_teplota = gp.read_string("v56") # odčítanie aktuálnej vonkajšej teploty z virtuálneho pinu Blynk
    if(aktualna_teplota == "--"): # ak senzor nie je aktívny
        pass
    else:
        try:
            if(float(aktualna_teplota)<=0):
                print("\t\t  - Teplota ovzdušia je <= 0 !")
                blynk.virtual_write(93, 1)  # zapnutie signalizácie do príslušného virtuálneho pinu v Blynk
        except TypeError:
                blynk.virtual_write(56, "--")  # ošetrenie chybového stavu

    ### Abnormálny stav signalizácia
    if (abnormal == 1):
        print("\t\t- Abnormálny stav !")
        blynk.log_event("abnormal", "Abnormálny stav plavákov v nádržiach !") # notifikácia
        blynk.virtual_write(93, 1) # zápis zapnutej modrej signalizácie do príslušného virtuálneho pinu v Blynk
        blynk.virtual_write(90, 1) # zápis zapnutej červenej signalizácie do príslušného virtuálneho pinu v Blynk
        blynk.virtual_write(91, 1) # zápis zapnutej oranžovej signalizácie do príslušného virtuálneho pinu v Blynk

        # reálne zapnutie požadovaných pinov na signalizačnom stľpiku s efektom blikania
        for x in range (0,2):
            gp.zapni_pin(gp.pin_modra)
            time.sleep(0.3)
            gp.zapni_pin(gp.pin_cervena)
            time.sleep(0.3)
            gp.vypni_pin(gp.pin_modra)
            gp.zapni_pin(gp.pin_oranzova)
            time.sleep(0.3)
            gp.vypni_pin(gp.pin_cervena)
            time.sleep(0.3)
            gp.vypni_pin(gp.pin_oranzova)
            time.sleep(0.3)

        blynk.virtual_write(93, 0) # zápis vypnutej modrej signalizácie do príslušného virtuálneho pinu v Blynk
        blynk.virtual_write(90, 0) # zápis vypnutej červenej signalizácie do príslušného virtuálneho pinu v Blynk
        blynk.virtual_write(91, 0) # zápis vypnutej oranžovej signalizácie do príslušného virtuálneho pinu v Blynk

    ### Oranžová signalizácia
    elif (oranzova == 1):
        print("\t\t- Oranžová signalizácia!")
        blynk.virtual_write(91, 1)  # zápis zapnutej oranžovej signalizácie do príslušného virtuálneho pinu v Blynk

        # reálne zapnutie požadovaných pinov na signalizačnom stľpiku s efektom blikania
        for x in range (0,2):
            gp.zapni_pin(gp.pin_oranzova)
            time.sleep(0.3)
            gp.vypni_pin(gp.pin_oranzova)
            time.sleep(0.3)

        blynk.virtual_write(91, 0) # zápis vypnutej oranžovej signalizácie do príslušného virtuálneho pinu v Blynk

    ### Červená signalizáca
    elif (cervena == 1):
        print("\t\tČervená signalizácia!")
        blynk.virtual_write(90, 1) # zápis zapnutej červenej signalizácie do príslušného virtuálneho pinu v Blynk

        # reálne zapnutie požadovaných pinov na signalizačnom stľpiku s efektom blikania
        for x in range (0,2):
            gp.zapni_pin(gp.pin_cervena)
            time.sleep(0.3)
            gp.vypni_pin(gp.pin_cervena)
            time.sleep(0.3)

        blynk.virtual_write(90, 0) # zápis vypnutej červenej signalizácie do príslušného virtuálneho pinu v Blynk

    ### Modrá signalizácia
    elif (modra == 1):
        minuty = int(datetime.fromtimestamp(int((datetime.now()).timestamp())).strftime('%M')) # minúty aktuálneho času

        if(minuty == 30 or minuty == 00): # V prípade aktívnej modrej signalizácie bude modrá farba blikať len každú pol hodinu

            print("\t\t- Modrá signalizácia!")
            blynk.virtual_write(93, 1) # zápis zapnutej modrej signalizácie do príslušného virtuálneho pinu v Blynk

            # reálne zapnutie požadovaných pinov na signalizačnom stľpiku s efektom blikania
            for x in range (0,2):
                gp.zapni_pin(gp.pin_modra)
                time.sleep(0.3)
                gp.vypni_pin(gp.pin_modra)
                time.sleep(0.3)

            blynk.virtual_write(93, 0) # zápis vypnutej modrej signalizácie do príslušného virtuálneho pinu v Blynk

        else:
            blynk.virtual_write(93, 0) # zápis vypnutej modrej signalizácie do príslušného virtuálneho pinu v Blynk