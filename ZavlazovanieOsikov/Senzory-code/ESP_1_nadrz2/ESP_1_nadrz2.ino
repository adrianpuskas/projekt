#define BLYNK_TEMPLATE_ID           "TMPLblK60Pj-"  // definícia Blynk šablóny ID
#define BLYNK_DEVICE_NAME           "Zavlaha"  // definícia názvu zariadenia v Blynk aplikácii
#define BLYNK_AUTH_TOKEN            "NhAZeqig1jKjzGuVcYmdnAH_zzIWd3pL"  // autentifikačný token pre Blynk
#define BLYNK_PRINT Serial  // používanie sériového výstupu pre Blynk

#include <WiFi.h>  // WiFi knižnica pre ESP32
#include <WiFiClient.h>  
#include <BlynkSimpleEsp32.h>  // Blynk knižnica pre ESP32

char auth[] = BLYNK_AUTH_TOKEN;  // inicializácia premennej pre autentifikáciu
char ssid[] = "iHome";  // meno Wi-Fi siete
char pass[] = "202PuskaS";  // heslo Wi-Fi siete

#define Ultra_TRIG_PIN 5  // definícia čísla pinu pre vysielanie ultrazvukového signálu
#define Ultra_ECHO_PIN 17  // definícia čísla pinu pre prijímanie odrazeného signálu ultrazvuku
#define Float_PIN1 26  // definícia čísla pinu pre prvý plavák
#define Float_PIN2 27  // definícia čísla pinu pre druhý plavák

float trvanie = 0.0;
float vzdialenost_hladiny = 0.0;

BlynkTimer timer; // časovač pre Blynk


// *** STATUS ESP32 *** //
void status_esp32(){  // funkcia na zobrazovanie statusu ESP32
  Blynk.virtualWrite(V5, 1);  // zapisovanie hodnoty 1 do virtuálneho pinu V5 pre zobrazenie statusu v Blynk aplikácii
}

// *** Plaváky ***
void plavaky(){ // funkcia na kontrolu stavu plavákov
  int plavak1 = !digitalRead(Float_PIN1); // čítanie stavu prvého plaváka
  int plavak2 = !digitalRead(Float_PIN2); // čítanie stavu druhého plaváka

  Serial.print("Plavak 1: ");  // výpis stavu 
  Serial.println(plavak1);
  Serial.print("Plavak 2: ");
  Serial.println(plavak2);

 
  Blynk.virtualWrite(V72, plavak1);  // zapisovanie stavu prvého plaváka do virtuálneho pinu V72
  Blynk.virtualWrite(V73, plavak2);  // zapisovanie stavu druhého plaváka do virtuálneho pinu V73
  
}

// *** Množstvo vody ***
void vzdialenost() {
  // nastavenie signálu na pine TRIG, aby sa vygeneroval 10-mikrosekundový impulz
  digitalWrite(Ultra_TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(Ultra_TRIG_PIN, LOW);

 // meranie trvania impulzu na pine ECHO
  trvanie = pulseIn(Ultra_ECHO_PIN, HIGH);

  vzdialenost_hladiny = 0.017 * trvanie;
  if(vzdialenost_hladiny >=783 || vzdialenost_hladiny <=20) {
    vzdialenost_hladiny = 20;
  }

  int vypocet_vzdialenosti = (100*100*(122-vzdialenost_hladiny))/1000;

  Serial.println("*****************************");
  Serial.print("Vzdialenost senzora: ");
  Serial.print(vzdialenost_hladiny);
  Serial.println(" cm");

  Serial.print("Množstvo vody: ");
  Serial.print(vypocet_vzdialenosti);
  Serial.println(" L");

  Blynk.virtualWrite(V52, vypocet_vzdialenosti);  // zapisovanie objemu nádrže do virtuálneho pinu V52  

}

void setup()
{
  Serial.begin(115200); //inicalizácia sériovej komunikácie
  Blynk.begin(auth, ssid, pass); //inicializácia pripojenia na Blynk

  pinMode(Ultra_TRIG_PIN, OUTPUT);
  pinMode(Ultra_ECHO_PIN, INPUT);

  pinMode(Float_PIN1, INPUT_PULLUP);
  pinMode(Float_PIN2, INPUT_PULLUP);
  
  timer.setInterval(10000L, vzdialenost); //cyklické volanie funkcie vzdialenost každých 10 sekúnd
  timer.setInterval(10000L, plavaky); //cyklické volanie funkcie plavaky každých 10 sekúnd
  timer.setInterval(10000L, status_esp32); //cyklické volanie funkcie vzdialenost každých 10 sekúnd

  Serial.println(""); //odoslanie prázdneho riadku na sériovú komunikáciu 
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
