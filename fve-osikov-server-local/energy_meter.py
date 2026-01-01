import sqlite3
import calendar
import time
from datetime import datetime, timedelta, time as dtime
from blynkSender import blynk_write, blynk_read

def calculate_daily_energy():
    try:
        conn = sqlite3.connect('solar_data.db')
        c = conn.cursor()

        # Ak chceš použiť aktuálny deň, nahraď riadok nižšie: datum = datetime.now().date()
        datum = (f"{rok}-{mesiac}-{den}")
        
        #datum = "2025-08-01"
        today = datetime.strptime(datum, "%Y-%m-%d").date()
        print(f"Dátum: {today}")

        start_time = datetime.combine(today, dtime.min)
        end_time = datetime.combine(today, dtime.max)
        print(f"Rozsah pre výpočet dennej energie: {start_time.date()} → {end_time.date()}")

        c.execute('''SELECT pv_input_power, pv2_input_power, battery_power, ac_output_power 
                     FROM solar_data 
                     WHERE timestamp BETWEEN ? AND ?''',
                  (start_time, end_time))
        rows = c.fetchall()

        pv_energy = 0.0
        battery_charging_energy = 0.0
        battery_discharging_energy = 0.0
        ac_energy = 0.0
        interval_hours = 5 / 3600  # 5 sekúnd

        for row in rows:
            pv_energy += (float(row[0]) + float(row[1])) * interval_hours / 1000
            if float(row[2]) > 0:
                battery_charging_energy += float(row[2]) * interval_hours / 1000
            elif float(row[2]) < 0:
                battery_discharging_energy += abs(float(row[2])) * interval_hours / 1000
            ac_energy += float(row[3]) * interval_hours / 1000

        print1 = f"""\nDenná výroba/spotreba {today}:
\tSolar: \t\t\t\t{pv_energy:.3f} kWh
\tBatérie (nabíjanie): \t{battery_charging_energy:.3f} kWh
\tBatérie (vybíjanie): \t{battery_discharging_energy:.3f} kWh
\tSpotreba: \t\t\t{ac_energy:.3f} kWh"""
        
        print(print1)
        blynk_write(101, print1)

    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Chyba pri výpočte dennej energie: {e}")
    finally:
        conn.close()


def calculate_monthly_energy():
    try:
        conn = sqlite3.connect('solar_data.db')
        c = conn.cursor()

        today = datetime.now().date()
        #year = today.year
        #month = today.month
        year = int(rok)
        month = int(mesiac)

        first_day = datetime(year, month, 1)
        last_day_number = calendar.monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_number)

        start_time = datetime.combine(first_day, dtime.min)
        end_time = datetime.combine(last_day, dtime.max)

        c.execute('''SELECT pv_input_power, pv2_input_power, battery_power, ac_output_power 
                     FROM solar_data 
                     WHERE timestamp BETWEEN ? AND ?''',
                  (start_time, end_time))
        rows = c.fetchall()

        pv_energy = 0.0
        battery_charging_energy = 0.0
        battery_discharging_energy = 0.0
        ac_energy = 0.0
        interval_hours = 5 / 3600

        for row in rows:
            pv_energy += (float(row[0]) + float(row[1])) * interval_hours / 1000
            if float(row[2]) > 0:
                battery_charging_energy += float(row[2]) * interval_hours / 1000
            elif float(row[2]) < 0:
                battery_discharging_energy += abs(float(row[2])) * interval_hours / 1000
            ac_energy += float(row[3]) * interval_hours / 1000

        print2 = f"""\n

[{datetime.now().strftime('%H:%M:%S')}]
Mesačná výroba/spotreba za obdobie \n{month:02d}/{year}: {start_time.date()} → {end_time.date()}
\tSolar: \t\t\t\t{pv_energy:.3f} kWh
\tSpotreba: \t\t\t{ac_energy:.3f} kWh"""
        
        print(print2)
        blynk_write(101, print2)

    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Chyba pri výpočte mesačnej energie: {e}")
    finally:
        conn.close()


# Spustenie
if __name__ == "__main__":
    AUTO_RESET_DELAY = timedelta(minutes=1)  # tu nastavíš po koľkých minútach má vrátiť aktuálny dátum
    last_manual_change = datetime.now()
    posledny_datum_z_blynku = None

    while True:
        # čítanie dátumu z Blynk
        rok = str(blynk_read("v102"))
        mesiac = str(blynk_read("v103"))
        den = str(blynk_read("v104"))
        aktualny_datum_z_blynku = f"{rok}-{mesiac}-{den}"

        if aktualny_datum_z_blynku != posledny_datum_z_blynku:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Zistená manuálna zmena dátumu: {aktualny_datum_z_blynku}")
            posledny_datum_z_blynku = aktualny_datum_z_blynku
            last_manual_change = datetime.now()

        # výpočty
        calculate_monthly_energy()
        calculate_daily_energy()

        # automatické obnovenie dátumu
        if datetime.now() - last_manual_change > AUTO_RESET_DELAY:
            aktualny_datum = datetime.now()
            blynk_write(102, aktualny_datum.year)
            blynk_write(103, f"{aktualny_datum.month:02d}")
            blynk_write(104, f"{aktualny_datum.day:02d}")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Automaticky obnovený dátum na aktuálny: {aktualny_datum.date()}")
            posledny_datum_z_blynku = aktualny_datum.strftime("%Y-%m-%d")
            last_manual_change = datetime.now()

        time.sleep(5)


