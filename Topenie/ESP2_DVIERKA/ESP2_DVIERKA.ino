#define BLYNK_TEMPLATE_ID "TMPL4kDwpWu-n"
#define BLYNK_TEMPLATE_NAME "Topenie Osikov"
#define BLYNK_AUTH_TOKEN "Mrf5LJuXlXRyqIz46IKkbgeZAfXC0q8x"
  
#include <WiFi.h>  // WiFi knižnica pre ESP32
#include <WiFiClient.h>
#include <BlynkSimpleEsp32.h>  // Blynk knižnica pre ESP32
#include <AccelStepper.h>
#include <HTTPClient.h>

char auth[] = BLYNK_AUTH_TOKEN;  // inicializácia premennej pre autentifikáciu
char ssid[] = "ESP";  // meno Wi-Fi siete
char pass[] = "202PuskaS";  // heslo Wi-Fi siete

#define spinac_dole 32
#define spinac_hore 33
#define tlacidlo_zavriet 35 // skontrolovat dostupnost 35 !!!!!!!!!!!!!!!!!!!!

#define dir_pin 12
#define step_pin 14
#define sleep_pin 22
#define reset_pin 23

boolean zmena = false;

BlynkTimer timer; // vytvorenie objektu BlynkTimer pre použitie časovača

int manualMode;
int prevadzkova_teplota_kotla;
int wifiStatus;
int kroky = 0;
int krokyMap = 0;

int nastavenySlider = 0;

AccelStepper stepper(1, 12, 14);

int maxKroky = 0;
int aktualnaPoloha = 0;
int tlacidlo_zavriet_status = 0;

float vonkajsiaTeplota;
float vonkajsiaVlhkost;
float teplotaKotla;

// Blynk wifi status
BLYNK_WRITE(V4) {
  int value = param.asInt();

  if (value == 0) {
    Blynk.logEvent("wifi", "Pripojenie na Wi-Fi zlyhalo!") ;
    wifiStatus = 0;
    Blynk.setProperty(V4, "color","f04a29");
  }else {
    wifiStatus = 1;
    Blynk.setProperty(V4, "color","#71d459");
  }
}


// Blynk manual/auto
BLYNK_WRITE(V5){
  int value = param.asInt();
  manualMode = value;
  Blynk.virtualWrite(V5, value);
}

// Blynk nastavena prevadzkova teplota kotla
BLYNK_WRITE(V0){
  int value = param.asInt();
  prevadzkova_teplota_kotla = value;
}


// Blynk zatvorenie dvierok
BLYNK_WRITE(V2) {
    int value = param.asInt();
    tlacidlo_zavriet_status = value;

}
int zmenaStavu = 0;
void fyzickeTlacidloZavrietDvierka(){
    if ((digitalRead(tlacidlo_zavriet) == LOW) && (tlacidlo_zavriet_status == 1)) {
      tlacidlo_zavriet_status = 0;
      Serial.print("Tlacidlo stlacene.. ");
      zmenaStavu = 1;
      }
    else if ((digitalRead(tlacidlo_zavriet) == LOW) && (tlacidlo_zavriet_status == 0)) {
      tlacidlo_zavriet_status = 1;
      Serial.print("Tlacidlo stlacene.. ");
      zmenaStavu = 1;
    }
    else {
        Serial.print("Cakam na stlacenie tlacidla.. ");
    }
    if (zmenaStavu = 1){
  Blynk.virtualWrite(V2, tlacidlo_zavriet_status);

  }
}


void zistiTeplotuKotla()
{
    // Vytvorenie objektu HTTPClient
    HTTPClient http;

    // URL pre získanie hodnoty z pinu V1
    String url2 = "http://blynk.cloud/external/api/get?token=JT_8ua2rn-cxt1JlkCHIIa7cSK-Rykmz&V1";
    

    // Nastavenie URL pre HTTP GET požiadavku
    http.begin(url2);

    // Vykonanie HTTP GET požiadavky
    int httpCode2 = http.GET();
    if (httpCode2 == HTTP_CODE_OK) {
    String teplotaKotlaString = http.getString();
    teplotaKotla = teplotaKotlaString.toFloat();
      Serial.print("Teplota kotla: ");
      Serial.println(teplotaKotla);
      Blynk.virtualWrite(V1, teplotaKotla);
    } else {
    
      Serial.println("Chyba pri HTTP požiadavke");
    }

    // Ukončenie HTTP spojenia
    http.end();
}


void coloring() {
 
  Blynk.virtualWrite(V10, teplotaKotla);

  if (teplotaKotla <=30) {                                                //modra
    Blynk.setProperty(V10, "color","#3b64d4");
  }else if(teplotaKotla > 30 && teplotaKotla <=45) {                      //zlta
    Blynk.setProperty(V10, "color","#ffe226");
  }else if(teplotaKotla > 45 && teplotaKotla <=65) {                      //zelena
    Blynk.setProperty(V10, "color","#71d459");
  }else if(teplotaKotla > 65 && teplotaKotla <=80) {                      //oranzova
    Blynk.setProperty(V10, "color","#fab339");
  }else {                                                                 //cervena
    Blynk.setProperty(V10, "color","#f04a29");
  }
}


void inicializaciaPolohy() {
  Serial.println("INICIALIZACIA");

  digitalWrite(sleep_pin, HIGH);
  digitalWrite(reset_pin, HIGH);
  

  digitalWrite(dir_pin, HIGH);
  while (digitalRead(spinac_dole) == LOW) {   
    for (int i = 0; i < 10; i++)
    {
      digitalWrite(step_pin, HIGH);
      delayMicroseconds(2000);
      digitalWrite(step_pin, LOW);
      delayMicroseconds(2000); 
    }
  }

  digitalWrite(dir_pin, LOW);

  while(digitalRead(spinac_hore) == LOW){
    for (int i = 0; i < 10; i++)
    {
      digitalWrite(step_pin, HIGH);
      delayMicroseconds(2000);
      digitalWrite(step_pin, LOW);
      delayMicroseconds(2000); 
    }

    maxKroky+= 1;
  }  

  aktualnaPoloha = map(maxKroky, 0, maxKroky, 0, 100);
  Blynk.virtualWrite(V15, aktualnaPoloha);
  kroky = maxKroky;

  Serial.println("FINISH INICIALIZACIE ");
  Serial.print("Aktuálna poloha: ");
  Serial.println(aktualnaPoloha);

  Blynk.virtualWrite(V12, 0);
  Blynk.virtualWrite(V14, 1);
  Blynk.setProperty(V14, "color", "#99d075");

  digitalWrite(sleep_pin, LOW);
  digitalWrite(reset_pin, LOW);
  delay(2000);

}

void sendSensorStep()
{   
    

    //aktualizácia wifi
    Blynk.virtualWrite(V4, 1);
    if (tlacidlo_zavriet_status == 0) { // ak nie je stlacene manualne zatvorenie dvierok, pokracuj tu
    // Ak sme v režime "Automatika", vykonáme logiku pre riadenie
      if (manualMode == 0) {
        Serial.println("\n*** AUTOMATICKÝ REŽIM ***");
        Serial.print("\nNastavena pracovna teplota kotla v automatike: ");
        Serial.println(prevadzkova_teplota_kotla);
        Serial.print("\n ");
        Serial.print("\nTeplota kotla v automatike: ");
        Serial.println(teplotaKotla);
        
        if (teplotaKotla >= 80) {
            nastavenySlider = 0;
            Serial.println("!!! Dosiahnuta maximálna teplota kotla 80°C !!! zatváram dvierka");
            
        } else if  (teplotaKotla >= prevadzkova_teplota_kotla + 10 && teplotaKotla < 79.9) {
            nastavenySlider = 0;
            Serial.println("!!! Kotol teplejsi o 10°C !!!");
            
        } else if  (teplotaKotla >= prevadzkova_teplota_kotla + 5 && teplotaKotla < prevadzkova_teplota_kotla + 9.9) {
            nastavenySlider = 1;
            Serial.println("!!! Kotol teplejsi o 5°C !!!");
            
        } else if  (teplotaKotla >= prevadzkova_teplota_kotla - 5 && teplotaKotla < prevadzkova_teplota_kotla + 4.9) {
            nastavenySlider = 3;
            Serial.println("!!! Dosiahnuta nastavena prevadzkova teplota !!!");
            
        } else if  (teplotaKotla <= prevadzkova_teplota_kotla - 35) {
            nastavenySlider = 60;
            Serial.println("!!! viac ako 35°C do dosiahnutia nastavenej prevadzkovej teploty !!!");
            
        } else if  (teplotaKotla <= prevadzkova_teplota_kotla - 30 && teplotaKotla > prevadzkova_teplota_kotla - 34.9 ) {
            nastavenySlider = 50;
            Serial.println("!!! 30°C do dosiahnutia nastavenej prevadzkovej teploty !!!");
                
        } else if  (teplotaKotla <= prevadzkova_teplota_kotla - 20 && teplotaKotla > prevadzkova_teplota_kotla - 29.9) {
            nastavenySlider = 40;
            Serial.println("!!! 20°C do dosiahnutia nastavenej prevadzkovej teploty !!!");
            
        } else if  (teplotaKotla <= prevadzkova_teplota_kotla - 15 && teplotaKotla > prevadzkova_teplota_kotla - 19.9) {
            nastavenySlider = 30;
            Serial.println("!!! 15°C do dosiahnutia nastavenej prevadzkovej teploty !!!");
            
        } else if  (teplotaKotla <= prevadzkova_teplota_kotla - 10 && teplotaKotla > prevadzkova_teplota_kotla - 14.9) {
            nastavenySlider = 10;
            Serial.println("!!! 10°C do dosiahnutia nastavenej prevadzkovej teploty !!!");
            
        } else if  (teplotaKotla <= prevadzkova_teplota_kotla - 5 && teplotaKotla > prevadzkova_teplota_kotla - 9.9) {
            nastavenySlider = 5;
            Serial.println("!!! 5°C do dosiahnutia nastavenej prevadzkovej teploty !!!");
        }
      Blynk.virtualWrite(V13, nastavenySlider);  
      zmena = true;
      Serial.print("Aktuálna poloha: ");
      Serial.println(aktualnaPoloha);
      }         

      else {  
        Blynk.syncVirtual(13);
        if(nastavenySlider != aktualnaPoloha){
          zmena = true;
        }
        else {
          Serial.println("\n*** MANUÁLNY REŽIM ***");
        }
      }
    } 
    else {
        Serial.println("\n*** MANUÁLNE UZAVRETÉ DVIERKA Z DOVODU NAKLADANIA DREVA ***");
        nastavenySlider = 0;
        zmena = true;
      }



   if(zmena) {
    digitalWrite(sleep_pin, HIGH);
    digitalWrite(reset_pin, HIGH);
    
    if(nastavenySlider < aktualnaPoloha) {
      Serial.println("Zatváram dvierka ...");
      digitalWrite(dir_pin, HIGH);
      while(aktualnaPoloha != nastavenySlider) {

        for (int i = 0; i < 10; i++)
        {
          digitalWrite(step_pin, HIGH);
          delayMicroseconds(2000);
          digitalWrite(step_pin, LOW);
          delayMicroseconds(2000); 
        }
        
        kroky -=1;

        aktualnaPoloha = map(kroky,0,maxKroky,0,100);
        // Blynk.virtualWrite(V15, aktualnaPoloha); presunute mimo while
      
        // bezpečnostne opatrenie
       if (aktualnaPoloha > 0 && digitalRead(spinac_dole) == HIGH) {
          Blynk.virtualWrite(V14, 0);
          ESP.restart();    //reštartovanie zariadenia v prípade, že
        } else {
          Blynk.virtualWrite(V14, 1);
        }
                
       if (aktualnaPoloha == nastavenySlider)
        {
          Blynk.virtualWrite(V15, aktualnaPoloha); //presunute z while
          digitalWrite(sleep_pin, LOW); // presunute 
          digitalWrite(reset_pin, LOW); // presunute 
          zmena= false;
          break;
        }
      }    
      
    } else {
      Serial.println("Otváram dvierka ...");
      digitalWrite(dir_pin, LOW);
      while(aktualnaPoloha != nastavenySlider) {

        for (int i = 0; i < 10; i++)
        {
          digitalWrite(step_pin, HIGH);
          delayMicroseconds(2000);
          digitalWrite(step_pin, LOW);
          delayMicroseconds(2000);
        }
        
        kroky +=1;
        
        aktualnaPoloha = map(kroky,0,maxKroky,0,100);
        //Blynk.virtualWrite(V15, aktualnaPoloha); presunute mimo while
        
        // bezpečnostne opatrenie
       if (aktualnaPoloha < 100 && digitalRead(spinac_hore) == HIGH) {
          Blynk.virtualWrite(V14, 0);
          ESP.restart();    //reštartovanie zariadenia v prípade, že
        } else {
          Blynk.virtualWrite(V14, 1);
        }
                
       if (aktualnaPoloha == nastavenySlider)
        {
          Blynk.virtualWrite(V15, aktualnaPoloha); //presunute z while
          digitalWrite(sleep_pin, LOW); // presunute 
          digitalWrite(reset_pin, LOW); // presunute 
          zmena= false; 
          break;
        }
      }      
    }  
    zmena= false;  
    digitalWrite(sleep_pin, LOW); // presunute do aktualnaPoloha == nastaveny slider
    digitalWrite(reset_pin, LOW); // presunute do aktualnaPoloha == nastaveny slider
   }
   //delay(500);  
  }


// tlacidlo incializacia
BLYNK_WRITE(V12){
  int value = param.asInt();
  
  if (value == 1) {
    inicializaciaPolohy(); 
  }
  delay(500);
}

// slider
BLYNK_WRITE(V13){
  int value = param.asInt();
  nastavenySlider = value;
  zmena = true;
  delay(500);
}

// stav inicializacie
BLYNK_WRITE(V14){
  int value = param.asInt();
  delay(500);
}

BLYNK_WRITE(V15) {
  int value = param.asInt();
  Serial.print("Aktuálna poloha BLYNK: ");
  Serial.println(value);
  delay(500);
}


void setup()
{
  
  Serial.begin(115200);
  
  // Pripojenie k Blynk
  Blynk.begin(auth, ssid, pass); //inicializácia pripojenia na Blynk
 
  pinMode(step_pin, OUTPUT);
  pinMode(dir_pin, OUTPUT);
  pinMode(sleep_pin, OUTPUT);
  pinMode(reset_pin, OUTPUT);

  digitalWrite(sleep_pin, LOW);
  digitalWrite(reset_pin, LOW);

  for (int i = 0; i <= 15; i++) {
    Blynk.syncVirtual(i);
  }

  pinMode(spinac_dole, INPUT_PULLUP);
  pinMode(spinac_hore, INPUT_PULLUP);
  pinMode(tlacidlo_zavriet, INPUT_PULLUP);
  Blynk.virtualWrite(V14, 0);
  Blynk.setProperty(V14, "color", "#ce6042");

  Blynk.virtualWrite(V4, 1);
  Blynk.setProperty(V4, "color","#71d459");

    // Nastavenie počiatočnej polohy
  inicializaciaPolohy();
  timer.setInterval(2000L, sendSensorStep);
  timer.setInterval(2000L, zistiTeplotuKotla); 
  timer.setInterval(2000L, coloring); 
  timer.setInterval(2000L, fyzickeTlacidloZavrietDvierka); 
}



void loop()
{  
  
  if (WiFi.status() != WL_CONNECTED) //kontrola, či je zariadenie pripojené
  {
    ESP.restart();    //reštartovanie zariadenia v prípade, že nie je pripojené
  }
  else
  {
    
    Blynk.run(); //vykonávanie funkcií na Blynk serveri
    timer.run(); //vykonávanie funkcií s nastavenými intervalmi

  }

}
 
