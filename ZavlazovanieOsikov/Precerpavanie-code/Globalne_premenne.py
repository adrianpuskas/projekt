# Globalne_premenne.py
# Import potrebných modulov
import requests
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

#?###########################################################

# * Token pre pripojenie k BLYNK
token = "NhAZeqig1jKjzGuVcYmdnAH_zzIWd3pL"

#?###########################################################

stop_threads = False

# * Funkcie na čítanie dát z Blynk virtuálnych pinov
def read(pin): #BLYNK int
	api_url = "https://blynk.cloud/external/api/get?token="+token+"&"+pin
	response = requests.get(api_url)
	return int(response.content.decode())

def read_string(pin): #BLYNK string
	api_url = "https://blynk.cloud/external/api/get?token="+token+"&"+pin
	response = requests.get(api_url)

def read_float(pin): #BLYNK float
	api_url = "https://blynk.cloud/external/api/get?token="+token+"&"+pin
	response = requests.get(api_url)
	return float(response.content.decode())

#?###########################################################

# * pomocné premenné
stav_cerpadla = 0
plavak1_1 = 0
plavak1_2 = 0
plavak2_1 = 0
plavak2_2 = 0

# * Inicializácia vstupných a výstupných pinov (zoznam s menom a počiatočným stavom pinu)
#?######################################################################################################################################
# * Výstupné piny - signalizačný stĺpik a čerpadlo
pin_zelena = 1
pin_oranzova = 12
pin_cervena = 16
pin_modra = 21
pin_cerpadlo = 20

piny_vystupy = {
   pin_zelena : {'name' : 'zelena', 'state' : 0},
   pin_oranzova : {'name' : 'oranzova', 'state' : 0},
   pin_cervena : {'name' : 'cervena', 'state' : 0},
   pin_modra : {'name' : 'modra', 'state' : 0},
   pin_cerpadlo:{'name':'cerpadlo', 'state':0}
}

# * Getter-y a Setter-y pre výstupné piny
def getStavPinuVystupy(pin):
    return piny_vystupy[pin]['state']

def setStavPinuVystupy(pin, hodnota):
    piny_vystupy[pin]['state'] = hodnota

#?###########################################################
# * Vstupné piny - plavákové spínače a motorová ochrana
pin_plavak1 = 0
pin_plavak2 = 5
pin_motorova_ochrana = 23

piny_vstupy = {
   pin_plavak1 : {'name' : 'plavak_1', 'state' : 0},
   pin_plavak2 : {'name' : 'plavak_2', 'state' : 0},
   pin_motorova_ochrana: {'name' : 'motorova_ochrana', 'state' : 0}
}

# * Getter-y a Setter-y pre vstupné piny
def getStavPinuVstupy(pin):
    return piny_vstupy[pin]['state']

def setStavPinuVstupy(pin, hodnota):
    piny_vstupy[pin]['state'] = hodnota

#?###########################################################

# * Funkcia na vypnutie pinu, resp. nastavenie stavu 1
def vypni_pin(pin):
    GPIO.output(pin, 1)

# * Funkcia na zapnutie pinu, resp. nastavenie stavu 0
def zapni_pin(pin):
    GPIO.output(pin, 0)