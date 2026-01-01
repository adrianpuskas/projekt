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

#define DHTPIN 22 // definovanie pinu, na ktorom je pripojený DHT senzor
#define DHTTYPE DHT11 // definovanie typu DHT senzora

BlynkTimer timer; // vytvorenie objektu BlynkTimer pre použitie časovača

DHT dht(DHTPIN, DHTTYPE); // vytvorenie objektu DHT a priradenie pinu a typu

#define bateria 33 // definovanie pinu, na ktorom je pripojená batéria
#define vlhkostPody 32 // definovanie pinu, na ktorom je pripojený senzor vlhkosti pôdy

int status_bateria = -1; // deklarácia premennej pre stav batérie
int status_vlhkost = -1; // deklarácia premennej pre stav vlhkosti pôdy

// *** Mapovacia funkcia *** //
// funkcia pre mapovanie hodnôt z analógového senzora na percentuálne hodnoty
double mapuj(double analogHodnota, double in_min, double in_max, double out_min, double out_max)
{
    double hodnota;

    if (((analogHodnota - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)>=100)
    {
      hodnota = 100;
    }
    else if(((analogHodnota - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)<=0)
    {
      hodnota = 0;
    }
    else 
    {
      hodnota = ((analogHodnota - in_min) * (out_max - out_min) / (in_max - in_min) + out_min);
    }
    
    return hodnota;    
}

// *** Senzor pody *** //
void senzorPody()
{
  int senzorPody = analogRead(vlhkostPody);
  double senzorPodyPercento = mapuj(senzorPody, 2900, 1200, 0, 100);

  if (isnan(senzorPody) ) {
    Serial.println(F("Citanie zo senzora pôdy sa nepodarilo !"));
    return;
  }
  else
  {
    status_vlhkost = senzorPodyPercento;
  }
  
  Blynk.virtualWrite(V21, senzorPodyPercento);  // Zapisanie percentuálnej hodnoty do virtuálneho pinu V21
  
  Serial.print("Vlhkost pody analog hodnota: "); // Vypís stavu
  Serial.print(senzorPody);
  Serial.print("\t Percentualna hodnota: ");
  Serial.print(senzorPodyPercento);
  Serial.println(" %");
}

// *** Bateria *** //
void snimanieBaterie() // Funkcia snímania stavu baterie
{
  int senzorBateria = analogRead(bateria); // Načítanie hodnoty z analógového pinu baterie
  double voltage = mapuj(senzorBateria, 1450, 2360, 2.8, 4.2); // Mapovanie nameranej hodnoty na napätie batérie
  int senzorBateriaPercento = mapuj(voltage, 2.8, 4.2, 0, 100); // Mapovanie napätia batérie na percentuálnu hodnotu
  
  if (isnan(senzorBateria)) { // Ak sú namerané hodnoty neplatné, vypíše sa chybová správa 
  Serial.println(F("Citanie z baterie sa nepodarilo !"));
  return;
  }
  else // Inak sa uloží percentuálna hodnota do premennej status_bateria
  {
  status_bateria = senzorBateriaPercento;
  }
  
  Blynk.virtualWrite(V22, senzorBateriaPercento); // Zapisanie percentuálnej hodnoty do virtuálneho pinu V22
  
  if(senzorBateriaPercento == 20){ // Ak je percentuálna hodnota batérie 20, zaznamená sa udalosť do Blynk logov
  Blynk.logEvent("senzor","Senzor 1 - Batéria takmer vybitá !");
  }
  
  Serial.print("Bateria analog hodnota: "); // Vypís stavu
  Serial.print(senzorBateria);
  Serial.print("\t V = "); 
  Serial.print(voltage);
  Serial.print("\t Percentualna hodnota: "); 
  Serial.print(senzorBateriaPercento);
  Serial.println(" %");
}
 

// *** DHT senzor *** //
void DHTSenzor() {
  int vlhkost = dht.readHumidity(); // Načítanie vlhkosti z DHT senzora
  double teplota = dht.readTemperature(); // Načítanie teploty z DHT senzora

  if (isnan(vlhkost) || isnan(teplota)) { // Ak sú namerané hodnoty neplatné, vypíše sa chybová správa 
    Serial.println(F("Citanie z DHT senzora sa nepodarilo !"));
    return;
  }
  double pocitovaTeplota = dht.computeHeatIndex(teplota, vlhkost, false); // Vypočíta sa pocitová teplota
  
  Serial.print(teplota); // Vypís stavu
  Serial.print(F("°C "));
  Blynk.virtualWrite(V20, teplota); // Zapisanie nameranej hodnoty teploty do virtuálneho pinu V20
}


// *** Status senzora pre BLYNK *** //
void statusSenzora(){
  Blynk.virtualWrite(V23, 1); // odoslanie hodnoty 1 do virtuálneho pinu V23 v Blynk aplikácii
}


void setup()
{

  Serial.begin(115200); //inicalizácia sériovej komunikácie
  Blynk.begin(auth, ssid, pass); //inicializácia pripojenia na Blynk
  dht.begin(); // inicializácia DHT senzora

  timer.setInterval(5000L, snimanieBaterie); //cyklické volanie funkcie snimanieBaterie každých 5 sekúnd
  timer.setInterval(5000L, DHTSenzor); //cyklické volanie funkcie DHTSenzor každých 5 sekúnd
  timer.setInterval(5000L, senzorPody); //cyklické volanie funkcie senzorPody každých 5 sekúnd
  timer.setInterval(5000L, statusSenzora); //cyklické volanie funkcie statusSenzora každých 5 sekúnd
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
