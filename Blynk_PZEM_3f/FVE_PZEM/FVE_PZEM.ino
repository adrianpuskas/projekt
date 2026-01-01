#define BLYNK_TEMPLATE_ID "TMPLUV2L_lh7"
#define BLYNK_TEMPLATE_NAME "FVE"
#define BLYNK_AUTH_TOKEN "Gurl2O0DoNv46y8iKKJmNTx1w15NLJ7l"

//#define BLYNK_PRINT Serial

#include <ESP8266WiFi.h>
#include <BlynkSimpleEsp8266.h>
#include <PZEM004Tv30.h>


#if !defined(PZEM_RX_PIN) && !defined(PZEM_TX_PIN)
#define PZEM_RX_PIN 0
#define PZEM_TX_PIN 2
#endif

#if !defined(PZEM_SERIAL)
#define PZEM_SERIAL Serial2
#endif

#define NUM_PZEMS 3

PZEM004Tv30 pzems[NUM_PZEMS];

#define USE_SOFTWARE_SERIAL
#include <SoftwareSerial.h>

SoftwareSerial pzemSWSerial(PZEM_RX_PIN, PZEM_TX_PIN);

char auth[] = BLYNK_AUTH_TOKEN;

char ssid[] = "iHome";
char pass[] = "202PuskaS";

BlynkTimer timer;

#define pin V0
double celkovaSpotreba = 0.0;


BLYNK_WRITE(V11) {  // vPin is the Virtual Pin assigned to a Button Widget
 if (param.asInt() == 1) {  // Assumes if 1 then follow through..
    for (int i = 0; i  < NUM_PZEMS; i++){
       pzems[i].resetEnergy();
    }  
    celkovaSpotreba = 0.0;
  }
 Blynk.virtualWrite(V11, 0);
}


void PZEMs()
{
    for(int i = 0; i < NUM_PZEMS; i++){
      
        Serial.print("PZEM ");
        Serial.print(i);
        Serial.print(" - Address:");
        Serial.println(pzems[i].getAddress(), HEX);
        Serial.println("===================");

        float voltage = pzems[i].voltage();
        float current = pzems[i].current();
        float power = pzems[i].power();
        float energy = pzems[i].energy();
        celkovaSpotreba = celkovaSpotreba + energy;
        float frequency = pzems[i].frequency();
        float pf = pzems[i].pf();

        if(!(isnan(voltage) && isnan(current) && isnan(power) && isnan(energy) && isnan(frequency) && isnan(pf))){
    
            Blynk.virtualWrite((pin+(10*(i+3) + 0)), voltage);

            Blynk.virtualWrite((pin+(10*(i+3) + 1)), current);

            Blynk.virtualWrite((pin+(10*(i+3) + 2)), power);

            Blynk.virtualWrite((pin+(10*(i+3) + 3)), energy);

            Blynk.virtualWrite((pin+(10*(i+3) + 4)), frequency);

            Blynk.virtualWrite((pin+(10*(i+3) + 5)), pf);

        }
     
    }
    Blynk.virtualWrite(V12, celkovaSpotreba);
    celkovaSpotreba =0;

    

}

//_____________________________________________________________________

void setup()
{
  Serial.begin(115200);
  Blynk.begin(auth, ssid, pass);

  // For each PZEM, initialize it
    for(int i = 0; i < NUM_PZEMS; i++)
    {
         pzems[i] = PZEM004Tv30(pzemSWSerial, 0x10 + i);  
    }
  
  timer.setInterval(5000L, PZEMs);

}

void loop()
{

  if (WiFi.status() != WL_CONNECTED)
  {
    ESP.restart();
  }
  else
  {
    Blynk.run();
    timer.run();
  }

}
