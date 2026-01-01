
import BlynkLib  # pip3 install blynk-library-python ## Pre blynk zapisovanie
import time
import requests  ## pre Blynk citanie

#### Blynk nastavenie
token = "Gurl2O0DoNv46y8iKKJmNTx1w15NLJ7l"
blynk = BlynkLib.Blynk(token, server='blynk.cloud')


# Funkcia na kontrolu pripojenia k internetu
def wait_for_internet_connection():
    """Funkcia počká, kým sa zariadenie nepripojí k internetu."""
    while True:
        try:
            requests.get("https://blynk.cloud", timeout=5)
            print("Pripojenie obnovené!")
            return
        except requests.ConnectionError:
            print("Čakám na obnovenie pripojenia k internetu...")
            time.sleep(5)
            

def blynk_write(blynkPin, blynkValue):
    blynk.virtual_write(blynkPin, blynkValue)
    #print (f"Zapisana hodnota {blynkValue} cez funkciu blynk_weite na pin V{blynkPin}")
    
def blynk_set_property(blynkPin, widgetProperty, propertyValue):
    blynk.set_property(blynkPin, widgetProperty, propertyValue)  # biela
    print (f"BLYNK SET PROPERTY na pin V{blynkPin}")
  
  
    
#### CITANIE & ZAPIS POMOCOU URL REQUESTS ###
    
def blynk_read(pin):
    api_url = "https://blynk.cloud/external/api/get?token=" + token + "&" + pin
    response = requests.get(api_url)
    return response.content.decode()


def blynk_read_float(pin):
    api_url = "https://blynk.cloud/external/api/get?token=" + token + "&" + pin
    response = requests.get(api_url)
    return float(response.content.decode())


def blynk_read_string(pin):
    api_url = "https://blynk.cloud/external/api/get?token=" + token + "&" + pin
    response = requests.get(api_url)
    return str(response.content.decode())

def blynk_url_write(pin, data):
    api_url = "http://blynk.cloud/external/api/update?token=" + token + "&" + pin + "=" + data
    #api_url = "https://blynk.cloud/external/api/get?token=" + token + "&" + pin
    response = requests.get(api_url)
    return str(response.content.decode())