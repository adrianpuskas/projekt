import time
import requests
from logovanie import log
FVEtoken = "Gurl2O0DoNv46y8iKKJmNTx1w15NLJ7l"
TopenieToken = "JT_8ua2rn-cxt1JlkCHIIa7cSK-Rykmz"
AutomatizaciaToken = '36W1yAdnJsAzpH7UUR5CzwrFjDKOdyjK'

# Parametrizovanie Blynk Vpinov FVE
inverter_mode = FVEtoken, 1
ohrev_vypinac = FVEtoken, 20
ohrev_play_stop = FVEtoken, 19
nastaveny_vykon_ohrevu = FVEtoken, 7    
bateria_vykon = FVEtoken, 75
panely_vykon = FVEtoken, 76
zataz_vykon = FVEtoken, 65
panely_napatie = FVEtoken, 73
bateria_kapacita = FVEtoken, 70
menic_teplota = FVEtoken, 71
automatika = FVEtoken, 8

vonkajsia_teplota = TopenieToken, 56
teplota_tuv = TopenieToken, 0

def write(token, pin, value):
    api_url = "https://blynk.cloud/external/api/update?token=" + token + "&V" + str(pin) + "=" + str(value)
    response = requests.get(api_url)
    return response.content.decode()
    time.sleep(0.1)
    
def read(token, pin):
    api_url = "https://blynk.cloud/external/api/get?token=" + token + "&V" + str(pin)
    response = requests.get(api_url)
    return response.content.decode()
    time.sleep(0.1)

def read_float(token, pin):
    api_url = "https://blynk.cloud/external/api/get?token=" + token + "&V" + str(pin)
    response = requests.get(api_url)
    return float(response.content.decode())
    time.sleep(0.1)

def read_string(token, pin):
    api_url = "https://blynk.cloud/external/api/get?token=" + token + "&V" + str(pin)
    response = requests.get(api_url)
    return str(response.content.decode())
    time.sleep(0.1)


def nacitanie_hodnôt_automatizacie():
    #Nastavenie hodnôt panelov
    global string_MPV
    panel_OV = float(read(AutomatizaciaToken, 0))
    panel_MPV = float(read(AutomatizaciaToken, 1))
    string_pcs = int(read(AutomatizaciaToken, 2))
    string_OV = panel_OV*string_pcs
    string_MPV = panel_MPV*string_pcs

    # Výkonové hranice
    global MIN_VYKON
    MIN_VYKON = int(read(AutomatizaciaToken, 3))
    print (f" | MIN_VYKON - {MIN_VYKON}%")
    
    global MAX_VYKON
    MAX_VYKON = int(read(AutomatizaciaToken, 4))
    print (f" | MAX_VYKON - {MAX_VYKON}%")
    
    global VYKON_KROK
    VYKON_KROK = int(read(AutomatizaciaToken, 5))       # - O koľko % sa mení výkon
    print (f" | VYKON_KROK - {VYKON_KROK}%")
    
    global BAT_CAP_ON
    BAT_CAP_ON = int(read(AutomatizaciaToken, 6))       # -  Od akej kapacity sa zapína ohrev
    print (f" | BAT_CAP_ON - {BAT_CAP_ON}%")
    
    global MIN_BATT_POWER_FOR_START
    MIN_BATT_POWER_FOR_START = int(read(AutomatizaciaToken, 7))      # - Minimalny bateriovy vykon na to aby sa zapol ohrev .. 
    print (f" | MIN_BATT_POWER_FOR_START - {MIN_BATT_POWER_FOR_START}W")
    
    global BAT_MAX_DISCHARGE
    BAT_MAX_DISCHARGE = int(read(AutomatizaciaToken, 8))    # - Maximálne vybíjanie batérie pred znížením výkonu
    print (f" | BAT_MAX_DISCHARGE - {BAT_MAX_DISCHARGE}W")
    
    global BAT_MAX_DISCHARGE2
    BAT_MAX_DISCHARGE2 = int(read(AutomatizaciaToken, 9))   # - Maximálne vybíjanie batérie pred znížením výkonu
    print (f" | BAT_MAX_DISCHARGE2 - {BAT_MAX_DISCHARGE2}W")
    
    global BAT_SAFE_RANGE
    BAT_SAFE_RANGE = int(read(AutomatizaciaToken, 10))  # - Ak je výkon batérie medzi -BAT_MAX_DISCHARGE a +BAT_SAFE_RANGE, nemeníme výkon
    print (f" | BAT_SAFE_RANGE - {BAT_SAFE_RANGE}W")
    
    global BAT_HARD_LIMIT
    BAT_HARD_LIMIT = int(read(AutomatizaciaToken, 11))  # - Ak batéria dodáva viac ako 2500W, vypnúť ohrev
    print (f" | BAT_HARD_LIMIT - {BAT_HARD_LIMIT}W")
    
    global MAX_ZATAZ_VYKON
    MAX_ZATAZ_VYKON = int(read(AutomatizaciaToken, 12)) # - Rezerva pre ďalšie spotrebiče
    print (f" | MAX_ZATAZ_VYKON - {MAX_ZATAZ_VYKON}W")
    
    global LIMIT_VYP_ZATAZ
    LIMIT_VYP_ZATAZ = int(read(AutomatizaciaToken, 13)) # - Kedy sa ohrev vypne
    print (f" | LIMIT_VYP_ZATAZ - {LIMIT_VYP_ZATAZ}W")
    
    global LIMIT_ZAP_ZATAZ
    LIMIT_ZAP_ZATAZ = int(read(AutomatizaciaToken, 14)) # - Kedy sa ohrev môže znova zapnúť
    print (f" | LIMIT_ZAP_ZATAZ - {LIMIT_ZAP_ZATAZ}W")
    time.sleep(1)
    
    write(AutomatizaciaToken, 15, 0) ## Vrat tlacidlo nacitania do povodneho stavu 
  
  
dlhodobe_nizke_vykonanie_cas = None
# Nastavenie časového limitu pre znovuzapnutie ohrevu (napr. 60 sekúnd)
COOLDOWN_TIME = 60
cas_vypnutia_ohrevu = None


ohrev_nedavno_vypnuty = False

def moze_sa_zapnut_ohrev():
    global cas_vypnutia_ohrevu
    if cas_vypnutia_ohrevu is None:
        return True
    elif time.time() - cas_vypnutia_ohrevu >= COOLDOWN_TIME:
        return True
    else:
        print("Nedá sa spustiť ohrev - nedávno bol vypnutý.")
        return False
    
def calculate_new_power(vykon_bateria, vykon_ohrevu):
    # Výpočet potrebnej zmeny výkonu
    potrebna_zmena = abs(vykon_bateria) / 2000 * 100  # % podla odberu z batérie
    
    if vykon_bateria < BAT_MAX_DISCHARGE:  # Batéria sa vybíja príliš rýchlo
        new_power = max(vykon_ohrevu - potrebna_zmena, MIN_VYKON)
    elif vykon_bateria > BAT_SAFE_RANGE:  # Môžeme pridať výkon
        new_power = min(vykon_ohrevu + potrebna_zmena, MAX_VYKON)
    else:
        new_power = vykon_ohrevu  # Žiadna zmena
    
    # Zaokrúhlenie na kalibračné body
    if new_power <= 37:
        new_power = 25
    elif new_power <= 62:
        new_power = 50
    else:
        new_power = 75
    
    return int(new_power)  # Zaokrúhľujeme na celé %


print ("Nacitavam hodnoty nastavene pre riadenie ohrevu v Blynk - Automatizácia ")
nacitanie_hodnôt_automatizacie()
MIN_VYKON_START = 25
moze_sa_zapnut_ohrev()

# Hlavná slučka
while True:
    if int(read(AutomatizaciaToken, 15)) == 1: # Kontrola tlacidla na aktualizaciu hodnôt automatizacie
        print ("Nacitavam hodnoty nastavene pre riadenie ohrevu v Blynk - Automatizácia ")
        nacitanie_hodnôt_automatizacie()
    print("...............................................")
    vonkajsia_teplota_read = read(*vonkajsia_teplota)
    print(f"Vonkajšia teplota {vonkajsia_teplota_read}°C")
    write(FVEtoken,4, vonkajsia_teplota_read)
    teplota_tuv_read = read(*teplota_tuv)
    print(f"Teplota TUV {teplota_tuv_read}°C")
    write(FVEtoken, 9, teplota_tuv_read)
    print("...............................................")
    print("...............................................")
    
    if int(read(*automatika)) == 1: # ak je navolena automatika (FVE)
        try:
            #data = get_shared_data()
            
            print ("Automatický režim riadenia ohrevu")
            napatie_panely = int(read(*panely_napatie))
            #napatie_panely = data.get("pv_voltage", 0)

            teplota_menica = int(read(*menic_teplota))    
            #teplota_menica = data.get("inverter_temp", 0)
            if napatie_panely > 50 and teplota_menica > 1:
                read_inverter_mode = (read(*inverter_mode))
                
                if read_inverter_mode == "Battery":
                    print ("Režim invertora - Battery")    
                
                    # Čítanie hodnôt
                    vykon_panely = int(read(*panely_vykon))
                    vykon_zataz = int(read(*zataz_vykon))
                    vykon_bateria = int(read(*bateria_vykon))
                    kapacita_bateria = int(read(*bateria_kapacita))
                    
                    stav_ohrevu = int(read(*ohrev_vypinac))
                    vykon_ohrevu = int(read(*nastaveny_vykon_ohrevu))
                    priorita_FVE = int(read(AutomatizaciaToken, 16)) ## 0 - bateria / 1 - TUV
                    if priorita_FVE == 0:
                        print ("Priorita - Batéria")
                    elif priorita_FVE == 1:
                        print ("Priorita - TUV")
                        
                    print(f"PV {napatie_panely}V, PV {vykon_panely}W, \nINV {teplota_menica}°C, INV {vykon_zataz}W, \nBATT {vykon_bateria}W, BATT {kapacita_bateria}%")  
                    moze_sa_zapnut_ohrev()
                    if stav_ohrevu == 0:
                        print("Ohrev vypnutý")
                        
                        if stav_ohrevu == 0 and vykon_bateria < BAT_MAX_DISCHARGE:
                            print(f"Bateria sa vybija, nemozem zapnut ohrev. {vykon_bateria}W")
                            pass                          

                        elif priorita_FVE == 0 and (vykon_bateria > MIN_BATT_POWER_FOR_START or napatie_panely > string_MPV) and vykon_zataz < LIMIT_ZAP_ZATAZ and kapacita_bateria >= BAT_CAP_ON and stav_ohrevu == 0 and moze_sa_zapnut_ohrev():
                            write(*ohrev_vypinac, 1)
                            write(*nastaveny_vykon_ohrevu, MIN_VYKON_START)
                            #ohrev_nedavno_vypnuty = False
                            print (f"Priorita využitia FVE - Batéria")
                            print(f"Zapínam ohrev na {MIN_VYKON_START}%")
                            print(f"- Záťaž klesla pod nastavený limit {LIMIT_ZAP_ZATAZ}W\n     Výkon záťaže ({vykon_zataz}W)")
                            print(f"- Kapacita batérie nad  {BAT_CAP_ON}%")
                            
                        elif priorita_FVE == 1 and (vykon_bateria > MIN_BATT_POWER_FOR_START or napatie_panely > string_MPV) and vykon_zataz < LIMIT_ZAP_ZATAZ and stav_ohrevu == 0 and moze_sa_zapnut_ohrev():
                            write(*ohrev_vypinac, 1)
                            write(*nastaveny_vykon_ohrevu, MIN_VYKON_START)
                            #ohrev_nedavno_vypnuty = False
                            print (f"Priorita využitia FVE - TUV")
                            print(f"Zapínam ohrev na {MIN_VYKON_START}%")
                            print(f"- Záťaž klesla pod nastavený limit {LIMIT_ZAP_ZATAZ}W\n     Výkon záťaže ({vykon_zataz}W)")                           
                            
                        else:
                            print(f"Nesplnené požiadavky pre zapnutie ohrevu")
                            if vykon_zataz > LIMIT_ZAP_ZATAZ:                             
                                print(f"- Záťaž presahuje nastavený limit {LIMIT_ZAP_ZATAZ}W\n     Výkon záťaže {vykon_zataz}W")
                            if kapacita_bateria < BAT_CAP_ON:
                                print(f"- Kapacita batérie pod nastavenú hranicu {BAT_CAP_ON}%\n     Kapacita batérie {kapacita_bateria}%")
                        time.sleep(2)
                        
                    else: ## stav ohrevu 1 ohrev zapnutý
                        if priorita_FVE == 0 and kapacita_bateria < BAT_CAP_ON: ## 0 - bateria / 1 - TUV
                            print(f"- Kapacita batérie pod nastavenú hranicu {BAT_CAP_ON}%\n     Kapacita batérie {kapacita_bateria}%")
                            write(*nastaveny_vykon_ohrevu, MIN_VYKON)
                            write(*ohrev_vypinac, 0)
                            cas_vypnutia_ohrevu = time.time()
                            print("Ohrev vypnutý")
                            
                            
                        elif vykon_zataz > LIMIT_VYP_ZATAZ and stav_ohrevu == 1:
                            write(*nastaveny_vykon_ohrevu, MIN_VYKON_START)
                            write(*ohrev_vypinac, 0)
                            cas_vypnutia_ohrevu = time.time()
                            print(f"Vypínam ohrev - výkon záťaže ({vykon_zataz}W) presiahol nastavených {LIMIT_VYP_ZATAZ}W")
                        else:
                            print (f"Ohrev zapnutý na {vykon_ohrevu}%")
                            #if vykon_zataz < MAX_ZATAZ_VYKON:
                            if vykon_zataz+150 < MAX_ZATAZ_VYKON and ((BAT_MAX_DISCHARGE > vykon_bateria > BAT_SAFE_RANGE) or (vykon_bateria > BAT_SAFE_RANGE or (kapacita_bateria >= BAT_CAP_ON and napatie_panely > string_MPV)) and vykon_ohrevu < MAX_VYKON):
                                new_power = min(vykon_ohrevu + VYKON_KROK, MAX_VYKON)
                                write(*nastaveny_vykon_ohrevu, new_power)
                                print(f"Zvyšujem ohrev na {new_power}%")
                                time.sleep(1.5)  # Pomalšie zvyšovanie výkonu
                                    
                            elif vykon_zataz > LIMIT_VYP_ZATAZ and stav_ohrevu == 1:
                                write(*nastaveny_vykon_ohrevu, MIN_VYKON_START)
                                write(*ohrev_vypinac, 0)
                                cas_vypnutia_ohrevu = time.time()
                                print(f"Vypínam ohrev\n - výkon záťaže ({vykon_zataz}W) presiahol nastavených {LIMIT_VYP_ZATAZ}W")
                                
                            elif vykon_bateria < BAT_HARD_LIMIT and stav_ohrevu == 1:
                                write(*nastaveny_vykon_ohrevu, MIN_VYKON_START)
                                write(*ohrev_vypinac, 0)
                                cas_vypnutia_ohrevu = time.time()
                                print(f"Vypínam ohrev\n - výkon z batérie ({vykon_bateria}W) presiahol nastavený limit pre zníženie výkonu {BAT_HARD_LIMIT}W")
                                
                            elif vykon_bateria < BAT_MAX_DISCHARGE2:
                                new_power = calculate_new_power(vykon_bateria, vykon_ohrevu)
                                write(*nastaveny_vykon_ohrevu, new_power)
                                print(f"Dynamické zníženie výkonu na {new_power}% \n Výkon záťaže - {vykon_zataz}W")
                            
                            elif stav_ohrevu == 1 and vykon_ohrevu > MIN_VYKON and (vykon_zataz > MAX_ZATAZ_VYKON) or (vykon_bateria < BAT_MAX_DISCHARGE):
                                if vykon_zataz > MAX_ZATAZ_VYKON:
                                    print (f"Výkon ({vykon_zataz}W) presiahol bezpečnú hranicu {MAX_ZATAZ_VYKON}W, znižujem výkon ohrevu")
                                if vykon_bateria < BAT_MAX_DISCHARGE:
                                    print (f"Výkon z batérie ({vykon_bateria}W) presiahol nastavený limit pre zníženie výkonu {BAT_MAX_DISCHARGE}W")
                                new_power = max(vykon_ohrevu - VYKON_KROK, MIN_VYKON)
                                write(*nastaveny_vykon_ohrevu, new_power)
                                print(f"Znižujem ohrev na {new_power}%")
                                
                                
                            #if vykon_ohrevu <= MIN_VYKON_START and vykon_bateria < BAT_MAX_DISCHARGE:
                            if vykon_bateria < BAT_MAX_DISCHARGE:    
                                if dlhodobe_nizke_vykonanie_cas is None:
                                    dlhodobe_nizke_vykonanie_cas = time.time()
                                elif time.time() - dlhodobe_nizke_vykonanie_cas > 60:
                                    if int(read(*bateria_vykon)) < BAT_MAX_DISCHARGE:
                                        write(*ohrev_vypinac, 0)
                                        cas_vypnutia_ohrevu = time.time()
                                        print("Vypínam ohrev - dlhodobé nadmerné vybíjanie batérie!")
                                    else:
                                        dlhodobe_nizke_vykonanie_cas = None
                            else:
                                dlhodobe_nizke_vykonanie_cas = None
            
                    time.sleep(0.5)
                    
            else:
                print("Porucha pri čítaní dát zo servera, skontroluj funkčnosť kódu FVE")
                write(*nastaveny_vykon_ohrevu, MIN_VYKON)
                write(*ohrev_vypinac, 0)
                cas_vypnutia_ohrevu = time.time()
                print(f"Vypínam ohrev - menič pravdepodobne nekomunikuje správne")
                time.sleep(2)
                continue         
           
        except Exception as e:
            print (e)
            write(*nastaveny_vykon_ohrevu, MIN_VYKON)
            write(*ohrev_vypinac, 0)
            cas_vypnutia_ohrevu = time.time()
            print(f"Vypínam ohrev - menič pravdepodobne nekomunikuje správne")
            time.sleep(2)
            continue
    else:
        print("Manuálny režim...")
        time.sleep(3)

