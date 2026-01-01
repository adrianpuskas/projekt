# Python3 script to interface basic Blynk rest API with Raspberry PI

import globals as gp
import parametersEnum as param
import deviceModeEnum as modes
import warningsEnum as warn
import flagEnum as flags
import JKBMS as BMS
#from TUV_WATCHDOG_TEST_TUV import log
#import json
import time
from blynkSender import blynk_write, blynk_read
   
    

def flags_enabled():
    response = gp.run_command_get(b'QFLAG')
    
    if response is None or b"NAKss" in response:
        print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QFLAG.")
        while response is None or b"NAKss" in response:
            print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QFLAG.")
            time.sleep(0.5)
            response = gp.run_command_get(b'QFLAG')
    else:

        substring_start = response.index(b'(E') + 1
        substring_end = response.index(b'd') + 1

        substring = response[substring_start:substring_end].decode('latin-1')  # Extracting and decoding the substring

        position_e = substring.index('E')
        position_d = substring.index('D')
        substring_e = substring[position_e + 1:position_d]

        for char in substring_e:
            try:
                flag = next(option for option in flags.Option if option.get_code() == char.upper())
                gp.flags_enabled.append(flag.get_name())
            except StopIteration:
                pass


def flags_disbled():
    response = gp.run_command_get(b'QFLAG')
    
    if response is None or b"NAKss" in response:
        print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QFLAG.")
        while response is None or b"NAKss" in response:
            print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QFLAG.")
            time.sleep(0.5)
            response = gp.run_command_get(b'QFLAG')
    else:

        substring_start = response.index(b'(E') + 1
        substring_end = response.index(b'd') + 1

        substring = response[substring_start:substring_end].decode('latin-1')  # Extracting and decoding the substring

        position_d = substring.index('D')
        substring_d = substring[position_d + 1:]

        for char in substring_d:
            try:
                flag = next(option for option in flags.Option if option.get_code() == char.upper())
                gp.flags_disabled.append(flag.get_name())
            except StopIteration:
                pass


###################################################################################
### QFLAG ###
def nastavenia_menica():
    flags_enabled()
    flags_disbled()

    print("-> Flags ENABLED: ", gp.flags_enabled)
    print("-> Flags DISABLED: ", gp.flags_disabled)


###################################################################################
### QVFW ###
def FW_version():
    response = gp.run_command_get(b'QVFW')
    
    if response is None or b"NAKss" in response:
        print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QVFW.")
        while response is None or b"NAKss" in response:
            print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QVFW.")
            time.sleep(0.5)
            response = gp.run_command_get(b'QVFW')
    else:
        version = response[1]
        print("-> FW verzia:", version)


def mode_zariadenia():
    response = gp.run_command_get(b'QMOD')
    
    if response is None or b"NAKss" in response:
        print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QMOD.")
        while response is None or b"NAKss" in response:
            print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QMOD.")
            time.sleep(0.5)
            response = gp.run_command_get(b'QMOD')
    else:
        print("-> Mode zariadenia: ")

        first_character = response[1:2].decode('latin-1')
        mode = None
        for device_mode in modes.DeviceMode:
            if device_mode.get_char() == first_character:
                mode = device_mode
                break
        if mode:
            blynk_write(1, mode.name)
            print("\t", mode.name)
        else:
            print("\tInvalid device mode:", first_character)

        gp.ser.close()


###################################################################################
### QPIRI + QDI ###
def nastaveneData():
    response = gp.run_command_get(b'QPIRI')
    
    if response is None or b"NAKss" in response:
        print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QPIRI.")
        while response is None or b"NAKss" in response:
            print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QPIRI.")
            time.sleep(0.5)
            response = gp.run_command_get(b'QPIRI')
    else:
        print("-> Nastavené dáta:")

        values = response.strip().split()
        decoded_values = [value.decode('latin-1').lstrip("b'(").rstrip("'") for value in values]

        brv = param.Params.BATTERY_RECHARGE_VOLTAGE
        print("\t", brv.get_name(), ":", decoded_values[8], brv.get_unit())
        blynk_write(brv.get_pin_set_value(), decoded_values[8])

        buv = param.Params.BATTERY_UNDER_VOLTAGE
        print("\t", buv.get_name(), ":", decoded_values[9], buv.get_unit())
        blynk_write(buv.get_pin_set_value(), decoded_values[9])

        bbv = param.Params.BATTERY_BULK_VOLTAGE
        print("\t", bbv.get_name(), ":", decoded_values[10], bbv.get_unit())
        blynk_write(bbv.get_pin_set_value(), decoded_values[10])

        bfv = param.Params.BATTERY_FLOAT_VOLTAGE
        print("\t", bfv.get_name(), ":", decoded_values[11], bfv.get_unit())
        blynk_write(bfv.get_pin_set_value(), decoded_values[11])

        bt = param.Params.BATTERY_TYPE
        value = decoded_values[12]
        value_str = ""
        if (value == '0'):
            value_str = "AGM"
        elif (value == '1'):
            value_str = "Flooded Battery"
        elif (value == '2'):
            value_str = "User"
        print("\t", bt.get_name(), ":", value_str)
        blynk_write(bt.get_pin_set_value(), decoded_values[12])

        cmachc = param.Params.CURRENT_MAX_AC_CHARGING_CURRENT
        print("\t", cmachc.get_name(), ":", decoded_values[13].lstrip("0"), cmachc.get_unit())
        blynk_write(cmachc.get_pin_set_value(), decoded_values[13])

        cmchc = param.Params.CURRENT_MAX_CHARGING_CURRENT
        print("\t", cmchc.get_name(), ":", decoded_values[14].lstrip("0"), cmchc.get_unit())
        blynk_write(cmchc.get_pin_set_value(), decoded_values[14])

        ivr = param.Params.INPUT_VOLTAGE_RANGE
        value = decoded_values[15]
        value_str = ""
        if (value == '0'):
            value_str = "Appliance"
        elif (value == '1'):
            value_str = "UPS"
        print("\t", ivr.get_name(), ":", value_str)
        blynk_write(ivr.get_pin_set_value(), decoded_values[15])

        osp = param.Params.OUTPUT_SOURCE_PRIORITY
        value = decoded_values[16]
        value_str = ""
        if (value == '0'):
            value_str = "Utility First"
        elif (value == '1'):
            value_str = "Solar First"
        elif (value == '2'):
            value_str = "SBU priority"
        print("\t", osp.get_name(), ":", value_str)
        blynk_write(osp.get_pin_set_value(), decoded_values[16])
        #blynk_write(6, decoded_values[16])

        chsp = param.Params.CHARGER_SOURCE_PRIORITY
        value = decoded_values[17]
        value_str = ""
        if (value == '0'):
            value_str = "Solar First"
        elif (value == '1'):
            value_str = "Solar nad Utility"
        elif (value == '2'):
            value_str = "Solar Only"
        print("\t", chsp.get_name(), ":", value_str)
        blynk_write(chsp.get_pin_set_value(), decoded_values[17])

        brdv = param.Params.BATTERY_RE_DISCHARGE_VOLTAGE
        print("\t", brdv.get_name(), ":", float(decoded_values[22]), brdv.get_unit())
        blynk_write(brdv.get_pin_set_value(), float(decoded_values[22]))


        response2 = gp.run_command_get(b'QDI')
        if response2 is None or b"NAKss" in response2:
            print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QDI.")
            while response2 is None or b"NAKss" in response2:
                print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QDI.")
                time.sleep(0.5)
                response2 = gp.run_command_get(b'QDI')
            else:
                values2 = response2.strip().split()
                decoded_values2 = [value2.decode('latin-1').lstrip("b'(").rstrip("'") for value2 in values2]
                aov = param.Params.AC_OUTPUT_VOLTAGE
                print("\t", aov.get_name(), ":", decoded_values2[0], aov.get_unit())
                blynk_write(aov.get_pin_set_value(), decoded_values2[0])

                aof = param.Params.AC_OUTPUT_FREQUENCY
                print("\t", aof.get_name(), ":", decoded_values2[1], aof.get_unit())
                blynk_write(aof.get_pin_set_value(), decoded_values2[1])


###################################################################################
### QPIGS ###
def aktualneData():
    response = gp.run_command_get(b'QPIGS')
    
    if response is None or b"NAKss" in response:
        print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QPIGS.")
        while response is None or b"NAKss" in response:
            print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QPIGS.")
            time.sleep(0.5)
            response = gp.run_command_get(b'QPIGS')
    else:
            
        print("-> Aktuálne dáta:")
        values = response.strip().split()
        decoded_values = [value.decode('latin-1').lstrip("b'(").rstrip("'") for value in values]
        #print (decoded_values)
        grid_rating_voltage = decoded_values[0]
        grv = param.Params.GRID_RATING_VOLTAGE
        blynk_write(grv.get_pin_actual_value(), grid_rating_voltage)
        print("\t", grv.get_name(), ":", grid_rating_voltage, grv.get_unit())

        grid_frequency = decoded_values[1]
        grf = param.Params.GRID_RATING_FREQUENCY
        blynk_write(grf.get_pin_actual_value(), grid_frequency)
        print("\t", grf.get_name(), ":", grid_frequency, grf.get_unit())

        ac_output_voltage = decoded_values[2]
        aov = param.Params.AC_OUTPUT_VOLTAGE
        blynk_write(aov.get_pin_actual_value(), ac_output_voltage)
        print("\t", aov.get_name(), ":", ac_output_voltage, aov.get_unit())

        ac_output_frequency = decoded_values[3]
        aof = param.Params.AC_OUTPUT_FREQUENCY
        blynk_write(aof.get_pin_actual_value(), ac_output_frequency)
        print("\t", aof.get_name(), ":", ac_output_frequency, aof.get_unit())

        ac_output_apparent_power = decoded_values[4].lstrip("0")
        aoap = param.Params.AC_OUTPUT_APPARENT_POWER
        blynk_write(aoap.get_pin_actual_value(), ac_output_apparent_power)
        print("\t", aoap.get_name(), ":", ac_output_apparent_power, aoap.get_unit())

        ### CSV
        ac_output_active_power = decoded_values[5].lstrip("0")
        aoacp = param.Params.AC_OUTPUT_ACTIVE_POWER
        blynk_write(aoacp.get_pin_actual_value(), ac_output_active_power)
        print("\t", aoacp.get_name(), ":", ac_output_active_power, aoacp.get_unit())

        output_load_percent = decoded_values[6].lstrip("0")
        olp = param.Params.OUTPUT_LOAD_PERCENT
        blynk_write(olp.get_pin_actual_value(), output_load_percent)
        print("\t", olp.get_name(), ":", output_load_percent, olp.get_unit())

        bus_voltage = decoded_values[7]
        bv = param.Params.BUS_VOLTAGE
        blynk_write(bv.get_pin_actual_value(), bus_voltage)
        print("\t", bv.get_name(), ":", bus_voltage, bv.get_unit())


        battery_voltage = decoded_values[8]
        bvo = param.Params.BATTERY_VOLTAGE
        blynk_write(bvo.get_pin_actual_value(), battery_voltage)
        print("\t", bvo.get_name(), ":", battery_voltage, bvo.get_unit())

        battery_charging_current = decoded_values[9]
        battery_discharge_current = decoded_values[15]

        bchc = param.Params.BATTERY_CURRENT

        if float(battery_discharge_current) == 0:
            battery_current = float(battery_charging_current)
            blynk_write(bchc.get_pin_actual_value(), battery_current)
        else:
            battery_discharge_current = float(battery_discharge_current) * -1
            battery_current = battery_discharge_current
            blynk_write(bchc.get_pin_actual_value(), battery_current)

        print("\t", bchc.get_name(), ":", battery_current, bchc.get_unit())


        #try:
        typ_baterie = blynk_read("v5")
        if typ_baterie == ("1"):    
            BMS.readBMS()
            print('JIKONG JK BMS - VYPIS HODNOT BATERIE')
        
        else: ## ak je typ_baterie 0
            print('INVERTER - VYPIS HODNOT BATERIE')
            battery_capacity = decoded_values[10].lstrip("0")
            bc = param.Params.BATTERY_CAPACITY
            blynk_write(bc.get_pin_actual_value(), battery_capacity)
            print("\t", bc.get_name(), ":", battery_capacity, bc.get_unit())
        
        battery_power = float(battery_voltage) * battery_current
        bp = param.Params.BATTERY_POWER
        blynk_write(bp.get_pin_actual_value(), round(battery_power))
        print("\t", bp.get_name(), ":", round(battery_power), bp.get_unit())

        inverter_heat_sink_temperature = decoded_values[11].lstrip("0")
        ihst = param.Params.INVERTER_HEAT_SINK_TEMPERATURE
        blynk_write(ihst.get_pin_actual_value(), inverter_heat_sink_temperature)
        print("\t", ihst.get_name(), ":", inverter_heat_sink_temperature, ihst.get_unit())

        pv_input_current_battery = decoded_values[12]
        pvcb = param.Params.PV_INPUT_CURRENT_BATTERY
        blynk_write(pvcb.get_pin_actual_value(), pv_input_current_battery)
        print("\t", pvcb.get_name(), ":", pv_input_current_battery, pvcb.get_unit())

        pv_input_voltage_1 = decoded_values[13]
        piv = param.Params.PV_INPUT_VOLTAGE
        blynk_write(piv.get_pin_actual_value(), pv_input_voltage_1)
        print("\t", piv.get_name(), ":", pv_input_voltage_1, piv.get_unit())

        battery_voltage_scc = decoded_values[14]
        bvs = param.Params.BATTERY_VOLTAGE_SCC
        blynk_write(bvs.get_pin_actual_value(), battery_voltage_scc)
        print("\t", bvs.get_name(), ":", battery_voltage_scc, bvs.get_unit())

        ### CSV
        pv_input_power = float(pv_input_voltage_1) * float(pv_input_current_battery)
        pip = param.Params.PV_INPUT_POWER
        blynk_write(pip.get_pin_actual_value(), pv_input_power)
        # gp.write_current_values("pv_input_power", pv_input_power)
        print("\t", pip.get_name(), ":", round(pv_input_power), pip.get_unit())
        
        """
        # Na konci funkcie aktualneData()
        shared_data = {
        "battery_power": round(battery_power),
        "pv_input_power": round(pv_input_power),
        "output_load_power": int(ac_output_active_power),
        "battery_capacity": int(battery_capacity) if typ_baterie != "1" else 0,
        "pv_voltage": float(pv_input_voltage_1),
        "inverter_temp": int(inverter_heat_sink_temperature),
        # prípadne aj ďalšie ktoré potrebuješ
        }
        
        with open("zdielane_data_pre_TUV.json", "w") as f:
            json.dump(shared_data, f)
        
        ### PRE 2 STRINGOVE MENICE
                  
        response2 = gp.run_command_get(b'QPIGS2')
        print (response2)
        if (response2 is None or len(response2) <= 7):
            print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QPIGS2.")
            while (response2 is None or b"NAKss" in response2):
                print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QPIGS2.")
                time.sleep(0.5)
                response2 = gp.run_command_get(b'QPIGS2')
        else:
            print("-> PV2 DATA:")

            values2 = response2.strip().split()
            decoded_values2 = [value.decode('latin-1').lstrip("b'(").rstrip("'") for value in values2]
            print (decoded_values2)
            pv2_input_current_battery = decoded_values2[12]
            pvcb = param.Params.PV2_INPUT_CURRENT_BATTERY
            blynk_write(pvcb.get_pin_actual_value(), pv2_input_current_battery)
            print("\t", pvcb.get_name(), ":", pv2_input_current_battery, pvcb.get_unit())
                
            
            pv2_input_voltage_1 = decoded_values2[13]
            piv = param.Params.PV_INPUT_VOLTAGE
            blynk_write(piv.get_pin_actual_value(), pv_input_voltage_1)
            print("\t", piv.get_name(), ":", pv_input_voltage_1, piv.get_unit())
            
            ### CSV
            pv2_input_power = float(pv2_input_voltage_1) * float(pv2_input_current_battery)
            pip = param.Params.PV_INPUT_POWER
            blynk_write(pip.get_pin_actual_value(), pv2_input_power)
            print("\t", pip.get_name(), ":", round(pv2_input_power), pip.get_unit())
        """                
        

###################################################################################
### QPIWS ###
def upozornenia():
    response = gp.run_command_get(b'QPIWS')
    
    if response is None or b"NAKss" in response:
        print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QPIWS.")
        while response is None or b"NAKss" in response:
            print("⚠️  Chyba: Neprišla žiadna odpoveď na príkaz QPIWS.")
            time.sleep(0.5)
            response = gp.run_command_get(b'QPIWS')
    else:
        print("-> Upozornenia: ")

        detected_warnings = []
        for i, bit in enumerate(response):
            if bit == '1':
                warning_code = i + 1
                warning_message = warn.WarningMessages(warning_code).value
                detected_warnings.append(warning_message)

        print("\t", detected_warnings)

