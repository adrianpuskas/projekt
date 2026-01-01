#define BLYNK_TEMPLATE_ID           "TMPLblK60Pj-"  // definícia Blynk šablóny ID
#define BLYNK_DEVICE_NAME           "Zavlaha"  // definícia názvu zariadenia v Blynk aplikácii
#define BLYNK_AUTH_TOKEN            "NhAZeqig1jKjzGuVcYmdnAH_zzIWd3pL"  // autentifikačný token pre Blynk
#define BLYNK_PRINT Serial  // používanie sériového výstupu pre Blynk

#include <WiFi.h>  // WiFi knižnica pre ESP32
#include <WiFiClient.h>  
#include <BlynkSimpleEsp32.h>  // Blynk knižnica pre ESP32
#include <DHT.h>  // knižnica pre senzor DHT

char auth[] = BLYNK_AUTH_TOKEN;  // inicializácia premennej pre autentifikáciu
char ssid[] = "iHome";  // meno Wi-Fi siete
char pass[] = "202PuskaS";  // heslo Wi-Fi siete

#define DHTPIN 2 // Definuje pin pre pripojenie DHT senzora
#define DHTTYPE DHT21 // Definuje typ DHT senzora, ktorý sa používa v kóde
DHT dht(DHTPIN, DHTTYPE); // Inicializuje DHT senzor pomocou definovaných parametrov

BlynkTimer timer; // Inicializuje timer pre Blynk knižnicu

double senzorTeploty; // Definuje premennú pre teplotu z DHT senzora
int senzorVlhkostiVzuchu; // Definuje premennú pre vlhkosť vzduchu z DHT senzora

// *** DHT senzor *** //
void DHTsenzor() // Funkcia pre čítanie dát z DHT senzora
{
  senzorVlhkostiVzuchu = dht.readHumidity(); // Načítanie vlhkosti vzduchu zo senzora
  senzorTeploty= dht.readTemperature(); // Načítanie teploty zo senzora
  
  if (isnan(senzorVlhkostiVzuchu) || isnan(senzorTeploty)) { // Ak sa nepodarilo načítať údaje zo senzora
    Serial.println(F("Nepodarilo sa čítanie z DTH senzora!")); 
  return;
  }
  
  Serial.print(F("Vlhkost vzduchu: ")); // Vypís stavu
  Serial.print(senzorVlhkostiVzuchu); 
  Serial.print(F("% Teplota vzduchu: ")); 
  Serial.print(senzorTeploty); 
  Serial.println(F("°C "));

  Blynk.virtualWrite(V56, senzorTeploty); // zapisovanie teploty vzduchu do virtuálneho pinu V56
  Blynk.virtualWrite(V58, senzorVlhkostiVzuchu); // zapisovanie vlhkosti vzduchu do virtuálneho pinu V58
}

//_____________________________________________________________________

void setup()
{
  Serial.begin(115200); //inicializácia sériovej komunikácie
  
  Blynk.begin(auth, ssid, pass); //inicializácia pripojenia na Blynk

  dht.begin(); //inicilaizácia DHT senzora

  timer.setInterval(5000L, DHTsenzor); //cyklické volanie funkcie DHTsenzor každých 5 sekúnd
  
  Serial.println();  

}

void loop()
{      
  if(WiFi.status() != WL_CONNECTED) //kontrola, či je zariadenie pripojené
  {
    ESP.restart();    //reštartovanie zariadenia v prípade, že nie je pripojené
  }
  else
  {
    Blynk.run(); //vykonávanie funkcií na Blynk serveri
    timer.run(); //vykonávanie funkcií s nastavenými intervalmi
  }  
 
}
