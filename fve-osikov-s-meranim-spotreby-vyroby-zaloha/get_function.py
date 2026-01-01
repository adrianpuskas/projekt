import sqlite3
import time
import os
from datetime import datetime
import globals as gp
import parametersEnum as param
import deviceModeEnum as modes
import warningsEnum as warn
import flagEnum as flags
import JKBMS as BMS
from blynkSender import blynk_write, blynk_read

# vytvorenie nazvu databazy podla aktualneho mesiaca a roku v podpriečinku db_data
DB_FOLDER = "db_data"

def get_db_filename():
    # vytvor priečinok ak neexistuje
    os.makedirs(DB_FOLDER, exist_ok=True)

    # názov DB podľa mesiaca a roka
    filename = datetime.now().strftime("%m-%Y.db")

    # kompletná cesta do podpriečinka
    return os.path.join(DB_FOLDER, filename)


# Inicializácia SQLite databázy
def init_db():
    db_file = get_db_filename()
    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS solar_data (
                        timestamp DATETIME,
                        pv_input_power REAL,
                        pv2_input_power REAL,
                        battery_power REAL,
                        ac_output_power REAL,
                        battery_capacity REAL,
                        pv_voltage REAL,
                        pv2_voltage REAL,
                        inverter_temp REAL
                    )''')
        conn.commit()
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Chyba pri inicializácii databázy {db_file}: {e}", flush=True)
    finally:
        conn.close()

# Funkcia na ukladanie údajov do databázy
def save_to_db(pv_input_power, pv2_input_power, battery_power, ac_output_power,
               battery_capacity, pv_voltage, pv2_voltage, inverter_temp):

    db_file = get_db_filename()
    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        c.execute('''INSERT INTO solar_data (
                        timestamp, pv_input_power, pv2_input_power, battery_power, ac_output_power,
                        battery_capacity, pv_voltage, pv2_voltage, inverter_temp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (timestamp, float(pv_input_power), float(pv2_input_power), float(battery_power),
                   float(ac_output_power), float(battery_capacity), float(pv_voltage),
                   float(pv2_voltage), float(inverter_temp)))
        conn.commit()
        print(f"\tZáznam uložený do databázy ({db_file}): {timestamp}", flush=True)
    except Exception as e:
        print(f"\tChyba pri ukladaní do databázy {db_file}: {e}", flush=True)
    finally:
        conn.close()


def flags_enabled():
    try:
        response = gp.run_command_get(b'QFLAG')
        if response is None:
            print(f"\t⚠️ Chyba: Neprišla žiadna odpoveď na príkaz QFLAG.", flush=True)
            return
        try:
            substring_start = response.index(b'(E') + 1
            substring_end = response.index(b'd') + 1
            substring = response[substring_start:substring_end].decode('latin-1')
            position_e = substring.index('E')
            position_d = substring.index('D')
            substring_e = substring[position_e + 1:position_d]
            for char in substring_e:
                try:
                    flag = next(option for option in flags.Option if option.get_code() == char.upper())
                    gp.flags_enabled.append(flag.get_name())
                except StopIteration:
                    pass
        except Exception as e:
            print(f"\tChyba pri spracovaní QFLAG: {e}", flush=True)
    except Exception as e:
        print(f"\tChyba pri QFLAG: {e}", flush=True)

def flags_disabled():
    try:
        response = gp.run_command_get(b'QFLAG')
        if response is None:
            print(f"\t⚠️ Chyba: Neprišla žiadna odpoveď na príkaz QFLAG.", flush=True)
            return
        try:
            substring_start = response.index(b'(E') + 1
            substring_end = response.index(b'd') + 1
            substring = response[substring_start:substring_end].decode('latin-1')
            position_d = substring.index('D')
            substring_d = substring[position_d + 1:]
            for char in substring_d:
                try:
                    flag = next(option for option in flags.Option if option.get_code() == char.upper())
                    gp.flags_disabled.append(flag.get_name())
                except StopIteration:
                    pass
        except Exception as e:
            print(f"\tChyba pri spracovaní QFLAG: {e}", flush=True)
    except Exception as e:
        print(f"\tChyba pri QFLAG: {e}", flush=True)

def nastavenia_menica():
    gp.flags_enabled.clear()
    gp.flags_disabled.clear()
    flags_enabled()
    flags_disabled()
    print(f"\t-> Flags ENABLED: {gp.flags_enabled}", flush=True)
    print(f"\t-> Flags DISABLED: {gp.flags_disabled}", flush=True)

def FW_version():
    try:
        response = gp.run_command_get(b'QVFW')
        if response is None:
            print(f"\t⚠️ Chyba: Neprišla žiadna odpoveď na príkaz QVFW.", flush=True)
            return
        try:
            version = response[1]
            print(f"\t-> FW verzia: {version}", flush=True)
        except Exception as e:
            print(f"\tChyba pri spracovaní QVFW: {e}", flush=True)
    except Exception as e:
        print(f"\tChyba pri QVFW: {e}", flush=True)

def mode_zariadenia():
    print(" -> Mode zariadenia:", flush=True)
    try:
        response = gp.run_command_get(b'QMOD')
        if response is None:
            print(f"\t⚠️ Chyba: Neprišla žiadna odpoveď na príkaz QMOD.", flush=True)
            return
        try:
            first_character = response[1:2].decode('latin-1')
            mode = None
            for device_mode in modes.DeviceMode:
                if device_mode.get_char() == first_character:
                    mode = device_mode
                    break
            if mode:
                try:
                    blynk_write(1, mode.name)
                except Exception as e:
                    print(f"\tChyba pri odoslaní do Blynku (mode): {e}", flush=True)
                print(f"\t{mode.name}", flush=True)
            else:
                print(f"\tInvalid device mode: {first_character} (neznámy mód, pokračujem)", flush=True)
                blynk_write(1, f"Unknown_{first_character}")
        except Exception as e:
            print(f"\tChyba pri spracovaní QMOD: {e}", flush=True)
    except Exception as e:
        print(f"\tChyba pri QMOD: {e}", flush=True)

def nastaveneData():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] -> Nastavené dáta:", flush=True)
    try:
        response = gp.run_command_get(b'QPIRI')
        if response is None:
            print(f"\t⚠️ Chyba: Neprišla žiadna odpoveď na príkaz QPIRI.", flush=True)
            return
        try:
            values = response.strip().split()
            decoded_values = [value.decode('latin-1').lstrip("b'(").rstrip("'") for value in values]
            
            brv = param.Params.BATTERY_RECHARGE_VOLTAGE
            print(f"\t{brv.get_name()}: {decoded_values[8]} {brv.get_unit()}", flush=True)
            blynk_write(brv.get_pin_set_value(), decoded_values[8])

            buv = param.Params.BATTERY_UNDER_VOLTAGE
            print(f"\t{buv.get_name()}: {decoded_values[9]} {buv.get_unit()}", flush=True)
            blynk_write(buv.get_pin_set_value(), decoded_values[9])
                
            bbv = param.Params.BATTERY_BULK_VOLTAGE
            print(f"\t{bbv.get_name()}: {decoded_values[10]} {bbv.get_unit()}", flush=True)
            blynk_write(bbv.get_pin_set_value(), decoded_values[10])

            bfv = param.Params.BATTERY_FLOAT_VOLTAGE
            print(f"\t{bfv.get_name()}: {decoded_values[11]} {bfv.get_unit()}", flush=True)
            blynk_write(bfv.get_pin_set_value(), decoded_values[11])
            
            bt = param.Params.BATTERY_TYPE
            value = decoded_values[12]
            value_str = {"0": "AGM", "1": "Flooded Battery", "2": "User"}.get(value, "Unknown")
            print(f"\t{bt.get_name()}: {value_str}", flush=True)
            blynk_write(bt.get_pin_set_value(), decoded_values[12])
                
            cmachc = param.Params.CURRENT_MAX_AC_CHARGING_CURRENT
            print(f"\t{cmachc.get_name()}: {decoded_values[13].lstrip('0')} {cmachc.get_unit()}", flush=True)
            blynk_write(cmachc.get_pin_set_value(), decoded_values[13])

            cmchc = param.Params.CURRENT_MAX_CHARGING_CURRENT
            print(f"\t{cmchc.get_name()}: {decoded_values[14].lstrip('0')} {cmchc.get_unit()}", flush=True)
            blynk_write(cmchc.get_pin_set_value(), decoded_values[14])
                
            ivr = param.Params.INPUT_VOLTAGE_RANGE
            value = decoded_values[15]
            value_str = {"0": "Appliance", "1": "UPS"}.get(value, "Unknown")
            print(f"\t{ivr.get_name()}: {value_str}", flush=True)
            blynk_write(ivr.get_pin_set_value(), decoded_values[15])
                
            osp = param.Params.OUTPUT_SOURCE_PRIORITY
            value = decoded_values[16]
            value_str = {"0": "Utility First", "1": "Solar First", "2": "SBU priority"}.get(value, "Unknown")
            print(f"\t{osp.get_name()}: {value_str}", flush=True)
            blynk_write(osp.get_pin_set_value(), decoded_values[16])
            
            chsp = param.Params.CHARGER_SOURCE_PRIORITY
            value = decoded_values[17]
            value_str = {"0": "Solar First", "1": "Solar and Utility", "2": "Solar Only"}.get(value, "Unknown")
            print(f"\t{chsp.get_name()}: {value_str}", flush=True)
            blynk_write(chsp.get_pin_set_value(), decoded_values[17])
            
            brdv = param.Params.BATTERY_RE_DISCHARGE_VOLTAGE
            print(f"\t{brdv.get_name()}: {float(decoded_values[22])} {brdv.get_unit()}", flush=True)
            blynk_write(brdv.get_pin_set_value(), float(decoded_values[22]))
            
            response2 = gp.run_command_get(b'QDI')
            
            if response2 is None:
                print(f"\t⚠️ Chyba: Neprišla žiadna odpoveď na príkaz QDI.", flush=True)
                return
            values2 = response2.strip().split()
            decoded_values2 = [value2.decode('latin-1').lstrip("b'(").rstrip("'") for value2 in values2]
            aov = param.Params.AC_OUTPUT_VOLTAGE
            print(f"\t{aov.get_name()}: {decoded_values2[0]} {aov.get_unit()}", flush=True)
            blynk_write(aov.get_pin_set_value(), decoded_values2[0])
            
            aof = param.Params.AC_OUTPUT_FREQUENCY
            print(f"\t{aof.get_name()}: {decoded_values2[1]} {aof.get_unit()}", flush=True)
            blynk_write(aof.get_pin_set_value(), decoded_values2[1])
            
        except Exception as e:
            print(f"\tChyba pri spracovaní QPIRI: {e}", flush=True)
    except Exception as e:
        print(f"\tChyba pri QPIRI: {e}", flush=True)

def aktualneData():
    pv_input_power = 0.0
    pv2_input_power = 0.0
    battery_power = 0.0
    ac_output_power = 0.0
    battery_capacity = 0.0
    pv_voltage = 0.0
    pv2_voltage = 0.0
    inverter_temp = 0.0

    print(" -> Aktuálne dáta:", flush=True)
    try:
        response = gp.run_command_get(b'QPIGS')
        if response is None:
            print(f"\t⚠️ Chyba: Neprišla žiadna odpoveď na príkaz QPIGS.", flush=True)
            save_to_db(pv_input_power, pv2_input_power, battery_power, ac_output_power, 
                       battery_capacity, pv_voltage, pv2_voltage, inverter_temp)
            return
        
        try:
            values = response.strip().split()
            decoded_values = [value.decode('latin-1').lstrip("b'(").rstrip("'") for value in values]
            if len(decoded_values) < 16:
                print(f"\tChyba: Neúplná odpoveď QPIGS, počet hodnôt: {len(decoded_values)}", flush=True)
                save_to_db(pv_input_power, pv2_input_power, battery_power, ac_output_power, 
                           battery_capacity, pv_voltage, pv2_voltage, inverter_temp)
                return
            
            grid_rating_voltage = decoded_values[0]
            grv = param.Params.GRID_RATING_VOLTAGE
            blynk_write(grv.get_pin_actual_value(), grid_rating_voltage)
            print(f"\t{grv.get_name()}: {grid_rating_voltage} {grv.get_unit()}", flush=True)

            grid_frequency = decoded_values[1]
            grf = param.Params.GRID_RATING_FREQUENCY
            blynk_write(grf.get_pin_actual_value(), grid_frequency)
            print(f"\t{grf.get_name()}: {grid_frequency} {grf.get_unit()}", flush=True)

            ac_output_voltage = decoded_values[2]
            aov = param.Params.AC_OUTPUT_VOLTAGE
            blynk_write(aov.get_pin_actual_value(), ac_output_voltage)
            print(f"\t{aov.get_name()}: {ac_output_voltage} {aov.get_unit()}", flush=True)

            ac_output_frequency = decoded_values[3]
            aof = param.Params.AC_OUTPUT_FREQUENCY
            blynk_write(aof.get_pin_actual_value(), ac_output_frequency)
            print(f"\t{aof.get_name()}: {ac_output_frequency} {aof.get_unit()}", flush=True)

            ac_output_apparent_power = decoded_values[4].lstrip("0")
            aoap = param.Params.AC_OUTPUT_APPARENT_POWER
            blynk_write(aoap.get_pin_actual_value(), ac_output_apparent_power)
            print(f"\t{aoap.get_name()}: {ac_output_apparent_power} {aoap.get_unit()}", flush=True)

            ac_output_power = decoded_values[5].lstrip("0")
            aoacp = param.Params.AC_OUTPUT_ACTIVE_POWER
            blynk_write(aoacp.get_pin_actual_value(), ac_output_power)
            print(f"\t{aoacp.get_name()}: {ac_output_power} {aoacp.get_unit()}", flush=True)

            output_load_percent = decoded_values[6].lstrip("0")
            olp = param.Params.OUTPUT_LOAD_PERCENT
            blynk_write(olp.get_pin_actual_value(), output_load_percent)
            print(f"\t{olp.get_name()}: {output_load_percent} {olp.get_unit()}", flush=True)

            bus_voltage = decoded_values[7]
            bv = param.Params.BUS_VOLTAGE
            blynk_write(bv.get_pin_actual_value(), bus_voltage)
            print(f"\t{bv.get_name()}: {bus_voltage} {bv.get_unit()}", flush=True)

            ### hodnoty baterie z meniča, zatiel len dekodovanie, neposielaniedo blynk ..
            battery_capacity = decoded_values[10].lstrip("0")
            bc = param.Params.BATTERY_CAPACITY
            
            battery_voltage = decoded_values[8]
            bvo = param.Params.BATTERY_VOLTAGE

            battery_charging_current = decoded_values[9]
            battery_discharge_current = decoded_values[15]
            bchc = param.Params.BATTERY_CURRENT
            if float(battery_discharge_current) == 0:
                battery_current = float(battery_charging_current)
            else:
                battery_current = float(battery_discharge_current) * -1


            try:
                typ_baterie = blynk_read("v5")
            except Exception as e:
                print(f"\tChyba pri čítaní z Blynku (typ_baterie): {e}", flush=True)
                
                typ_baterie = "0"
            if typ_baterie == "1":    
                try:
                    print(f"\tJIKONG JK BMS - VYPIS HODNOT BATERIE", flush=True)
                    bms_data = BMS.readBMS()
                    battery_capacity = bms_data.get('capacity', 0.0)
                    battery_voltage = bms_data.get('voltage', 0.0)
                    battery_current = bms_data.get('current', 0.0)
                    print(f"\tZostávajúca kapacita (BMS): {battery_capacity} %", flush=True)
                    blynk_write(param.Params.BATTERY_CAPACITY.get_pin_actual_value(), battery_capacity)
                    blynk_write(param.Params.BATTERY_VOLTAGE.get_pin_actual_value(), battery_voltage)
                    blynk_write(param.Params.BATTERY_CURRENT.get_pin_actual_value(), battery_current)
                    
                except Exception as e:
                    print(f"\tChyba pri čítaní BMS: {e}", flush=True)
                    print(f"\tINVERTER - VYPIS HODNOT BATERIE - PORUCHA BMS", flush=True)
            else:
                print(f"\tINVERTER - VYPIS HODNOT BATERIE", flush=True)
                blynk_write(bc.get_pin_actual_value(), battery_capacity)
                print(f"\t{bc.get_name()}: {battery_capacity} {bc.get_unit()}", flush=True)
                blynk_write(bvo.get_pin_actual_value(), battery_voltage)
                print(f"\t{bvo.get_name()}: {battery_voltage} {bvo.get_unit()}", flush=True)
                blynk_write(bchc.get_pin_actual_value(), battery_current)
                print(f"\t{bchc.get_name()}: {battery_current} {bchc.get_unit()}", flush=True)


            try:
                battery_power = float(battery_voltage) * float(battery_current)
                bp = param.Params.BATTERY_POWER
                blynk_write(bp.get_pin_actual_value(), round(battery_power))
                print(f"\t{bp.get_name()}: {round(battery_power)} {bp.get_unit()}", flush=True)
            except Exception as e:
                print(f"\tChyba pri výpočte BATTERY_POWER: {e}", flush=True)
                battery_power = 0.0

            inverter_temp = decoded_values[11].lstrip("0")
            ihst = param.Params.INVERTER_HEAT_SINK_TEMPERATURE
            blynk_write(ihst.get_pin_actual_value(), inverter_temp)
            print(f"\t{ihst.get_name()}: {inverter_temp} {ihst.get_unit()}", flush=True)
                

            pv_input_current_battery = decoded_values[12]
            pvcb = param.Params.PV_INPUT_CURRENT_BATTERY
            blynk_write(pvcb.get_pin_actual_value(), pv_input_current_battery)
            print(f"\t{pvcb.get_name()}: {pv_input_current_battery} {pvcb.get_unit()}", flush=True)

            pv_voltage = decoded_values[13]
            piv = param.Params.PV_INPUT_VOLTAGE
            blynk_write(piv.get_pin_actual_value(), pv_voltage)
            print(f"\t{piv.get_name()}: {pv_voltage} {piv.get_unit()}", flush=True)

            battery_voltage_scc = decoded_values[14]
            bvs = param.Params.BATTERY_VOLTAGE_SCC
            blynk_write(bvs.get_pin_actual_value(), battery_voltage_scc)
            print(f"\t{bvs.get_name()}: {battery_voltage_scc} {bvs.get_unit()}", flush=True)

            pv_input_power = float(pv_voltage) * float(pv_input_current_battery)
            pip = param.Params.PV_INPUT_POWER
            blynk_write(pip.get_pin_actual_value(), round(pv_input_power))
            print(f"\t{pip.get_name()}: {round(pv_input_power)} {pip.get_unit()}", flush=True)
            
        except Exception as e:
            print(f"\tChyba pri spracovaní QPIGS: {e}", flush=True)
    except Exception as e:
        print(f"\tChyba pri QPIGS: {e}", flush=True)
        try:
            gp.closePort()
            time.sleep(3)
            gp.initializePort()
        except Exception as e2:
            print(f"\tChyba pri reinicializácii portu: {e2}", flush=True)
    save_to_db(pv_input_power, pv2_input_power, battery_power, ac_output_power, 
               battery_capacity, pv_voltage, pv2_voltage, inverter_temp)

def upozornenia():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] -> Upozornenia:", flush=True)
    try:
        response = gp.run_command_get(b'QPIWS')
        if response is None:
            print(f"\t⚠️ Chyba: Neprišla žiadna odpoveď na príkaz QPIWS.", flush=True)
            return
        try:
            detected_warnings = []
            for i, bit in enumerate(response):
                if bit == '1':
                    warning_code = i + 1
                    warning_message = warn.WarningMessages(warning_code).value
                    detected_warnings.append(warning_message)
            print(f"\t{detected_warnings}", flush=True)
        except Exception as e:
            print(f"\tChyba pri spracovaní QPIWS: {e}", flush=True)
    except Exception as e:
        print(f"\tChyba pri QPIWS: {e}", flush=True)

# Inicializácia databázy
init_db()