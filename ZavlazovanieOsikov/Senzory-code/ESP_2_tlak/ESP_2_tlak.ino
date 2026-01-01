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


#define ANALOG_Tlak_PIN 32 // definícia pinu pre meranie analógového signálu senzora tlaku

BlynkTimer timer; // definícia objektu pre časovač BlynkTimer

// *** STATUS ESP32 *** //
void status_esp32(){ // funkcia pre aktualizáciu statusu ESP32, ktorá sa vykonáva s intervalom daným v setup() funkcii
Blynk.virtualWrite(V6, 1); // odoslanie hodnoty 1 do virtuálneho pinu V6 v Blynk aplikácii
}

double senzorTlaku; // deklarácia premennej pre nameranú hodnotu z tlakového senzora

// *** Tlakový senzor *** //
void tlakovySenzor() // funkcia pre meranie tlaku vody s intervalom daným v setup() funkcii
{
  senzorTlaku = analogRead(ANALOG_Tlak_PIN); // nameranie hodnoty z analógového pinu senzora tlaku
  Serial.print(F("Tlak vody analog: "));
  Serial.print(senzorTlaku);
  
  // mapovacia funkcia -> (nameraná_analog_hodnota - min_analog_hodnota) * (max_tlak - min_tlak) / (max_analog_hodnota - min_analog_hodnota) + min_tlak
  senzorTlaku = (senzorTlaku-520) * (3-0)/(1700-520) + 0; // výpočet skutočnej hodnoty tlaku z nameranej hodnoty analógového signálu
  
  // ošetrenie podtlaku
  if(senzorTlaku <=0){
  senzorTlaku = 0; // nastavenie hodnoty na 0, ak je tlak menší alebo rovný 0
  }
  
  Serial.print(F("Tlak vody: "));
  Serial.print(senzorTlaku);
  Serial.println(F(" bar"));
  
  Blynk.virtualWrite(V53, senzorTlaku); // odoslanie skutočnej hodnoty tlaku do virtuálneho pinu V53 v Blynk aplikácii
}

//_____________________________________________________________________
void setup()
{
  Serial.begin(115200); //inicalizácia sériovej komunikácie
  Blynk.begin(auth, ssid, pass); //inicializácia pripojenia na Blynk
  
  timer.setInterval(10000L, status_esp32); //cyklické volanie funkcie status_esp32 každých 10 sekúnd
  
  timer.setInterval(1000L, tlakovySenzor); //cyklické volanie funkcie tlakovySenzor každú 1 sekundu
    
  Serial.println(); //odoslanie prázdneho riadku na sériovú komunikáciu 

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
