import time
import datetime
import sys
import struct
import serial
from serial.tools import list_ports
import parametersEnum as param
import globals as gp
from blynkSender import blynk_write

def find_bms_port(vid, pid):
    ports = list_ports.comports()
    for port in ports:
        if port.vid == vid and port.pid == pid:
            return port.device
    return None


# VID a PID pre JKBMS (cinsky modry prevodnik)
VID = 6790
PID = 29987

bms_port = find_bms_port(VID, PID)

if bms_port is None:
    print("BMS zariadenie nebolo nájdené.")
    # sys.exit(1)

try:
    bms = serial.Serial(bms_port, baudrate=115200, timeout=0.2)
    print("BMS pripojená na port: ", bms_port)
except Exception as e:
    print(f"Nepodarilo sa otvoriť sériový port: {e}")
    # sys.exit(1)


def sendBMSCommand(cmd_string):
    cmd_bytes = bytearray.fromhex(cmd_string)
    bms.write(cmd_bytes)


def readBMS():
    try:
        sendBMSCommand('4E 57 00 13 00 00 00 00 06 03 00 00 00 00 00 00 68 00 00 01 29')
        print("Posielam požiadavku")
        time.sleep(0.1)

        if bms.in_waiting >= 4:
            if bms.read(1).hex() == '4e':  # header byte 1
                if bms.read(1).hex() == '57':  # header byte 2
                    length = int.from_bytes(bms.read(2), byteorder='big') - 2
                    available = bms.in_waiting
                    if available != length:
                        time.sleep(0.1)
                        available = bms.in_waiting
                        if available != length:
                            bms.reset_input_buffer()
                            raise Exception("Chyba pri čítaní dát...")
                            raise ValueError('Žiadne údaje z BMS')

                    b = bytearray.fromhex("4e57")
                    b += (length + 2).to_bytes(2, byteorder='big')
                    data = bytearray(bms.read(available))
                    data = b + data
                    print(len(data), "Dlžka dát")

                    crc_calc = sum(data[0:-4])
                    crc_lo = struct.unpack_from('>H', data[-2:])[0]

                    if crc_calc != crc_lo:
                        bms.reset_input_buffer()
                        raise Exception("Nesprávne CRC")

                    data = data[11:length - 19]
                    bytecount = data[1]
                    cellcount = int(bytecount / 3)
                    
                    #zobrazenie napäti jednotlivych clankov, MIN MAX DELTA U
                    cell_voltages = []

                    # Zber napätí do zoznamu
                    for i in range(cellcount):
                        voltage = struct.unpack_from('>xH', data, i * 3 + 2)[0] / 1000
                        cell_voltages.append(voltage)
                        blynk_write(13, f"Cell {i + 1}: {voltage:.3f} V\t")

                    # Nájdi min, max a delta
                    min_voltage = min(cell_voltages)
                    max_voltage = max(cell_voltages)
                    min_index = cell_voltages.index(min_voltage) + 1  # +1 kvôli číslovaniu od 1
                    max_index = cell_voltages.index(max_voltage) + 1

                    delta_u = max_voltage - min_voltage

                    # Výpis výsledkov
                    blynk_write(13, f"\nMin.: Cell {min_index} = {min_voltage:.3f}V ")
                    blynk_write(13, f"\tMax.: Cell {max_index} = {max_voltage:.3f}V")
                    blynk_write(13, f"\nDelta U: {delta_u:.3f} V")
                    
                    ### pokracovanie

                    temp_fet = struct.unpack_from('>H', data, bytecount + 3)[0]
                    if temp_fet > 100:
                        temp_fet = -(temp_fet - 100)
                    temp_1 = struct.unpack_from('>H', data, bytecount + 6)[0]
                    if temp_1 > 100:
                        temp_1 = -(temp_1 - 100)
                    temp_2 = struct.unpack_from('>H', data, bytecount + 9)[0]
                    if temp_2 > 100:
                        temp_2 = -(temp_2 - 100)

                    print("BMS - ",f"Temp1: {temp_1} °C")
                    print("BMS - ",f"Temp2: {temp_2} °C")

                    voltage = struct.unpack_from('>H', data, bytecount + 12)[0] / 100
                    print("BMS - ",f"Napätie batérie: {voltage} V")


                    unsigned_current = struct.unpack_from('>H', data, bytecount + 15)[0]
                    current = unsigned_current / 100
                    if unsigned_current > 32767:
                        current = (32767 - unsigned_current) / 100
                    current = -current
                    print("BMS - ",f"Prúd: {current} A")

                    capacity = struct.unpack_from('>B', data, bytecount + 18)[0]
                    print("BMS - ",f"Zostávajúca kapacita: {capacity} %")

                    """
                    bvo = param.Params.BATTERY_VOLTAGE
                    blynk.virtual_write(bvo.get_pin_actual_value(), voltage)
                    print("\t", bvo.get_name(), ":", voltage, bvo.get_unit())

                    bchc = param.Params.BATTERY_CURRENT
                    blynk.virtual_write(bchc.get_pin_actual_value(), current)
                    print("\t", bchc.get_name(), ":", current, bchc.get_unit())

                    battery_power = float(voltage) * current
                    bp = param.Params.BATTERY_POWER
                    blynk.virtual_write(bp.get_pin_actual_value(), round(battery_power))
                    print("\t", bp.get_name(), ":", round(battery_power), bp.get_unit())
                    """
                    bc = param.Params.BATTERY_CAPACITY
                    #blynk.virtual_write(bc.get_pin_actual_value(), capacity)
                    blynk_write(70, str(capacity))
                    #print("BMS - ", bc.get_name(), ":", capacity, bc.get_unit())
                    
                    allBmsData = f"""
.......................................
\tUDAJE BMS :
Temp1: {temp_1} °C , Temp2: {temp_2} °C
Napätie batérie: {voltage} V
Prúd: {current} A
Zostávajúca kapacita: {capacity} %
.......................................
\n"""
                    #print (allBmsData)
                    blynk_write(13, allBmsData)
                    blynk_write(13, (datetime.datetime.now().strftime("%H:%M:%S")))
                    blynk_write(13, f"\n")
                    blynk_write(13, f"\n")
                    

        bms.reset_input_buffer()
        # raise ValueError('Žiadne údaje z BMS')
    except Exception as e:
        print(e)
        raise ValueError('Žiadne údaje z BMS')
        readBMS()

# while True:
#  readBMS()
#   time.sleep(1.5)
