#include <WiFi.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include <Arduino.h>
#include <IRremote.hpp>
#include <PZEM004Tv30.h>

#define IR_LED_PIN 4
PZEM004Tv30 pzem(Serial2, 16, 17);  // RX=16, TX=17

// WiFi + Flask
const char* ssid = "ESP";
const char* pass = "202PuskaS";
const char* serverIP = "192.168.3.84";
const int serverPort = 8000;

// Klúče pre Flask
const String KEY_AUTOMATIKA = "automatika_ohrev";
const String KEY_OHREV_VYPINAC = "ohrev_vypinac";
const String KEY_OHREV_PLAY_STOP = "ohrev_play_stop";
const String KEY_NASTAVENY_VYKON = "nastaveny_vykon_ohrevu";
const String KEY_BAT_VYKON = "V75";
const String KEY_ZATAZ_VYKON = "V65";
const String KEY_PANELY_VYKON = "V76";
const String KEY_PANELY_NAPATIE = "V73";
const String KEY_BAT_KAPACITA = "V70";
const String KEY_MENIC_TEPLOTA = "V71";
const String KEY_INVERTER_MODE = "V1";
const String KEY_TEPLOTA_TUV = "teplota_tuv";

// Nové klúče pre nastavenia automatizácie
const String KEY_MIN_VYKON = "ohrev_min_vykon";
const String KEY_MAX_VYKON = "ohrev_max_vykon";
const String KEY_VYKON_KROK = "ohrev_vykon_krok";
const String KEY_BAT_CAP_ON = "ohrev_bat_cap_on";
const String KEY_MIN_BATT_POWER_START = "ohrev_min_batt_power_start";
const String KEY_BAT_MAX_DISCHARGE = "ohrev_bat_max_discharge";
const String KEY_BAT_MAX_DISCHARGE2 = "ohrev_bat_max_discharge2";
const String KEY_BAT_SAFE_RANGE = "ohrev_bat_safe_range";
const String KEY_BAT_HARD_LIMIT = "ohrev_bat_hard_limit";
const String KEY_MAX_ZATAZ_VYKON = "ohrev_max_zataz";
const String KEY_LIMIT_VYP_ZATAZ = "ohrev_limit_vyp_zataz";
const String KEY_LIMIT_ZAP_ZATAZ = "ohrev_limit_zap_zataz";
const String KEY_PRIORITA_FVE = "ohrev_priorita_fve";
const String KEY_PANEL_OV = "panel_ov";
const String KEY_PANEL_MPV = "panel_mpv";
const String KEY_STRING_PCS = "string_pcs";
const String KEY_RELOAD = "ohrev_reload";
const String resetKey = "ohrev_pzem_reset";

// Globálne premenné
float string_MPV = 0.0;
int MIN_VYKON = 25;
int MAX_VYKON = 75;
int VYKON_KROK = 25;
int BAT_CAP_ON = 30;
int MIN_BATT_POWER_FOR_START = 100;
int BAT_MAX_DISCHARGE = -500;
int BAT_MAX_DISCHARGE2 = -1000;
int BAT_SAFE_RANGE = 150;
int BAT_HARD_LIMIT = -2500;
int MAX_ZATAZ_VYKON = 4000;
int LIMIT_VYP_ZATAZ = 3500;
int LIMIT_ZAP_ZATAZ = 3000;
int PRIORITA_FVE = 0;
int MIN_VYKON_START = 25;

bool stavOhrevu = false;
int currentPercent = 25;
unsigned long cas_vypnutia_ohrevu = 0;
const unsigned long COOLDOWN_TIME = 60000;
unsigned long dlhodobe_nizke_vykonanie_cas = 0;

int vykon_panely = 0, vykon_zataz = 0, vykon_bateria = 0, kapacita_bateria = 0;
int napatie_panely = 0, teplota_menica = 0;
String inverter_mode = "Unknown";

double celkovaSpotreba = 0.0;

// Časovače
unsigned long lastDataSync = 0;
unsigned long lastSettingsSync = 0;
unsigned long lastPzemRead = 0;
unsigned long lastResetCheckTime = 0;
unsigned long lastServerCheckTime = 0;
unsigned long lastWifiReconnectTime = 0;

const unsigned long DATA_SYNC_INTERVAL = 2000;
const unsigned long SETTINGS_SYNC_INTERVAL = 30000;
const unsigned long PZEM_INTERVAL = 5000;
const unsigned long resetCheckInterval = 2000;
const unsigned long serverCheckInterval = 10000;  // Check servera každých 10s
const unsigned long wifiReconnectInterval = 10000;

// Pohotovostný režim
bool serverAvailable = false;

// --- Flask komunikácia ---
float readFlaskValue(const String& key) {
  if (WiFi.status() != WL_CONNECTED) return -1.0;
  HTTPClient http;
  WiFiClient client;
  String url = "http://" + String(serverIP) + ":" + String(serverPort) + "/get/" + key;
  http.begin(client, url);
  int code = http.GET();
  if (code == HTTP_CODE_OK) {
    String payload = http.getString();
    http.end();
    return payload.toFloat();
  }
  http.end();
  return -1.0;
}

String readFlaskString(const String& key) {
  if (WiFi.status() != WL_CONNECTED) return "";
  HTTPClient http;
  WiFiClient client;
  String url = "http://" + String(serverIP) + ":" + String(serverPort) + "/get/" + key;
  http.begin(client, url);
  int code = http.GET();
  if (code == HTTP_CODE_OK) {
    String payload = http.getString();
    http.end();
    return payload;
  }
  http.end();
  return "";
}

void writeFlaskValue(const String& key, float value) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  WiFiClient client;
  String url = "http://" + String(serverIP) + ":" + String(serverPort) + "/write";
  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");
  String payload = "{\"key\":\"" + key + "\",\"value\":" + String(value) + "}";
  http.POST(payload);
  http.end();
}

void writeFlaskValue(const String& key, const String& text) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  WiFiClient client;
  String url = "http://" + String(serverIP) + ":" + String(serverPort) + "/write";
  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");
  String payload = "{\"key\":\"" + key + "\",\"value\":\"" + text + "\"}";
  http.POST(payload);
  http.end();
}

// --- Server dostupnosť ---
bool isServerAvailable() {
  HTTPClient http;
  WiFiClient client;
  String url = "http://" + String(serverIP) + ":" + String(serverPort) + "/get/" + KEY_AUTOMATIKA;  // Testovací endpoint
  http.begin(client, url);
  int code = http.GET();
  http.end();
  return (code > 0);  // Ak server odpovie (aj errorom), je dostupný
}

// --- Načítanie nastavení ---
void syncSettings() {
  float panel_OV = readFlaskValue(KEY_PANEL_OV);
  float panel_MPV = readFlaskValue(KEY_PANEL_MPV);
  int string_pcs = (int)readFlaskValue(KEY_STRING_PCS);
  string_MPV = panel_MPV * string_pcs;

  MIN_VYKON = (int)readFlaskValue(KEY_MIN_VYKON);
  MAX_VYKON = (int)readFlaskValue(KEY_MAX_VYKON);
  VYKON_KROK = (int)readFlaskValue(KEY_VYKON_KROK);
  BAT_CAP_ON = (int)readFlaskValue(KEY_BAT_CAP_ON);
  MIN_BATT_POWER_FOR_START = (int)readFlaskValue(KEY_MIN_BATT_POWER_START);
  BAT_MAX_DISCHARGE = (int)readFlaskValue(KEY_BAT_MAX_DISCHARGE);
  BAT_MAX_DISCHARGE2 = (int)readFlaskValue(KEY_BAT_MAX_DISCHARGE2);
  BAT_SAFE_RANGE = (int)readFlaskValue(KEY_BAT_SAFE_RANGE);
  BAT_HARD_LIMIT = (int)readFlaskValue(KEY_BAT_HARD_LIMIT);
  MAX_ZATAZ_VYKON = (int)readFlaskValue(KEY_MAX_ZATAZ_VYKON);
  LIMIT_VYP_ZATAZ = (int)readFlaskValue(KEY_LIMIT_VYP_ZATAZ);
  LIMIT_ZAP_ZATAZ = (int)readFlaskValue(KEY_LIMIT_ZAP_ZATAZ);
  PRIORITA_FVE = (int)readFlaskValue(KEY_PRIORITA_FVE);

  if (readFlaskValue(KEY_RELOAD) == 1) {
    writeFlaskValue(KEY_RELOAD, 0);
  }
}

// --- Načítanie aktuálnych dát ---
void syncData() {
  napatie_panely = (int)readFlaskValue(KEY_PANELY_NAPATIE);
  teplota_menica = (int)readFlaskValue(KEY_MENIC_TEPLOTA);
  vykon_panely = (int)readFlaskValue(KEY_PANELY_VYKON);
  vykon_zataz = (int)readFlaskValue(KEY_ZATAZ_VYKON);
  vykon_bateria = (int)readFlaskValue(KEY_BAT_VYKON);
  kapacita_bateria = (int)readFlaskValue(KEY_BAT_KAPACITA);
  inverter_mode = readFlaskString(KEY_INVERTER_MODE);

  float tuv = readFlaskValue(KEY_TEPLOTA_TUV);
  writeFlaskValue("V9", tuv);  // Ak máš V9
}

// --- IR funkcie ---
void sendIRCommand(uint16_t userCode, uint16_t dataCode) {
  Serial.printf("IR: 0x%X 0x%X\n", userCode, dataCode);
  IrSender.sendNEC(userCode, dataCode, 0);
}

void adjustPowerLevel(int targetPercent) {
  if (!stavOhrevu) return;
  Serial.printf("Power: %d%% -> %d%%\n", currentPercent, targetPercent);

  if (targetPercent == 100) { sendIRCommand(0xFE01, 0xF807); currentPercent = 100; return; }
  if (targetPercent == 75)  { sendIRCommand(0xFE01, 0xF50A); currentPercent = 75; return; }
  if (targetPercent == 50)  { sendIRCommand(0xFE01, 0xFB04); currentPercent = 50; return; }
  if (targetPercent == 25)  { sendIRCommand(0xFE01, 0xFD02); currentPercent = 25; return; }

  while (currentPercent != targetPercent) {
    if ((currentPercent > targetPercent && (currentPercent - 1) % 25 != 0) ||
        (currentPercent < targetPercent && (currentPercent + 1) % 25 != 0)) {
      sendIRCommand(0xFE01, currentPercent > targetPercent ? 0xE11E : 0xE31C);
      currentPercent += (currentPercent > targetPercent) ? -1 : 1;
    } else {
      if (currentPercent > targetPercent) {
        if (currentPercent > 75) { sendIRCommand(0xFE01, 0xF50A); currentPercent = 75; }
        else if (currentPercent > 50) { sendIRCommand(0xFE01, 0xFB04); currentPercent = 50; }
        else if (currentPercent > 25) { sendIRCommand(0xFE01, 0xFD02); currentPercent = 25; }
      } else {
        if (currentPercent < 25) { sendIRCommand(0xFE01, 0xFD02); currentPercent = 25; }
        else if (currentPercent < 50) { sendIRCommand(0xFE01, 0xFB04); currentPercent = 50; }
        else if (currentPercent < 75) { sendIRCommand(0xFE01, 0xF50A); currentPercent = 75; }
        else if (currentPercent < 100) { sendIRCommand(0xFE01, 0xF807); currentPercent = 100; }
      }
    }
    delay(500);
  }
  writeFlaskValue(KEY_NASTAVENY_VYKON, currentPercent);
}

void setOhrev(bool on) {
  if (on && !stavOhrevu) {
    Serial.println("Zapínam ohrev IR");
    delay(5000);
    sendIRCommand(0xFE01, 0xE41B);
    stavOhrevu = true;
    writeFlaskValue(KEY_OHREV_VYPINAC, 1);
  } else if (!on && stavOhrevu) {
    Serial.println("Vypínam ohrev IR");
    sendIRCommand(0xFE01, 0xE41B);
    stavOhrevu = false;
    writeFlaskValue(KEY_OHREV_VYPINAC, 0);
    cas_vypnutia_ohrevu = millis();
  }
}

// --- Bezpečný fallback pri výpadku ---
void fallbackSafeMode() {
  Serial.println("!!! FALLBACK SAFE MODE !!! WiFi alebo server down → vypínam ohrev + 25%");
  sendIRCommand(0xFE01, 0xE41B);  // Vypnúť ohrev
  delay(1000);                    // Malý delay pre istotu
  sendIRCommand(0xFE01, 0xFD02);  // Nastaviť na 25%
  currentPercent = 25;
  stavOhrevu = false;
  writeFlaskValue(KEY_OHREV_VYPINAC, 0);  // Aktualizuj dashboard (ak sa podarí)
  writeFlaskValue(KEY_NASTAVENY_VYKON, 25);
}

// --- Logika automatiky (portovaná) ---
bool mozeSaZapnutOhrev() {
  if (cas_vypnutia_ohrevu == 0) return true;
  if (millis() - cas_vypnutia_ohrevu >= COOLDOWN_TIME) return true;
  return false;
}

int calculateNewPower(int vykonBateria, int vykonOhrevu) {
  float zmena = abs(vykonBateria) / 2000.0 * 100.0;
  int newP;
  if (vykonBateria < BAT_MAX_DISCHARGE) {
    newP = max((int)(vykonOhrevu - zmena), MIN_VYKON);
  } else if (vykonBateria > BAT_SAFE_RANGE) {
    newP = min((int)(vykonOhrevu + zmena), MAX_VYKON);
  } else {
    newP = vykonOhrevu;
  }
  if (newP <= 37) newP = 25;
  else if (newP <= 62) newP = 50;
  else newP = 75;
  return newP;
}

void automatikaLoop() {
  if (napatie_panely > 50 && teplota_menica > 1 && inverter_mode == "Battery") {
    if (!stavOhrevu) {
      // Zapnutie
      bool zapnut = false;
      if (vykon_bateria < BAT_MAX_DISCHARGE) {
        // nemôže
      } else if (PRIORITA_FVE == 0 &&
                 (vykon_bateria > MIN_BATT_POWER_FOR_START || napatie_panely > string_MPV) &&
                 vykon_zataz < LIMIT_ZAP_ZATAZ &&
                 kapacita_bateria >= BAT_CAP_ON &&
                 mozeSaZapnutOhrev()) {
        zapnut = true;
        Serial.println("Zapínam ohrev - priorita Batéria");
      } else if (PRIORITA_FVE == 1 &&
                 (vykon_bateria > MIN_BATT_POWER_FOR_START || napatie_panely > string_MPV) &&
                 vykon_zataz < LIMIT_ZAP_ZATAZ &&
                 mozeSaZapnutOhrev()) {
        zapnut = true;
        Serial.println("Zapínam ohrev - priorita TUV");
      }
      if (zapnut) {
        setOhrev(true);
        adjustPowerLevel(MIN_VYKON_START);
      }
    } else {
      // Vypnutie / úprava
      bool vypnut = false;
      if (PRIORITA_FVE == 0 && kapacita_bateria < BAT_CAP_ON) vypnut = true;
      if (vykon_zataz > LIMIT_VYP_ZATAZ) vypnut = true;
      if (vykon_bateria < BAT_HARD_LIMIT) vypnut = true;

      if (vypnut) {
        setOhrev(false);
      } else {
        // Zvýšenie
        if (vykon_zataz + 150 < MAX_ZATAZ_VYKON &&
            ((BAT_MAX_DISCHARGE < vykon_bateria && vykon_bateria > BAT_SAFE_RANGE) ||
             (vykon_bateria > BAT_SAFE_RANGE || (kapacita_bateria >= BAT_CAP_ON && napatie_panely > string_MPV && vykon_bateria > 50))) &&
            currentPercent < MAX_VYKON) {
          int newP = min(currentPercent + VYKON_KROK, MAX_VYKON);
          adjustPowerLevel(newP);
        }
        // Zníženie
        else if (vykon_bateria < BAT_MAX_DISCHARGE2) {
          int newP = calculateNewPower(vykon_bateria, currentPercent);
          if (newP == 25 && vykon_bateria < BAT_MAX_DISCHARGE2) newP = 5;
          adjustPowerLevel(newP);
        }
        else if (currentPercent > MIN_VYKON && (vykon_zataz > MAX_ZATAZ_VYKON || vykon_bateria < BAT_MAX_DISCHARGE)) {
          int newP = max(currentPercent - VYKON_KROK, MIN_VYKON);
          adjustPowerLevel(newP);
        }

        // Dlhodobé vybíjanie
        if (vykon_bateria < BAT_MAX_DISCHARGE) {
          if (dlhodobe_nizke_vykonanie_cas == 0) dlhodobe_nizke_vykonanie_cas = millis();
          else if (millis() - dlhodobe_nizke_vykonanie_cas > 60000) {
            setOhrev(false);
            dlhodobe_nizke_vykonanie_cas = 0;
          }
        } else {
          dlhodobe_nizke_vykonanie_cas = 0;
        }
      }
    }
  } else {
    // Porucha
    setOhrev(false);
  }
}

// --- PZEM čítanie ---
int pzemErrorCount = 0;
int pzemOkCount = 0;

void readPzem() {
  float voltage = pzem.voltage();
  float current = pzem.current();
  float power = pzem.power();
  float energy = pzem.energy();

  if ((isnan(voltage) || isnan(current) || isnan(power)) || power < 50) {
    pzemErrorCount++;
    pzemOkCount = 0;
    Serial.printf("⚠️ PZEM error %d/3\n", pzemErrorCount);
    if (pzemErrorCount >= 3) {
      Serial.println("❌ PZEM nekomunikuje → OFF");
      setOhrev(false);
      writeFlaskValue(KEY_OHREV_VYPINAC, 0);
      pzemErrorCount = 0;
    }
    return;
  } else {
    pzemOkCount++;
    pzemErrorCount = 0;
    Serial.printf("✅ PZEM OK %d/3\n", pzemOkCount);
    if (pzemOkCount >= 3) {
      stavOhrevu = true;
      writeFlaskValue(KEY_OHREV_VYPINAC, 1);
      pzemOkCount = 0;
    }
  }

  celkovaSpotreba = energy;

  writeFlaskValue("ohrev_pzem_voltage", voltage);
  writeFlaskValue("ohrev_pzem_current", current);
  writeFlaskValue("ohrev_pzem_power", power);
  writeFlaskValue("ohrev_pzem_energy", energy);
}

// --- Reset energie ---
void resetPZEMEnergy() {
  pzem.resetEnergy();
  celkovaSpotreba = 0.0;
  writeFlaskValue("ohrev_pzem_energy", 0.0);
  writeFlaskValue(resetKey, 0.0);
  Serial.println("PZEM energia resetovaná na 0 kWh");
}

// --- Setup ---
void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, pass);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  Serial.println("WiFi pripojené");

  IrSender.begin(IR_LED_PIN);

  syncSettings();
  syncData();
  pzemErrorCount = 0;
  pzemOkCount = 0;

  serverAvailable = isServerAvailable();
}

// --- Loop ---
void loop() {
  unsigned long now = millis();

  // WiFi kontrola + reconnect
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi odpojené → pohotovostný režim + reconnect");
    fallbackSafeMode();  // Bezpečnostný fallback
    if (now - lastWifiReconnectTime >= wifiReconnectInterval) {
      lastWifiReconnectTime = now;
      WiFi.reconnect();
    }
    delay(100);
    return;
  }

  // Server kontrola
  if (now - lastServerCheckTime >= serverCheckInterval) {
    lastServerCheckTime = now;
    serverAvailable = isServerAvailable();
    if (!serverAvailable) {
      Serial.println("Server nedostupný → fallback safe mode");
      fallbackSafeMode();
    }
  }

  if (!serverAvailable) {
    // Pohotovostný režim (server down, ale WiFi OK)
    fallbackSafeMode();
    delay(100);
    return;
  }

  // Normálny režim
  if (now - lastDataSync >= DATA_SYNC_INTERVAL) {
    syncData();
    lastDataSync = now;
  }
  if (now - lastSettingsSync >= SETTINGS_SYNC_INTERVAL) {
    syncSettings();
    lastSettingsSync = now;
  }

  if (readFlaskValue(KEY_AUTOMATIKA) == 1) {
    automatikaLoop();
  } else {
    int vypinac = (int)readFlaskValue(KEY_OHREV_VYPINAC);
    int power = (int)readFlaskValue(KEY_NASTAVENY_VYKON);
    if (vypinac == 1 && !stavOhrevu) setOhrev(true);
    if (vypinac == 0 && stavOhrevu) setOhrev(false);
    if (stavOhrevu && power != currentPercent) adjustPowerLevel(power);
  }

  if (now - lastPzemRead >= PZEM_INTERVAL) {
    readPzem();
    lastPzemRead = now;
  }

  if (now - lastResetCheckTime >= resetCheckInterval) {
    lastResetCheckTime = now;
    float resetValue = readFlaskValue(resetKey);
    if ((int)resetValue == 1) {
      Serial.println("Reset požiadavka prijatá...");
      resetPZEMEnergy();
    } else if (resetValue == -1.0) {
      Serial.println("Chyba čítania resetu...");
    }
  }

  delay(100);
  yield();
}