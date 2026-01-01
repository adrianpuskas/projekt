# Komunikácia RS232-USB s hybridným inverterom Daxtromn v jazyku Python

## Prehľad
Tento projekt má za cieľ uľahčiť komunikáciu medzi [hybridným inverterom Daxtromn](https://daxtromn-power.com/products/6.2kw-hybrid-solar-inverter-pure-sine-wave-220vac-output-48vdc-input-120a-mppt-solar-charger-controller-6200w-european-union-stock-fast-ship) 
a počítačom prostredníctvom rozhrania RS232-USB. 
Hlavné funkcie zahŕňajú čítanie rôznych hodnôt z invertera, nastavovanie špecifických nastavení a ovládanie pomocou aplikácie Blynk.
Tento README poskytuje prehľad štruktúry projektu, pokyny na použitie a relevantné podrobnosti pre vývojárov a používateľov.

## Funkcie
- **Čítanie hodnôt**: Projekt umožňuje používateľom získať rôzne parametre z hybridného invertera Daxtromn, ako je aktuálny výkon, stav batérie, stav siete atď.
- **Nastavovanie nastavení**: Používatelia môžu upravovať špecifické nastavenia invertera, vrátane prahov nabíjania/vybíjania, limity výkonu a ďalších konfigurovateľných parametrov.
- **Sériová komunikácia**: Projekt zabezpečuje sériovú komunikáciu medzi počítačom a inverterom prostredníctvom rozhrania RS232-USB, čo umožňuje výmenu údajov.
- **Používateľsky prívetivé rozhranie využitím Blynk**: Projekt sa snaží poskytnúť intuitívne rozhranie pre používateľov na interakciu s inverterom, čím je prístupný pre začiatočníkov aj skúsených používateľov.

## Inštalácia
1. **Klonovanie Repozitára**: Klonujte repozitár projektu z [GitHub link](https://gitlab.com/kristonela/fve-osikov.git).
2. **Inštalácia Závislostí**: Prejdite do adresára projektu a nainštalujte požadované závislosti pomocou `pip`:
- `BlynkLib`: Modul pre komunikáciu s platformou Blynk, používaný na zapisovanie údajov.
  ```
  pip install blynk-library-python
  ```
- `requests`: Modul pre HTTP požiadavky, využívaný na čítanie údajov z platformy Blynk.
  ```
  pip install requests
  ```
- `serial`: Modul pre sériovú komunikáciu, používaný na komunikáciu s meničom.
  ```
  pip install pyserial
  ```
- `crcmod`: Modul pre výpočet kontrolného súčtu CRC, používaný pri komunikácii s meničom.
  ```
  pip install crcmod
  ```
3. **Pripojenie RS232-USB Kábla**: Pripojte RS232-USB kábel medzi počítačom a hybridným inverterom Daxtromn.

## Spustenie
Spustite hlavný Python Watchdog skript pre spustenie aplikácie:
```
  python Watchdog.py
  ```
`Watchdog` zabezečí automatické opätovné spustene programu v prípade chyby. Interaktívne rozhranie je implemenované v Blynk aplikácií. 

## Licencia
Tento projekt je licencovaný pod [MIT licenciou](LICENSE).

## Autori
Kristína Pavličková & Adrián Puškáš
