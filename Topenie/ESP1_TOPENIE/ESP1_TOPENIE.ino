
#define BLYNK_TEMPLATE_ID "TMPL4kDwpWu-n"
#define BLYNK_TEMPLATE_NAME "Topenie Osikov"
#define BLYNK_AUTH_TOKEN "JT_8ua2rn-cxt1JlkCHIIa7cSK-Rykmz"
#define BLYNK_PRINT Serial  // používanie sériového výstupu pre Blynk

#include <WiFi.h>  // WiFi knižnica pre ESP32
#include <WiFiClient.h>
#include <BlynkSimpleEsp32.h>  // Blynk knižnica pre ESP32
#include <OneWire.h>
#include <DallasTemperature.h>
#include <HTTPClient.h>


char auth[] = BLYNK_AUTH_TOKEN;  // inicializácia premennej pre autentifikáciu
char ssid[] = "ESP";  // meno Wi-Fi siete
char pass[] = "202PuskaS";  // heslo Wi-Fi siete

//#define SENSOR1_PIN 4 // VODA
//#define SENSOR2_PIN 2 // KOTOL
//#define SENSOR3_PIN 15// DYMOVOD

#define ONE_WIRE_BUS 15

// Inicializácia OneWire pre každý senzor
//OneWire oneWire1(SENSOR1_PIN);
//OneWire oneWire2(SENSOR2_PIN);
//OneWire oneWire3(SENSOR3_PIN);

// Inicializácia DallasTemperature pre každý senzor
//DallasTemperature sensor1(&oneWire1);
//DallasTemperature sensor2(&oneWire2);
//DallasTemperature sensor3(&oneWire3);

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// #define ONE_WIRE_BUS 4    // Data vodič je pripojený na pin 4 na Arduine
#define RELAY_PUMP 5   // Digitálny pin na riadenie čerpadla
#define RELAY_VALVE 17  // Digitálny pin na riadenie elektroventilu TUV
#define RELAY_VALVE_RADIATOR 18   // Digitálny pin na riadenie elektroventila radiatorov


BlynkTimer timer; // vytvorenie objektu BlynkTimer pre použitie časovača


int manualMode;
int wifiStatus;

float teplotaVody;
float teplotaKotla;
float teplotaDymovodu;

int tlacidlo_cerpadlo;
int tlacidlo_ventil;
int tlacidlo_ventil_radiator;

int cerpadlo_slider_min;
int cerpadlo_slider_max;

int nastavena_teplota_dymovodu;

float ventil_slider_pom;
float cerpadlo_slider_pom;

int nastavena_teplota_vody;
int toleranciaTUV;
int prevadzkova_kotol;
int prevadzkova_kotol_TUV;

int status_TUV_1 = 0;
int status_TUV_2 = 0;

int lastMode = 0;

// Blynk manual/auto
BLYNK_WRITE(V5) {
  int value = param.asInt();

  manualMode = value;
  Blynk.virtualWrite(V5, value);
}


// Blynk čerpadlo
BLYNK_WRITE(V2) {
  if (manualMode == 1) {
    int value = param.asInt();
  
    tlacidlo_cerpadlo = value;
  
    if (tlacidlo_cerpadlo == 0) {
      digitalWrite(RELAY_PUMP, LOW);
    } else  {
      digitalWrite(RELAY_PUMP, HIGH);
    }
  }
  else {
    Serial.println("Tlačidlo sa neda stlačiť v automatickom mode");
  }
}

// Blynk ventil
BLYNK_WRITE(V3) {
   if (manualMode == 1) {
    int value = param.asInt();
  
    tlacidlo_ventil = value;
  
    if (tlacidlo_ventil == 0) {
      digitalWrite(RELAY_VALVE, LOW);
    } else  {
      digitalWrite(RELAY_VALVE, HIGH);
    }
  } 
  else {
    Serial.println("Tlačidlo sa neda stlačiť v automatickom mode");
  }
}

// Blynk ventil RELAY_VALVE_RADIATOR
BLYNK_WRITE(V12) {
   if (manualMode == 1) {
      int value = param.asInt();
    
      tlacidlo_ventil_radiator = value;
    
      if (tlacidlo_ventil_radiator == 0) {
        digitalWrite(RELAY_VALVE_RADIATOR, LOW);
      } else  {
        digitalWrite(RELAY_VALVE_RADIATOR, HIGH);
      }
    }
  else {
    Serial.println("Tlačidlo sa neda stlačiť v automatickom mode");
  }
}


// Blynk nastavena teplota vody
BLYNK_WRITE(V24) {
  int value = param.asInt();
  nastavena_teplota_dymovodu = value;
}


// Blynk priorita topenia
BLYNK_WRITE(V13) {
  int value = param.asInt();
  lastMode = value;
}


// Blynk wifi status
BLYNK_WRITE(V4) {
  int value = param.asInt();

  if (value == 0) {
    Blynk.logEvent("wifi", "Pripojenie na Wi-Fi zlyhalo!") ;
    wifiStatus = 0;
    Blynk.setProperty(V4, "color", "f04a29");
  } else {
    wifiStatus = 1;
    Blynk.setProperty(V4, "color", "#71d459");
  }
}

// Nastavena tolerancia TUV
BLYNK_WRITE(V6) {
  int value = param.asInt();

  toleranciaTUV = value;
  Blynk.virtualWrite(V6, value);
}

// Blynk čerpadlo max
BLYNK_WRITE(V7) {
  int value = param.asInt();
  cerpadlo_slider_max = value;
}

// Blynk nastavena teplota vody
BLYNK_WRITE(V8) {
  int value = param.asInt();
  nastavena_teplota_vody = value;
}

// Blynk čerpadlo min
BLYNK_WRITE(V11) {
  int value = param.asInt();
  cerpadlo_slider_min = value;
}

// Blynk prevadzkova
BLYNK_WRITE(V16) {
  int value = param.asInt();
  prevadzkova_kotol = value;
}

// Blynk prevadzkova
BLYNK_WRITE(V17) {
  int value = param.asInt();
  prevadzkova_kotol_TUV = value;
}



void coloring() {

  sensors.requestTemperatures();
  teplotaVody = sensors.getTempCByIndex(0);
  teplotaKotla = sensors.getTempCByIndex(2);
  teplotaDymovodu = sensors.getTempCByIndex(1);
  //sensor1.requestTemperatures();
  //sensor2.requestTemperatures();
  //sensor3.requestTemperatures();

  // Prečítaj hodnoty z každého senzora
  //float teplotaVody = sensor1.getTempCByIndex(0);
  //float teplotaKotla = sensor2.getTempCByIndex(0);
  //float teplotaDymovodu = sensor3.getTempCByIndex(0);


  if (isnan(teplotaKotla)) {
    Serial.println("Chyba pri čítaní z prvého DS18B20 snímača!");
    return;
  }
  if (isnan(teplotaVody)) {
    Serial.println("Chyba pri čítaní z druhého DS18B20 snímača!");
    return;
  }

  if (isnan(teplotaDymovodu)) {
    Serial.println("Chyba pri čítaní z tretieho DS18B20 snímača!");
    return;
  }
  
  if (teplotaKotla < 0 || teplotaKotla > 150) {
    Serial.println("Chybná hodnota pre teplotu kotla!");
    return;
  }

  if (teplotaVody < 0 || teplotaVody > 100) {
    Serial.println("Chybná hodnota pre teplotu vody!");
    return;
  }

  if (teplotaDymovodu < 0 || teplotaDymovodu > 180) {
    Serial.println("Chybná hodnota pre teplotu dymovodu!");
    return;
  }

  if (teplotaVody == teplotaKotla) {
    Serial.println("Chybná hodnota pre teploty!");
    return;
  }

  if (teplotaDymovodu == teplotaKotla) {
    Serial.println("Chybná hodnota pre teploty!");
    return;
  }

  if (teplotaVody == teplotaDymovodu) {
    Serial.println("Chybná hodnota pre teploty!");
    return;
  }

  Blynk.virtualWrite(V10, teplotaKotla);
  Blynk.virtualWrite(V9, teplotaVody);

  if (teplotaKotla <= 30) {                                                //modra
    Blynk.setProperty(V10, "color", "#3b64d4");
  } else if (teplotaKotla > 30 && teplotaKotla <= 45) {                    //zlta
    Blynk.setProperty(V10, "color", "#ffe226");
  } else if (teplotaKotla > 45 && teplotaKotla <= 65) {                    //zelena
    Blynk.setProperty(V10, "color", "#71d459");
  } else if (teplotaKotla > 65 && teplotaKotla <= 80) {                    //oranzova
    Blynk.setProperty(V10, "color", "#fab339");
  } else {                                                                 //cervena
    Blynk.setProperty(V10, "color", "#f04a29");
  }

  if (teplotaVody <= 35) {                                                 //modra
    Blynk.setProperty(V9, "color", "#3b64d4");
  } else if (teplotaVody > 35 && teplotaVody <= 50) {                      //zelena
    Blynk.setProperty(V9, "color", "#71d459");
  } else if (teplotaVody > 50 && teplotaVody <= 60) {                      //oranzova
    Blynk.setProperty(V9, "color", "#fab339");
  } else {                                                                 //cervena
    Blynk.setProperty(V9, "color", "#f04a29");
  }
}

//Ak je teplota TUV už DOSIAHNUTÁ, nastav prevádzhovú teplotu kotla podľa nastavenia v BLYNK
unsigned long cas_zapnutia_ventilu = 0; // Uchováva čas, kedy sa má ventil zapnúť
bool ventil_zapnute = false; // Sledovanie stavu ventilu


// FUNKCIA PRE RIADENIE POZADOVANEJ TEPLOTY KOTLA V AUTOMATIKE
void TUVcontrol() {

  //Ak je teplota TUV ešte nedosiahnutá, nastav prevádzhovú teplotu kotla podľa nastavenia v BLYNK
  if (lastMode == 1 && status_TUV_1 == 0) { // 0 = Radiatory ; 1 = TUV
    status_TUV_1 = 1;
    status_TUV_2 = 0;
    HTTPClient http;
    // Vytvorenie URL s tokenom, virtuálnym pinom a hodnotou
    String url3 = "https://blynk.cloud/external/api/update?token=Mrf5LJuXlXRyqIz46IKkbgeZAfXC0q8x&V0=";
    url3 += String(prevadzkova_kotol_TUV);
    Serial.print("\nSending Blynk update: ");
    Serial.println(url3);
    http.begin(url3);
    int httpCode3 = http.GET();
    // Skontrolovanie, či sa požiadavka úspešne odoslala
    if (httpCode3 > 0) {
      Serial.printf("HTTP Response code: %d\n", httpCode3);
    } else {
      Serial.printf("HTTP GET failed: %s\n", http.errorToString(httpCode3).c_str());
    }
    // Ukončenie spojenia
    http.end();
    Serial.print("\nNastavená prevádzková teplota kotla ");
    Serial.print(prevadzkova_kotol_TUV);
    Serial.print("°C");
  } else {
    Serial.print("\n ");
  }



  if (lastMode == 0 && status_TUV_2 == 0) { // 0 = Radiatory ; 1 = TUV
    status_TUV_1 = 0;
    status_TUV_2 = 1;
    HTTPClient http;

    // Vytvorenie URL s tokenom, virtuálnym pinom a hodnotou
    String url4 = "https://blynk.cloud/external/api/update?token=Mrf5LJuXlXRyqIz46IKkbgeZAfXC0q8x&V0=";
    url4 += String(prevadzkova_kotol);
    Serial.print("Sending Blynk update: ");
    Serial.println(url4);
    http.begin(url4);
    int httpCode4 = http.GET();
    // Skontrolovanie, či sa požiadavka úspešne odoslala
    if (httpCode4 > 0) {
      Serial.printf("HTTP Response code: %d\n", httpCode4);
    } else {
      Serial.printf("HTTP GET failed: %s\n", http.errorToString(httpCode4).c_str());
    }
    // Ukončenie spojenia
    http.end();
    Serial.print("\nNastavená prevádzková teplota kotla ");
    Serial.print(prevadzkova_kotol);
    Serial.print("°C");
  }
}

unsigned long cas_zapnutia_eletroventilu = 0; // Uchováva čas pre zapnutie ventilu
bool eletroventil_tuv_vypnuty = false; // Sledovanie stavu ventilu


void updateBlynkPins() {
  if (manualMode == 0) { // Len v automatickom režime
    // Pre RELAY_PUMP
    if (digitalRead(RELAY_PUMP) == LOW) { // LOW = zapnuté
      Blynk.virtualWrite(V2, 1);
    } else {
      Blynk.virtualWrite(V2, 0);
    }

    // Pre RELAY_VALVE_RADIATOR
    if (digitalRead(RELAY_VALVE) == LOW) { // LOW = zapnuté
      Blynk.virtualWrite(V3, 1);
    } else {
      Blynk.virtualWrite(V3, 0);
    }

    // Pre RELAY_VALVE
    if (digitalRead(RELAY_VALVE_RADIATOR) == LOW) { // LOW = zapnuté
      Blynk.virtualWrite(V12, 1);
    } else {
      Blynk.virtualWrite(V12, 0);
    }

    // Pre lastMode
    if ((lastMode) == 1) { // 0 = Radiatory ; 1 = TUV
      Blynk.virtualWrite(V13, 1);
    } else {
      Blynk.virtualWrite(V13, 0);
    } 
  }
}



// *** RIADIACA FUNKCIA  ***
void sendSensor() {

  //aktualizácia wifi
  Blynk.virtualWrite(V4, 1);

  sensors.requestTemperatures();
  teplotaVody = sensors.getTempCByIndex(0);
  teplotaKotla = sensors.getTempCByIndex(2);
  teplotaDymovodu = sensors.getTempCByIndex(1);
  //sensor1.requestTemperatures();
  //sensor2.requestTemperatures();
  //sensor3.requestTemperatures();

  // Prečítaj hodnoty z každého senzora
  //float teplotaVody = sensor1.getTempCByIndex(0);
  //float teplotaKotla = sensor2.getTempCByIndex(0);
  //float teplotaDymovodu = sensor3.getTempCByIndex(0);

  if (isnan(teplotaKotla)) {
    Serial.println("Chyba pri čítaní z prvého DS18B20 snímača!");
    return;
  }
  if (isnan(teplotaVody)) {
    Serial.println("Chyba pri čítaní z druhého DS18B20 snímača!");
    return;
  }

  if (isnan(teplotaDymovodu)) {
    Serial.println("Chyba pri čítaní z tretieho DS18B20 snímača!");
    return;
  }
  
  if (teplotaKotla < 0 || teplotaKotla > 150) {
    Serial.println("Chybná hodnota pre teplotu kotla!");
    return;
  }

  if (teplotaVody < 0 || teplotaVody > 100) {
    Serial.println("Chybná hodnota pre teplotu vody!");
    return;
  }

  if (teplotaDymovodu < 0 || teplotaDymovodu > 180) {
    Serial.println("Chybná hodnota pre teplotu dymovodu!");
    return;
  }

  if (teplotaVody == teplotaKotla) {
    Serial.println("Chybná hodnota pre teploty!");
    return;
  }

  if (teplotaDymovodu == teplotaKotla) {
    Serial.println("Chybná hodnota pre teploty!");
    return;
  }

  if (teplotaVody == teplotaDymovodu) {
    Serial.println("Chybná hodnota pre teploty!");
    return;
  }

  Blynk.virtualWrite(V1, teplotaKotla);
  Blynk.virtualWrite(V0, teplotaVody);
  Blynk.virtualWrite(V19, teplotaDymovodu);

  // Ak sme v režime "Automatika", vykonáme logiku pre riadenie
// Ak sme v režime "Automatika", vykonáme logiku pre riadenie
    if (manualMode == 0) {
      Serial.println("\n*** AUTOMATICKÝ REŽIM ***");
    
      //if ((teplotaKotla >= cerpadlo_slider_max) || ((teplotaDymovodu-2) >= nastavena_teplota_dymovodu)) { // ak teplota kotla je vyšša než nastavena + ak teplota dymovodu je o 2°C vyššia
      if (teplotaDymovodu-2 >= nastavena_teplota_dymovodu) { // ak teplota dymovodu je o 2°C vyššia
        Serial.println("---> Čerpadlo zapnuté");
        Blynk.logEvent("obehove_cerpadlo_on", "Obehové čerpadlo je zapnuté");
        digitalWrite(RELAY_PUMP, LOW); // LOW - zapnuté ; HIGH - vypnuté
    
        TUVcontrol();

        
        if (teplotaKotla >= 85) { // bezpečnostné opatrenie
          digitalWrite(RELAY_VALVE, LOW);
          digitalWrite(RELAY_VALVE_RADIATOR, LOW);
          Serial.println("---> Elektroventily zapnuté");
          Blynk.logEvent("vysoka_teplota", "Teplota kotla je vyššia ako 85 °C !!!");

        } else {
          if (teplotaVody >= nastavena_teplota_vody) {
            lastMode = 0; // 0 = Radiatory ; 1 = TUV
            if (!eletroventil_tuv_vypnuty) {
              // Nastavte čas začiatku čakania, ak ešte nebol zaznamenaný
              if (cas_zapnutia_eletroventilu == 0) {
                cas_zapnutia_eletroventilu = millis();
              }
    
              // Skontrolujte, či uplynuli 2 minúty (120000 ms)
              if (millis() - cas_zapnutia_eletroventilu >= 120000) {
                digitalWrite(RELAY_VALVE, HIGH); // LOW - zapnuté ; HIGH - vypnuté
                Serial.println("---> Elektroventil TUV vypnutý");
                digitalWrite(RELAY_VALVE_RADIATOR, LOW); // LOW - zapnuté ; HIGH - vypnuté
                Serial.println("---> Elektroventil RADIÁTOROV zapnutý");
    
                eletroventil_tuv_vypnuty = true; // Zaznamenajte, že ventil bol vypnutý
                cas_zapnutia_eletroventilu = 0; // Reset času
              }
            }
            digitalWrite(RELAY_VALVE_RADIATOR, LOW); // LOW - zapnuté ; HIGH - vypnuté
            Serial.println("---> Elektroventil RADIÁTOROV zapnutý");
    
          } else if (teplotaVody < (nastavena_teplota_vody - toleranciaTUV)) {
            
             if (teplotaDymovodu < nastavena_teplota_dymovodu){ // ak je dymovod zimny, prepni na radiatory a potom podla teploty kotla vypne cerpadlo
                lastMode = 0; // 0 = Radiatory ; 1 = TUV
                Serial.println("---> NEDOSTATOCNA TEPLOTA SPALIN NA TO, ABY SA HRIALA TUV");
                // Resetujte stav ventilu a čas pri prechode do druhého bloku
                eletroventil_tuv_vypnuty = false;
                cas_zapnutia_eletroventilu = 0;
                digitalWrite(RELAY_VALVE, HIGH); // LOW - zapnuté ; HIGH - vypnuté
                digitalWrite(RELAY_VALVE_RADIATOR, LOW); // LOW - zapnuté ; HIGH - vypnuté
                Serial.println("---> Elektroventil TUV vypnutý - TEPLOTA DYMOVODU");
                Serial.println("---> Elektroventil RADIÁTOROV zapnutý - TEPLOTA DYMOVODU");
                }
                
              else {
                lastMode = 1; // 0 = Radiatory ; 1 = TUV
                // Resetujte stav ventilu a čas pri prechode do druhého bloku
                eletroventil_tuv_vypnuty = false;
                cas_zapnutia_eletroventilu = 0;
        
                digitalWrite(RELAY_VALVE, LOW); // LOW - zapnuté ; HIGH - vypnuté
                Serial.println("---> Elektroventil TUV zapnutý");
                digitalWrite(RELAY_VALVE_RADIATOR, HIGH); // LOW - zapnuté ; HIGH - vypnuté
                Serial.println("---> Elektroventil RADIÁTOROV vypnutý");
                }
          } else if ((teplotaVody > (nastavena_teplota_vody - toleranciaTUV)) && (teplotaVody < nastavena_teplota_vody)) {

              if (teplotaDymovodu < nastavena_teplota_dymovodu){ // ak je dymovod zimny, prepni na radiatory a potom podla teploty kotla vypne cerpadlo
                lastMode = 0; // 0 = Radiatory ; 1 = TUV
                Serial.println("---> NEDOSTATOCNA TEPLOTA SPALIN NA TO, ABY SA HRIALA TUV");
                // Resetujte stav ventilu a čas pri prechode do druhého bloku
                eletroventil_tuv_vypnuty = false;
                cas_zapnutia_eletroventilu = 0;
                digitalWrite(RELAY_VALVE, HIGH); // LOW - zapnuté ; HIGH - vypnuté
                digitalWrite(RELAY_VALVE_RADIATOR, LOW); // LOW - zapnuté ; HIGH - vypnuté
                Serial.println("---> Elektroventil TUV vypnutý - TEPLOTA DYMOVODU");
                Serial.println("---> Elektroventil RADIÁTOROV zapnutý - TEPLOTA DYMOVODU");
                }

              else {  

                if (lastMode == 0) { // 0 = Radiatory ; 1 = TUV
                  digitalWrite(RELAY_VALVE, HIGH); // LOW - zapnuté ; HIGH - vypnuté
                  digitalWrite(RELAY_VALVE_RADIATOR, LOW); // LOW - zapnuté ; HIGH - vypnuté
                  Serial.println("---> Elektroventil TUV vypnutý - LASTMODE");
                  Serial.println("---> Elektroventil RADIÁTOROV zapnutý - LASTMODE");
                  }
          
                else { // 0 = Radiatory ; 1 = TUV
                  digitalWrite(RELAY_VALVE, LOW); // LOW - zapnuté ; HIGH - vypnuté
                  digitalWrite(RELAY_VALVE_RADIATOR, HIGH); // LOW - zapnuté ; HIGH - vypnuté
                  Serial.println("---> Elektroventil TUV zapnutý - LASTMODE");
                  Serial.println("---> Elektroventil RADIÁTOROV vypnutý - LASTMODE");
                  }
            }
          }
        }
      } else if (teplotaKotla <= cerpadlo_slider_min){
        Serial.println("---> Čerpadlo vypnuté");
        Blynk.logEvent("obehove_cerpadlo_off", "Obehové čerpadlo je vypnuté");
        digitalWrite(RELAY_PUMP, HIGH); // LOW - zapnuté ; HIGH - vypnuté
        digitalWrite(RELAY_VALVE_RADIATOR, HIGH); // LOW - zapnuté ; HIGH - vypnuté
        digitalWrite(RELAY_VALVE, HIGH); // LOW - zapnuté ; HIGH - vypnuté
    }

  updateBlynkPins();
    
}

 else {

    Serial.println("\n*** MANUÁLNY REŽIM ***");

    if (tlacidlo_cerpadlo == 1) {
      Serial.println("---> Čerpadlo zapnuté");
      Blynk.logEvent("obehove_cerpadlo_on", "Obehové čerpadlo je zapnuté");
      digitalWrite(RELAY_PUMP, LOW);
      Blynk.virtualWrite(V2, 1);
    } else {
      Serial.println("---> Čerpadlo vypnuté");
      Blynk.logEvent("obehove_cerpadlo_off", "Obehové čerpadlo je vypnuté");
      digitalWrite(RELAY_PUMP, HIGH);
      Blynk.virtualWrite(V2, 0);
    }

    if (tlacidlo_ventil == 1) {
      Serial.println("---> Eletroventil zapnutý");
      Blynk.logEvent("ohrev_tuv_on", "Ohrev TUV je zapnutý");
      digitalWrite(RELAY_VALVE, LOW);
      Blynk.virtualWrite(V3, 1);
    } else {
      Serial.println("---> Eletroventil vypnutý");
      Blynk.logEvent("ohrev_tuv_off", "Ohrev TUV je vypnutý");
      digitalWrite(RELAY_VALVE, HIGH);
      Blynk.virtualWrite(V3, 0);
    }


    if (tlacidlo_ventil_radiator == 1) {
      Serial.println("---> Eletroventil radiatora zapnutý");
      Blynk.logEvent("ohrev_tuv_on", "Ohrev radiatorov je zapnutý");
      digitalWrite(RELAY_VALVE_RADIATOR, LOW);
      Blynk.virtualWrite(V12, 1);
    } else {
      Serial.println("---> Eletroventil radiatorov vypnutý");
      Blynk.logEvent("ohrev_tuv_off", "Ohrev radiatorov je vypnutý");
      digitalWrite(RELAY_VALVE_RADIATOR, HIGH);
      Blynk.virtualWrite(V12, 0);
    }

  }
  Serial.print("\nTeplota úžitkovej vody: ");
  Serial.print(teplotaVody);
  Serial.print(" °C\t");
  Serial.print("Teplota v kotli: ");
  Serial.print(teplotaKotla);
  Serial.println(" °C\t");
  Serial.print("Teplota dymovodu: ");
  Serial.print(teplotaDymovodu);
  Serial.println(" °C\t");

}

void sendSensorDefault() {

  sensors.requestTemperatures();
  teplotaVody = sensors.getTempCByIndex(0);
  teplotaKotla = sensors.getTempCByIndex(2);
  teplotaDymovodu = sensors.getTempCByIndex(1);
  //sensor1.requestTemperatures();
  //sensor2.requestTemperatures();
  //sensor3.requestTemperatures();

  // Prečítaj hodnoty z každého senzora
  //float teplotaVody = sensor1.getTempCByIndex(0);
  //float teplotaKotla = sensor2.getTempCByIndex(0);
  //float teplotaDymovodu = sensor3.getTempCByIndex(0);

  if (isnan(teplotaKotla)) {
    Serial.println("Chyba pri čítaní z prvého DS18B20 snímača!");
    return;
  }
  if (isnan(teplotaVody)) {
    Serial.println("Chyba pri čítaní z druhého DS18B20 snímača!");
    return;
  }

  if (isnan(teplotaDymovodu)) {
    Serial.println("Chyba pri čítaní z tretieho DS18B20 snímača!");
    return;
  }
  
  if (teplotaKotla < 0 || teplotaKotla > 150) {
    Serial.println("Chybná hodnota pre teplotu kotla!");
    return;
  }

  if (teplotaVody < 0 || teplotaVody > 100) {
    Serial.println("Chybná hodnota pre teplotu vody!");
    return;
  }

  if (teplotaDymovodu < 0 || teplotaDymovodu > 180) {
    Serial.println("Chybná hodnota pre teplotu dymovodu!");
    return;
  }

  if (teplotaVody == teplotaKotla) {
    Serial.println("Chybná hodnota pre teploty!");
    return;
  }

  if (teplotaDymovodu == teplotaKotla) {
    Serial.println("Chybná hodnota pre teploty!");
    return;
  }

  if (teplotaVody == teplotaDymovodu) {
    Serial.println("Chybná hodnota pre teploty!");
    return;
  }

  Serial.println("\n*** AUTOMATICKÝ POHOTOVOSTNÝ REŽIM ***");


  if (teplotaKotla >= 30) {
    Serial.println("---> Čerpadlo zapnuté");
    digitalWrite(RELAY_PUMP, LOW); // LOW - zapnute ; HIGH - vypnute

    if (teplotaKotla >= 85) { //bezpečnostne opatrenie
      digitalWrite(RELAY_VALVE, LOW);
      digitalWrite(RELAY_VALVE_RADIATOR, LOW);
      Serial.println("---> Eletroventily zapnuté");

    } else {
      //podmienky splnene a platne
      if ((teplotaVody >= 60) || (teplotaVody >= (teplotaKotla - 5))) {
        digitalWrite(RELAY_VALVE, HIGH); // LOW - zapnute ; HIGH - vypnute
        Serial.println("---> Eletroventil TUV vypnutý");
        digitalWrite(RELAY_VALVE_RADIATOR, LOW); // LOW - zapnute ; HIGH - vypnute
        Serial.println("---> Eletroventil radiatorov zapnutý");
      } else if ((teplotaKotla - 8) >= teplotaVody) {
        digitalWrite(RELAY_VALVE, LOW); // LOW - zapnute ; HIGH - vypnute
        Serial.println("---> Eletroventil TUV zapnutý");
        digitalWrite(RELAY_VALVE_RADIATOR, HIGH); // LOW - zapnute ; HIGH - vypnute
        Serial.println("---> Eletroventil radiatorov vypnutý");
      }
    }


  } else if (teplotaKotla <= 30) {
    Serial.println("---> Čerpadlo a elektroventily vypnuté");
    digitalWrite(RELAY_PUMP, HIGH); // LOW - zapnute ; HIGH - vypnute
    digitalWrite(RELAY_VALVE_RADIATOR, HIGH); // LOW - zapnute ; HIGH - vypnute
    digitalWrite(RELAY_VALVE, HIGH); // LOW - zapnute ; HIGH - vypnute
  }

}


void zistiVonkajsiuTeplotu()
{
  HTTPClient http;

  // URL pre získanie hodnoty z pinu V1
  String url = "http://blynk.cloud/external/api/get?token=NhAZeqig1jKjzGuVcYmdnAH_zzIWd3pL&V56";

  // Nastavenie URL pre HTTP GET požiadavku
  http.begin(url);

  // Vykonanie HTTP GET požiadavky
  int httpCode = http.GET();
  if (httpCode == HTTP_CODE_OK) {
    String vonkajsiaTeplotaString = http.getString();
    float vonkajsiaTeplota = vonkajsiaTeplotaString.toFloat();
    Serial.print("Vonkajšia teplota: ");
    Serial.println(vonkajsiaTeplota);
    Blynk.virtualWrite(V56, vonkajsiaTeplota);
  } else {

    Serial.println("Chyba pri HTTP požiadavke");
  }

  // Ukončenie HTTP spojenia
  http.end();
  delay(1000);

  // Zistenie polohy dvierok
  // URL pre získanie hodnoty z pinu V58
  String url2 = "http://blynk.cloud/external/api/get?token=Mrf5LJuXlXRyqIz46IKkbgeZAfXC0q8x&V15";

  // Nastavenie URL pre HTTP GET požiadavku
  http.begin(url2);

  // Vykonanie HTTP GET požiadavky
  int httpCode2 = http.GET();
  if (httpCode2 == HTTP_CODE_OK) {
    String polohaDvierokString = http.getString();
    float polohaDvierok = polohaDvierokString.toFloat();
    Serial.print("Poloha dvierok: ");
    Serial.println(polohaDvierok);
    Blynk.virtualWrite(V15, polohaDvierok);
  } else {

    Serial.println("Chyba pri HTTP požiadavke pre polohu dvierok");
  }

  // Ukončenie HTTP spojenia
  http.end();
}

void setup()
{
  Serial.begin(9600); //inicalizácia sériovej komunikácie
  Blynk.begin(auth, ssid, pass); //inicializácia pripojenia na Blynk

  for (int i = 0; i <= 17; i++) {
    Blynk.syncVirtual(i);
    Blynk.syncVirtual(24); // aktualizovat nastaveny slider dymovodu
  }

  digitalWrite(RELAY_PUMP, HIGH);
  digitalWrite(RELAY_VALVE, HIGH);
  digitalWrite(RELAY_VALVE_RADIATOR, HIGH);

  Blynk.virtualWrite(V4, 1);
  Blynk.setProperty(V4, "color", "#71d459");


  // Inicializácia OneWire pre každý senzor
  sensors.begin();
  //sensor1.begin();
  //sensor2.begin();
  //sensor3.begin();

  Serial.println("Senzory pripravené");

  
  pinMode(RELAY_PUMP, OUTPUT);
  pinMode(RELAY_VALVE, OUTPUT);
  pinMode(RELAY_VALVE_RADIATOR, OUTPUT);

  if (manualMode == 1) {
    Blynk.virtualWrite(V5, 1);
  } else {
    Blynk.virtualWrite(V5, 0);
  }

  timer.setInterval(3000L, sendSensor);
  timer.setInterval(3000L, coloring);
  timer.setInterval(3000L, zistiVonkajsiuTeplotu);
}

void loop()
{

  if (WiFi.status() != WL_CONNECTED) //kontrola, či je zariadenie pripojené
  {
    sendSensorDefault();
    ESP.restart();    //reštartovanie zariadenia v prípade, že nie je pripojené
  }
  else
  {
    Blynk.run(); //vykonávanie funkcií na Blynk serveri
    timer.run(); //vykonávanie funkcií s nastavenými intervalmi
    delay(3000);
    // Vytvorenie objektu HTTPClient

  }
}
