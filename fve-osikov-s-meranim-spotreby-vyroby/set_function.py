# Python3 script to interface basic Blynk rest API with Raspberry PI
import time

#import BlynkLib # pip3 install blynk-library-python ## Pre blynk zapisovanie
import globals as gp
import get_function as get
import flagEnum as flag

from blynkSender import blynk_write, blynk_set_property, blynk_read, blynk_read_float
###################################################################################

def nastavene_hodnoty_update():

    get.nastaveneData()
    time.sleep(0.1)
    blynk_write(2, 0)

def skontroluj_posuvace():

    button_pin = 99

    for option in flag.Option:
        flag_name = option.get_name()
        flag_pin = option.get_pin()
        float_code = (option.get_code()).lower()

        if flag_name in gp.flags_enabled:
            flag_pin_str = "v"+str(flag_pin)
            if (blynk_read(flag_pin_str) == '0'):
                print("-> Nastavujem ", flag_name)
                blynk_write(flag_pin, 0)
                evaluate_response(gp.run_command_set(b'PD', float_code), button_pin)
                time.sleep(0.2)
            else:
                pass

        if flag_name in gp.flags_disabled:
            flag_pin_str = "v"+str(flag_pin)
            if (blynk_read(flag_pin_str) == '1'):
                print("-> Nastavujem ", flag_name)
                blynk_write(flag_pin, 1)
                evaluate_response(gp.run_command_set(b'PE', float_code), button_pin)
                time.sleep(0.2)
            else:
                pass

    blynk_write(button_pin, 2)
    blynk_set_property

    blynk_write(0, 0)

def zmen_nastavenia():

    button_pin = 97
    response = gp.run_command_get(b'QPIRI')
    time.sleep(0.2)

    values = response.strip().split()
    decoded_set_values = [value.decode('latin-1').lstrip("b'(").rstrip("'") for value in values]


    # nastav
    back_to_charge_voltage_value = float(blynk_read_float("v86"))
    # 44V/45V/46V/47V/48V/49V/50V/51V
    if (float(decoded_set_values[8]) != back_to_charge_voltage_value):
        print("-> Nastavujem BACK TO CHARGE VOLTAGE")
        evaluate_response(gp.run_command_set(b'PBCV', str(back_to_charge_voltage_value)), button_pin)
        time.sleep(0.2)

    battery_cut_off_voltage_value = float(blynk_read_float("v87"))
    # 40.0V ~ 48.0V for 48V unit
    if (float(decoded_set_values[9]) != battery_cut_off_voltage_value):
        print("-> Nastavujem BATTERY CUT OFF VOLTAGE")
        evaluate_response(gp.run_command_set(b'PSDV', str(battery_cut_off_voltage_value)), button_pin)
        time.sleep(0.2)

    bulk_charging_voltage_value = float(blynk_read_float("v88"))
    # 48.0V ~ 58.4V for 48V unit
    if (float(decoded_set_values[10]) != bulk_charging_voltage_value):
        print("-> Nastavujem BULK CHARGING VOLTAGE")
        evaluate_response(gp.run_command_set(b'PCVV', str(bulk_charging_voltage_value)), button_pin)
        time.sleep(0.2)

    float_charging_voltage_value = float(blynk_read_float("v89"))
    # 48.0V ~ 58.4V for 48V unit
    if (float(decoded_set_values[11]) != float_charging_voltage_value):
        print("-> Nastavujem FLOAT CHARGING VOLTAGE")
        evaluate_response(gp.run_command_set(b'PBFT', str(float_charging_voltage_value)), button_pin)
        time.sleep(0.2)

    battery_type_value = int(blynk_read("v90"))
    # 00 for AGM, 01 for Flooded battery, 02 for User
    if (int(decoded_set_values[12]) != battery_type_value):
        print("-> Nastavujem BATTERY TYPE VOLTAGE")
        evaluate_response(gp.run_command_set(b'PBT', '0' + str(battery_type_value)), button_pin)
        time.sleep(0.2)

    current_max_ac_charging_current_value = int(blynk_read("v91"))
    # 00 ~ 99
    if (int(decoded_set_values[13]) != current_max_ac_charging_current_value):
        print("-> Nastavujem CURRENT MAX AC CHARGING CURRENT VOLTAGE")
        value = '';
        if(current_max_ac_charging_current_value <=9):
            value = '00' + str(current_max_ac_charging_current_value)
        else:
            value = '0'+str(current_max_ac_charging_current_value)
        evaluate_response(gp.run_command_set(b'MUCHGC', value), button_pin)
        time.sleep(0.2)

    current_max_charging_current_value = int(blynk_read("v92"))
    # 010 ~ 090
    if (int(decoded_set_values[14]) != current_max_charging_current_value):
        print("-> Nastavujem CURRENT MAX CHARGING CURRENT VOLTAGE")
        evaluate_response(gp.run_command_set(b'MNCHGC', '0' + str(current_max_charging_current_value)), button_pin)
        time.sleep(0.2)

    input_voltage_range_value = int(blynk_read("v93"))
    # 00 for appliance, 01 for UPS
    if (int(decoded_set_values[15]) != input_voltage_range_value):
        print("-> Nastavujem INPUT VOLTAGE RANGE")
        evaluate_response(gp.run_command_set(b'PGR', '0'+str(input_voltage_range_value)), button_pin)
        time.sleep(0.2)

    output_source_priority_value = int(blynk_read("v94"))
    # 00 for utility first, 01 for solar first, 02 for SBU priority
    if (int(decoded_set_values[16]) != output_source_priority_value):
        print("-> Nastavujem OUTPUT SOURCE PRIORITY VALUE")

        if(output_source_priority_value == 2):
            evaluate_response(gp.run_command_set_POP02(), button_pin)
            time.sleep(0.2)

        else:
            evaluate_response(gp.run_command_set(b'POP0', str(output_source_priority_value)), button_pin)
            time.sleep(0.2)

    charger_source_priority_value = int(blynk_read("v95"))
    # 00 for utility first, 01 for solar first, 03 for only solar charging
    if (int(decoded_set_values[17]) != charger_source_priority_value):
        print("-> Nastavujem CHARGER SOURCE PRIORITY")
        evaluate_response(gp.run_command_set(b'PCP', '0'+str(charger_source_priority_value)), button_pin)
        time.sleep(0.2)

    battery_redischarge_voltage_value = float(blynk_read_float("v96"))
    # 00.0V 48V/49V/50V/51V/52V/53V/54V/55V/56V/57V/58V
    if (float(decoded_set_values[22]) != battery_redischarge_voltage_value):
        print("-> Nastavujem BATTERY RE-DISCHARGE VOLTAGE")
        evaluate_response(gp.run_command_set(b'PBDV', str(battery_redischarge_voltage_value)), button_pin)
        time.sleep(0.2)

    response2 = gp.run_command_get(b'QDI')
    values2 = response2.strip().split()
    decoded_set_values2 = [value2.decode('latin-1').lstrip("b'(").rstrip("'") for value2 in values2]

    ac_output_frequency_value = float(blynk_read_float("v98"))
    # 50Hz.or 60Hz
    if (float(decoded_set_values2[1]) != ac_output_frequency_value):
        print("-> Nastavujem AC OUTPUT FREQUENCY")
        evaluate_response(gp.run_command_set(b'F', str(ac_output_frequency_value)), button_pin)
        time.sleep(0.2)

    blynk_write(button_pin, 2)
    blynk_set_property(button_pin, "color", "#000000")

def evaluate_response(response, button_pin):
    if b'ACK' in response:
        print("\tNastavenie prebehlo úspešne :)")
        blynk_write(button_pin, 1)
        blynk_set_property(button_pin, "color", "#86B953")

    else:
        blynk_write(button_pin, 0)
        blynk_set_property(button_pin, "color", "#D03A20")
        print("\tNastavenie zlyhalo :(")

    time.sleep(0.2)

