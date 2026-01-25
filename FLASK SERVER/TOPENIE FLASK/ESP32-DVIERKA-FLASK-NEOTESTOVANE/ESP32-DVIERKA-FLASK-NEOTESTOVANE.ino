#include <WiFi.h>  // WiFi knižnica pre ESP32
#include <WiFiClient.h>
#include <AccelStepper.h>
#include <HTTPClient.h>

char ssid[] = "ESP";  // meno Wi-Fi siete
char pass[] = "202PuskaS";  // heslo Wi-Fi siete

// === LOKÁLNY SERVER ===
const char* serverIP = "192.168.3.84";
const int serverPort = 8000;

// Piny pre krokový motor a spínače
#define spinac_dole 32 //dolný koncový spínač
#define spinac_hore 33 //horný koncový spínač
#define tlacidlo_zavriet 35 // manualne zavretie dvierok tlacidlom na kotle

//napinovanie krokoveho motora
#define dir_pin 12
#define step_pin 14
#define sleep_pin 22
#define reset_pin 23

// Globálne premenné pre logiku
float teplota_kotla = 0.0;  // Teplota kotla čítaná z Flask
float nastavenie_pracovna_teplota_kotla = 0.0;  // Pracovná teplota kotla (vybraná podľa priority)

float topenie_kotol_rezim = 0;  // Auto/manual (0=auto, 1=manual)
float wifiStatus_kotol = 0;  // WiFi status
float ovladanie_priorita_topenie = 0;  // Priorita topenia (z ESP1)
float nastavenie_teplota_kotla_pracovna_radiatory = 0;  // Pracovná teplota pre radiátory
float nastavenie_teplota_kotla_pracovna_tuv = 0;  // Pracovná teplota pre TUV
float ovladanie_inicializacia = 0;  // Inicializácia (1=spustiť)
float ovladanie_manualne_zatvorenie_dvierok = 0;  // Manuálne zatvorenie (1=zatvoriť)
float poloha_dvierok_aktualna = 0;  // Aktuálna poloha dvierok (%)
float poloha_dvierok_pozadovana = 0;  // Požadovaná poloha dvierok (%)

// Premenné pre motor
AccelStepper stepper(1, step_pin, dir_pin);  // Inicializácia stepper
int maxKroky = 0;  // Maximálny počet krokov (z inicializácie)
int kroky = 0;  // Aktuálny počet krokov
bool zmena = false;  // Indikátor zmeny polohy
int tlacidlo_zavriet_status = 0;  // Stav fyzického tlačidla
const float tolerancia_extra_percent = 0.05;  // 5% tolerancia extra krokov pre zatváranie na 0% (bezpečnosť)

// Premenné pre timery a stav
bool serverAvailable = false;
unsigned long lastSensorTime = 0;
const unsigned long sensorInterval = 2000;  // Interval pre hlavnú logiku (ako pôvodne)
unsigned long lastWatchTime = 0;
const unsigned long watchInterval = 1000;  // Interval pre watch
unsigned long lastCheckTime = 0;
const unsigned long checkIntervalWhenDown = 5000;  // Interval pre kontrolu obnovy servera
unsigned long lastWifiReconnectTime = 0;  // Timer pre reconnect WiFi
const unsigned long wifiReconnectInterval = 10000;  // Skús reconnect každých 10 sekúnd

// Zapisovanie do local servera
int sendToLocalServer(const String& key, float value) {
  if (WiFi.status() != WL_CONNECTED) return -1;

  WiFiClient client;
  HTTPClient http;

  String url = String("http://") + serverIP + ":" + String(serverPort) + "/write";

  http.begin(client, url);
  http.setTimeout(10000);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Connection", "close");
  http.addHeader("User-Agent", "ESP32-Sensor");

  String payload = "{\"key\":\"" + key + "\",\"value\":" + String(value, 1) + "}";

  int httpCode = http.POST(payload);
  Serial.printf("%s odoslané, HTTP kód: %d\n", key.c_str(), httpCode);

  http.end();
  return httpCode;
}

// Čítanie z local servera
WiFiClient client;
HTTPClient http;

float readFromLocalServer(const String& readKey) {
  String url = "http://" + String(serverIP) + ":" + String(serverPort) + "/get/" + readKey;
  http.begin(client, url);
  int httpCode = http.GET();
  float result = -999.0;

  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    Serial.println("Flask read success: " + payload);
    result = payload.toFloat();
  } else {
    Serial.println("Flask read error: HTTP code " + String(httpCode));
  }
  http.end();
  return result;
}

// Funkcia na overenie dostupnosti servera
bool isServerAvailable() {
  WiFiClient client;
  HTTPClient http;
  String url = "http://" + String(serverIP) + ":" + String(serverPort) + "/get/wifiStatus_kotol";  // Používame existujúci endpoint na test
  http.begin(client, url);
  int httpCode = http.GET();
  http.end();
  return (httpCode > 0);  // Ak > 0, server odpovedal
}

// Funkcia na čítanie hodnôt z Flask servera
void watchFlaskValue(const String& key, float& localVar, void (*callback)(float)) {
  float newValue = readFromLocalServer(key);

  if (newValue < -900) return; // chyba čítania

  if (newValue != localVar) {
    localVar = newValue;
    callback(newValue);
  }
}

// Callbacky pre Flask hodnoty
void cb_topenie_kotol_rezim(float value) {
  topenie_kotol_rezim = (int)value;
  Serial.printf("Režim zmenený na: %d\n", (int)topenie_kotol_rezim);
  sendToLocalServer("topenie_kotol_rezim", value);  // Potvrdenie
}

void cb_wifiStatus_kotol(float value) {
  wifiStatus_kotol = (int)value;
  Serial.printf("WiFi status kotol: %d\n", (int)wifiStatus_kotol);
}

void cb_ovladanie_inicializacia(float value) {
  if ((int)value == 1) {
    inicializaciaPolohy();
    sendToLocalServer("ovladanie_inicializacia", 0);  // Reset po inicializácii
  }
}

void cb_ovladanie_manualne_zatvorenie_dvierok(float value) {
  ovladanie_manualne_zatvorenie_dvierok = (int)value;
  if ((int)value == 1) {
    Serial.println("Manuálne zatvorenie dvierok");
    poloha_dvierok_pozadovana = 0;
    zmena = true;
  }
}

void cb_poloha_dvierok_pozadovana(float value) {
  poloha_dvierok_pozadovana = (int)value;
  if (topenie_kotol_rezim == 1) {  // Len v manuálnom režime
    zmena = true;
  }
}

void cb_nastavenie_teplota_kotla_pracovna_radiatory(float value) {
  nastavenie_teplota_kotla_pracovna_radiatory = value;
}

void cb_nastavenie_teplota_kotla_pracovna_tuv(float value) {
  nastavenie_teplota_kotla_pracovna_tuv = value;
}

void cb_ovladanie_priorita_topenie(float value) {
  ovladanie_priorita_topenie = (int)value;
  // Vybrať pracovnú teplotu podľa priority
  if (ovladanie_priorita_topenie == 0) {  // Radiátory
    nastavenie_pracovna_teplota_kotla = nastavenie_teplota_kotla_pracovna_radiatory;
  } else {  // TUV
    nastavenie_pracovna_teplota_kotla = nastavenie_teplota_kotla_pracovna_tuv;
  }
  sendToLocalServer("nastavenie_pracovna_teplota_kotla", nastavenie_pracovna_teplota_kotla);  // Aktualizovať vo Flask
}

// Funkcia na inicializáciu polohy motora
void inicializaciaPolohy() {
  Serial.println("=== INICIALIZÁCIA POLOHY - ŠTART ===");

  digitalWrite(sleep_pin, HIGH);
  digitalWrite(reset_pin, HIGH);

  // === 1. VŽDY NAJPRV VYNULUJ GLOBÁLNE PREMENNÉ ===
  maxKroky = 0;
  kroky = 0;
  poloha_dvierok_aktualna = 0;
  poloha_dvierok_pozadovana = 0;
  zmena = false;

  // === 2. Najprv úplne zatvor dvierka (do dolného spínača) ===
  Serial.println("Zatváram dvierka na dolný spínač...");
  digitalWrite(dir_pin, HIGH);   // smer dole
  while (digitalRead(spinac_dole) == LOW) {
    for (int i = 0; i < 10; i++) {
      digitalWrite(step_pin, HIGH);
      delayMicroseconds(2000);
      digitalWrite(step_pin, LOW);
      delayMicroseconds(2000);
    }
  }
  Serial.println("Dolný spínač dosiahnutý.");

  // === 3. Počítame kroky od 0% do 100% (hore) ===
  Serial.println("Otváram dvierka a počítam kroky...");
  digitalWrite(dir_pin, LOW);    // smer hore
  maxKroky = 0;

  while (digitalRead(spinac_hore) == LOW) {
    for (int i = 0; i < 10; i++) {
      digitalWrite(step_pin, HIGH);
      delayMicroseconds(2000);
      digitalWrite(step_pin, LOW);
      delayMicroseconds(2000);
    }
    maxKroky++;
  }

  kroky = maxKroky;                              // teraz sme na 100%
  poloha_dvierok_aktualna = 100;                 // nastavíme na 100%
  poloha_dvierok_pozadovana = 100;

  sendToLocalServer("poloha_dvierok_aktualna", 100);
  sendToLocalServer("poloha_dvierok_pozadovana", 100);

  Serial.printf("Inicializácia dokončená - maxKroky = %d, 100%% = %d krokov\n", maxKroky, maxKroky);

  digitalWrite(sleep_pin, LOW);
  digitalWrite(reset_pin, LOW);

  Serial.println("=== INICIALIZÁCIA POLOHY - KONIEC ===\n");
}

// Funkcia na kontrolu fyzického tlačidla zatvorenia dvierok
void fyzickeTlacidloZavrietDvierka() {
  static int prev_status = 0;
  int current_status = digitalRead(tlacidlo_zavriet) == LOW ? 1 : 0;

  if (current_status != prev_status) {
    Serial.println("Fyzické tlačidlo stlačené - manuálne zatvorenie dvierok");
    sendToLocalServer("ovladanie_manualne_zatvorenie_dvierok", current_status);
    prev_status = current_status;
    if (current_status == 1) {
      poloha_dvierok_pozadovana = 0;
      zmena = true;
    }
  }
}

// Zlúčená funkcia pre automatický režim (vypočíta požadovanú polohu)
void handleAutomaticMode(bool useDefault) {
  if (useDefault) {
    // V pohotovostnom režime (bez spojenia) zatvoriť dvierka na 0% pre bezpečnosť, bez čítania teploty
    poloha_dvierok_pozadovana = 0;
    zmena = true;
    Serial.println("\n*** AUTOMATICKÝ POHOTOVOSTNÝ REŽIM - DVIERKA ZATVORENÉ NA 0% ***");
    return;  // Koniec - nevyhodnocovať ďalej
  }

  // Normálny režim: Čítať teplotu a vypočítať
  float local_teplota_kotla = readFromLocalServer("teplota_kotla");  // Čítať teplotu kotla z Flask

  if (local_teplota_kotla < -900) {  // Chyba čítania
    Serial.println("Chyba čítania teploty kotla - zatváram dvierka na 0% pre bezpečnosť");
    poloha_dvierok_pozadovana = 0;
    zmena = true;
    return;
  }

  Serial.println("\n*** AUTOMATICKÝ REŽIM ***");
  Serial.print("Teplota kotla: ");
  Serial.println(local_teplota_kotla);
  Serial.print("Nastavená pracovná teplota: ");
  Serial.println(nastavenie_pracovna_teplota_kotla);

  if (local_teplota_kotla >= 80) {
    poloha_dvierok_pozadovana = 0;
    Serial.println("!!! Dosiahnuta maximálna teplota kotla 80°C !!! zatváram dvierka");
  } else if (local_teplota_kotla >= nastavenie_pracovna_teplota_kotla + 10 && local_teplota_kotla < 79.9) {
    poloha_dvierok_pozadovana = 0;
    Serial.println("!!! Kotol teplejsi o 10°C !!!");
  } else if (local_teplota_kotla >= nastavenie_pracovna_teplota_kotla + 5 && local_teplota_kotla < nastavenie_pracovna_teplota_kotla + 9.9) {
    poloha_dvierok_pozadovana = 1;
    Serial.println("!!! Kotol teplejsi o 5°C !!!");
  } else if (local_teplota_kotla >= nastavenie_pracovna_teplota_kotla - 5 && local_teplota_kotla < nastavenie_pracovna_teplota_kotla + 4.9) {
    poloha_dvierok_pozadovana = 3;
    Serial.println("!!! Dosiahnuta nastavena prevadzkova teplota !!!");
  } else if (local_teplota_kotla <= nastavenie_pracovna_teplota_kotla - 35) {
    poloha_dvierok_pozadovana = 60;
    Serial.println("!!! viac ako 35°C do dosiahnutia nastavenej prevadzkovej teploty !!!");
  } else if (local_teplota_kotla <= nastavenie_pracovna_teplota_kotla - 30 && local_teplota_kotla > nastavenie_pracovna_teplota_kotla - 34.9) {
    poloha_dvierok_pozadovana = 50;
    Serial.println("!!! 30°C do dosiahnutia nastavenej prevadzkovej teploty !!!");
  } else if (local_teplota_kotla <= nastavenie_pracovna_teplota_kotla - 20 && local_teplota_kotla > nastavenie_pracovna_teplota_kotla - 29.9) {
    poloha_dvierok_pozadovana = 40;
    Serial.println("!!! 20°C do dosiahnutia nastavenej prevadzkovej teploty !!!");
  } else if (local_teplota_kotla <= nastavenie_pracovna_teplota_kotla - 15 && local_teplota_kotla > nastavenie_pracovna_teplota_kotla - 19.9) {
    poloha_dvierok_pozadovana = 30;
    Serial.println("!!! 15°C do dosiahnutia nastavenej prevadzkovej teploty !!!");
  } else if (local_teplota_kotla <= nastavenie_pracovna_teplota_kotla - 10 && local_teplota_kotla > nastavenie_pracovna_teplota_kotla - 14.9) {
    poloha_dvierok_pozadovana = 10;
    Serial.println("!!! 10°C do dosiahnutia nastavenej prevadzkovej teploty !!!");
  } else if (local_teplota_kotla <= nastavenie_pracovna_teplota_kotla - 5 && local_teplota_kotla > nastavenie_pracovna_teplota_kotla - 9.9) {
    poloha_dvierok_pozadovana = 5;
    Serial.println("!!! 5°C do dosiahnutia nastavenej prevadzkovej teploty !!!");
  }

  sendToLocalServer("poloha_dvierok_pozadovana", poloha_dvierok_pozadovana);
  zmena = true;  // Označiť zmenu pre pohyb motora
}

// Funkcia na pohyb motora podľa požadovanej polohy
void pohybujMotorom() {
  if (zmena) {
    digitalWrite(sleep_pin, HIGH);
    digitalWrite(reset_pin, HIGH);

    int ciel_kroky = map(poloha_dvierok_pozadovana, 0, 100, 0, maxKroky);

    if (ciel_kroky < kroky) {
      Serial.println("Zatváram dvierka ...");
      digitalWrite(dir_pin, HIGH);
      int extra_kroky = 0;  // Počítadlo extra krokov pre 0%
      int max_extra_kroky = (int)(tolerancia_extra_percent * maxKroky);  // Limit 5%

      while (kroky > ciel_kroky || (poloha_dvierok_pozadovana == 0 && digitalRead(spinac_dole) == LOW)) {
        for (int i = 0; i < 10; i++) {
          digitalWrite(step_pin, HIGH);
          delayMicroseconds(2000);
          digitalWrite(step_pin, LOW);
          delayMicroseconds(2000);
        }
        kroky -= 1;

        // Ak sme pod cieľ (pre 0%), počítaj extra
        if (kroky < ciel_kroky) {
          extra_kroky++;
          if (extra_kroky > max_extra_kroky) {
            Serial.println("Možná chyba spínača dole – extra kroky presiahnuté! Zastavujem motor.");
            // Voliteľne: ESP.restart();  // Ak chceš reštartovať
            break;  // Zastav slučku
          }
        }

        // Bezpečnostné opatrenie (pôvodné)
        if (kroky > 0 && digitalRead(spinac_dole) == HIGH) {
          Serial.println("Chyba - dolný spínač aktivovaný predčasne!");
          return;  // Zastav (možno restart ak treba)
        }
      }

      // Ak sa dosiahol spínač pri 0%, resetuj polohu
      if (poloha_dvierok_pozadovana == 0 && digitalRead(spinac_dole) == HIGH) {
        kroky = 0;
        Serial.println("Dolný spínač aktivovaný – resetujem polohu na 0%");
      }

    } else if (ciel_kroky > kroky) {
      Serial.println("Otváram dvierka ...");
      digitalWrite(dir_pin, LOW);
      while (kroky < ciel_kroky) {
        for (int i = 0; i < 10; i++) {
          digitalWrite(step_pin, HIGH);
          delayMicroseconds(2000);
          digitalWrite(step_pin, LOW);
          delayMicroseconds(2000);
        }
        kroky += 1;

        // Bezpečnostné opatrenie
        if (kroky < maxKroky && digitalRead(spinac_hore) == HIGH) {
          Serial.println("Chyba - horný spínač aktivovaný!");
          return;  // Zastav
        }
      }
    }

    poloha_dvierok_aktualna = map(kroky, 0, maxKroky, 0, 100);
    sendToLocalServer("poloha_dvierok_aktualna", poloha_dvierok_aktualna);

    digitalWrite(sleep_pin, LOW);
    digitalWrite(reset_pin, LOW);
    zmena = false;
  }
}

// Hlavná riadiaca funkcia
void sendSensor() {
  int wifiCode = sendToLocalServer("wifiStatus_kotol", 1);

  if (wifiCode < 0) {
    sendSensorDefault();
    return;
  }

  fyzickeTlacidloZavrietDvierka();  // Skontrolovať fyzické tlačidlo

  if (ovladanie_manualne_zatvorenie_dvierok == 1) {
    Serial.println("\n*** MANUÁLNE UZAVRETÉ DVIERKA Z DOVODU NAKLADANIA DREVA ***");
    poloha_dvierok_pozadovana = 0;
    zmena = true;
  } else if (topenie_kotol_rezim == 0) {
    handleAutomaticMode(false);  // Automatický režim
  } else {
    Serial.println("\n*** MANUÁLNY REŽIM ***");
    // V manuálnom režime používať poloha_dvierok_pozadovana z Flask
    zmena = true;
  }

  pohybujMotorom();  // Vykonať pohyb motora ak zmena
}

void sendSensorDefault() {
  fyzickeTlacidloZavrietDvierka();  // Skontrolovať fyzické tlačidlo aj v default

  handleAutomaticMode(true);  // V defaultnom režime zatvorí na 0%
}

void setup() {
  Serial.begin(115200);  // Ako v pôvodnom

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, pass);

  Serial.print("Pripájam sa na WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi pripojené!");
  Serial.print("IP adresa: ");
  Serial.println(WiFi.localIP());

  // Inicializácia pinov
  pinMode(step_pin, OUTPUT);
  pinMode(dir_pin, OUTPUT);
  pinMode(sleep_pin, OUTPUT);
  pinMode(reset_pin, OUTPUT);

  digitalWrite(sleep_pin, LOW);
  digitalWrite(reset_pin, LOW);

  pinMode(spinac_dole, INPUT_PULLUP);
  pinMode(spinac_hore, INPUT_PULLUP);
  pinMode(tlacidlo_zavriet, INPUT_PULLUP);

  // Inicializácia dostupnosti servera
  serverAvailable = isServerAvailable();
  if (serverAvailable) {
    sendToLocalServer("wifiStatus_kotol", 1);
  }

  // Počiatočná inicializácia polohy
  inicializaciaPolohy();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    // Pohotovostný režim bez reštartu
    Serial.println("WiFi odpojené - bežím v pohotovostnom režime");

    // Pokus o reconnect WiFi periodicky
    if (millis() - lastWifiReconnectTime >= wifiReconnectInterval) {
      lastWifiReconnectTime = millis();
      Serial.print("Pokus o reconnect WiFi...");
      WiFi.reconnect();
    }

    // Spusti sendSensorDefault() periodicky
    if (millis() - lastSensorTime >= sensorInterval) {
      lastSensorTime = millis();
      sendSensorDefault();
    }

    // Kontrola, či sa WiFi obnovilo (a server)
    if (millis() - lastCheckTime >= checkIntervalWhenDown) {
      lastCheckTime = millis();
      if (WiFi.status() == WL_CONNECTED && isServerAvailable()) {
        serverAvailable = true;
        Serial.println("WiFi a server obnovené - prechádzam do normálneho režimu");
        lastSensorTime = millis();  // Okamžite spusti sendSensor
        lastWatchTime = millis();  // Okamžite spusti watch
      }
    }

    delay(100);  // Malý delay na zabránenie busy loop
  } else {
    if (!serverAvailable) {
      // Pohotovostný režim (server dole, ale WiFi hore)
      if (millis() - lastCheckTime >= checkIntervalWhenDown) {
        lastCheckTime = millis();
        if (isServerAvailable()) {
          serverAvailable = true;
          lastSensorTime = millis();  // Okamžite spusti sendSensor
          lastWatchTime = millis();  // Okamžite spusti watch
        }
      }
      if (millis() - lastSensorTime >= sensorInterval) {
        lastSensorTime = millis();
        sendSensorDefault();
      }
      delay(100);  // Malý delay na zabránenie busy loop
    } else {
      // Normálny režim
      if (millis() - lastSensorTime >= sensorInterval) {
        lastSensorTime = millis();
        sendSensor();
      }
      if (millis() - lastWatchTime >= watchInterval) {
        lastWatchTime = millis();
        watchFlaskValue("topenie_kotol_rezim", topenie_kotol_rezim, cb_topenie_kotol_rezim);
        watchFlaskValue("wifiStatus_kotol", wifiStatus_kotol, cb_wifiStatus_kotol);
        watchFlaskValue("ovladanie_inicializacia", ovladanie_inicializacia, cb_ovladanie_inicializacia);
        watchFlaskValue("ovladanie_manualne_zatvorenie_dvierok", ovladanie_manualne_zatvorenie_dvierok, cb_ovladanie_manualne_zatvorenie_dvierok);
        watchFlaskValue("poloha_dvierok_pozadovana", poloha_dvierok_pozadovana, cb_poloha_dvierok_pozadovana);
        watchFlaskValue("nastavenie_teplota_kotla_pracovna_radiatory", nastavenie_teplota_kotla_pracovna_radiatory, cb_nastavenie_teplota_kotla_pracovna_radiatory);
        watchFlaskValue("nastavenie_teplota_kotla_pracovna_tuv", nastavenie_teplota_kotla_pracovna_tuv, cb_nastavenie_teplota_kotla_pracovna_tuv);
        watchFlaskValue("ovladanie_priorita_topenie", ovladanie_priorita_topenie, cb_ovladanie_priorita_topenie);
      }
    }
  }
}