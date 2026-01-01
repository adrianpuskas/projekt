# Nadrz.py
# Import potrebných modulov
import RPi.GPIO as GPIO
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

# * Funkcia na monitorovanie stavu hladiny vody v nádrži č.1 a 2
def monitorovanie():

    print("*** Hladina vody v nádrži 1")

    # uloženie aktuálnych hodnôt plavákov do globálnych pomocných premenných
    gp.plavak1_1 = gp.getStavPinuVstupy(gp.pin_plavak1)
    gp.plavak1_2 = gp.getStavPinuVstupy(gp.pin_plavak2)

    gp.plavak2_1 = gp.read("v72")
    gp.plavak2_2 = gp.read("v73")

    print('\t-----------',  gp.plavak1_2)
    print('\t|')
    print('\t|')
    print('\t|')
    print('\t|')
    print('\t-----------',  gp.plavak1_1)


    blynk.virtual_write(18, gp.plavak1_1)
    if(gp.plavak1_1 == 1):
        blynk.set_property(18, "color", "#5AC4F7")
    blynk.virtual_write(19, gp.plavak1_2)
    if(gp.plavak1_2 == 1):
        blynk.set_property(19, "color", "#5AC4F7")

    # * Nádrž č. 1
    # ak sú oba plaváky hore
    if(gp.plavak1_1 == 1 and gp.plavak1_2 == 1):
        blynk.log_event("nadrz1", "Nádrž 1 - plná") # notifikácia
        blynk.set_property(70, "color", "#ED732E")
        blynk.virtual_write(70, "Nádrž prečerpávania je plná") # zápis nameranej hodnoty do príslušného virtuálneho pinu v Blynk

    # ak sú oba plaváky dole
    elif(gp.plavak1_1 == 0 and gp.plavak1_2 == 0):
        blynk.set_property(70, "color", "#ED6C59")
        blynk.virtual_write(70, "Nádrž prečerpávania má nedostatok vody") # zápis nameranej hodnoty do príslušného virtuálneho pinu v Blynk

    # ak je prvý plavák hore a druhý dole
    elif(gp.plavak1_1 == 1 and gp.plavak1_2 == 0):
        blynk.set_property(70, "color", "#86B953")
        blynk.virtual_write(70, "Nádrž prečerpávania má dostatok vody") # zápis nameranej hodnoty do príslušného virtuálneho pinu v Blynk

    # ak je druhý plavák hore a prvý dole
    elif(gp.plavak1_1 == 0 and gp.plavak1_2 == 1): #abnormal
        blynk.virtual_write(70, "Chybový stav plavákov v nádrži prečerpávania !") # zápis nameranej hodnoty do príslušného virtuálneho pinu v Blynk
        blynk.set_property(70, "color", "#EB4D3D")
        blynk.virtual_write(7, 1) # ! signalizácia abnormálneho stavu zapísaná do Blynk
        blynk.log_event("abnormal", "Chybový stav plavákov v nádrži prečerpávania !")

    # ? #?###########################################################
    # * Nádrž č. 2
     # ak sú oba plaváky hore
    if(gp.plavak2_1 == 1 and gp.plavak2_2 == 1):
        blynk.log_event("nadrz2", "Nádrž 2 - plná") # notifikácia
        blynk.set_property(71, "color", "#ED732E")
        blynk.virtual_write(71, "Nádrž zavlažovania je plná") # zápis nameranej hodnoty do príslušného virtuálneho pinu v Blynk

    # ak sú oba plaváky dole
    elif(gp.plavak2_1 == 0 and gp.plavak2_2 == 0):
        blynk.set_property(71, "color", "#ED6C59")
        blynk.virtual_write(71, "Nádrž zavlažovania má nedostatok vody") # zápis nameranej hodnoty do príslušného virtuálneho pinu v Blynk

    # ak je prvý plavák hore a druhý dole
    elif(gp.plavak2_1 == 1 and gp.plavak2_2 == 0):
        blynk.set_property(71, "color", "#86B953")
        blynk.virtual_write(71, "Nádrž zavlažovania má dostatok vody")  # zápis nameranej hodnoty do príslušného virtuálneho pinu v Blynk

    # ak je druhý plavák hore a prvý dole
    elif(gp.plavak2_1 == 0 and gp.plavak2_2 == 1): #abnormal
        blynk.virtual_write(71, "Chybový stav plavákov v nádrži zavlažovania !") # zápis nameranej hodnoty do príslušného virtuálneho pinu v Blynk
        blynk.virtual_write(19,0)
        blynk.set_property(71, "color", "#EB4D3D")
        blynk.virtual_write(7, 1) # ! signalizácia abnormálneho stavu zapísaná do Blynk
        blynk.log_event("abnormal", "hybový stav plavákov v nádrži zavlažovania !")

    #kontola, či nie sú obe nádrže plné
    if(gp.plavak1_2 == 1 and gp.plavak2_2 == 1):
        blynk.virtual_write(91, 1) # zápis zapnutej oranzovej signalizácie do príslušného virtuálneho pinu v Blynk
        blynk.log_event("nadrz1", "Obe nádrže plné !!! ") # notifikácia