import time
import datetime
import sys
import struct
import serial
from serial.tools import list_ports
import parametersEnum as param
import globals as gp
from blynkSender import blynk_write

# Globálna premenná na uchovanie posledných platných údajov
last_bms_data = {'capacity': 0.0, 'voltage': 0.0, 'current': 0.0, 'temp_1': 0, 'temp_2': 0}

def find_bms_port(vid, pid):
    ports = list_ports.comports()
    for port in ports:
        if port.vid == vid and port.pid == pid:
            return port.device
    return None

# VID a PID pre JKBMS (čínsky modrý prevodník)
VID = 6790
PID = 29987

bms_port = find_bms_port(VID, PID)

if bms_port is None:
    print(f" BMS zariadenie nebolo nájdené.")
else:
    try:
        bms = serial.Serial(bms_port, baudrate=115200, timeout=0.3)  # Zvýšený timeout
        print(f" BMS pripojená na port: {bms_port}")
    except Exception as e:
        print(f" Nepodarilo sa otvoriť sériový port: \n\t{e}")

def sendBMSCommand(cmd_string):
    try:
        cmd_bytes = bytearray.fromhex(cmd_string)
        bms.write(cmd_bytes)
    except Exception as e:
        print(f" Chyba pri odosielaní príkazu BMS: \n\t{e}")

def readBMS(max_retries=5):  # počet pokusov pripojenia = 5
    global last_bms_data
    for attempt in range(max_retries):
        try:
            if bms is None or not bms.is_open:
                print(f" BMS port nie je otvorený.")
                return last_bms_data  # Vráti posledné platné údaje

            sendBMSCommand('4E 57 00 13 00 00 00 00 06 03 00 00 00 00 00 00 68 00 00 01 29')
            print(f" Posielam požiadavku")
            time.sleep(0.2)  # Zvýšené časovanie

            if bms.in_waiting >= 4:
                if bms.read(1).hex() == '4e':  # header byte 1
                    if bms.read(1).hex() == '57':  # header byte 2
                        length = int.from_bytes(bms.read(2), byteorder='big') - 2
                        available = bms.in_waiting
                        if available != length:
                            time.sleep(0.2)  # Zvýšené časovanie
                            available = bms.in_waiting
                            if available != length:
                                bms.reset_input_buffer()
                                print(f" Chyba: Nesprávna dĺžka dát ({available}/{length})")
                                continue

                        b = bytearray.fromhex("4e57")
                        b += (length + 2).to_bytes(2, byteorder='big')
                        data = bytearray(bms.read(available))
                        data = b + data
                        print(f" {len(data)} Dlžka dát")

                        crc_calc = sum(data[0:-4])
                        crc_lo = struct.unpack_from('>H', data[-2:])[0]

                        if crc_calc != crc_lo:
                            bms.reset_input_buffer()
                            print(f" Chyba: Nesprávne CRC")
                            continue

                        data = data[11:length - 19]
                        bytecount = data[1]
                        cellcount = int(bytecount / 3)
                        
                        # Zber napätí jednotlivých článkov
                        cell_voltages = []
                        for i in range(cellcount):
                            voltage = struct.unpack_from('>xH', data, i * 3 + 2)[0] / 1000
                            cell_voltages.append(voltage)
                            blynk_write(13, f"Cell {i + 1}: {voltage:.3f} V\t")

                        # Nájdi min, max a delta
                        min_voltage = min(cell_voltages)
                        max_voltage = max(cell_voltages)
                        min_index = cell_voltages.index(min_voltage) + 1
                        max_index = cell_voltages.index(max_voltage) + 1
                        delta_u = max_voltage - min_voltage

                        blynk_write(13, f"\nMin.: Cell {min_index} = {min_voltage:.3f}V ")
                        blynk_write(13, f"\tMax.: Cell {max_index} = {max_voltage:.3f}V")
                        blynk_write(13, f"\nDelta U: {delta_u:.3f} V")
                        
                        temp_fet = struct.unpack_from('>H', data, bytecount + 3)[0]
                        if temp_fet > 100:
                            temp_fet = -(temp_fet - 100)
                        temp_1 = struct.unpack_from('>H', data, bytecount + 6)[0]
                        if temp_1 > 100:
                            temp_1 = -(temp_1 - 100)
                        temp_2 = struct.unpack_from('>H', data, bytecount + 9)[0]
                        if temp_2 > 100:
                            temp_2 = -(temp_2 - 100)

                        print(f" BMS - Temp1: {temp_1} °C")
                        print(f" BMS - Temp2: {temp_2} °C")

                        voltage = struct.unpack_from('>H', data, bytecount + 12)[0] / 100
                        print(f" BMS - Napätie batérie: {voltage} V")

                        unsigned_current = struct.unpack_from('>H', data, bytecount + 15)[0]
                        current = unsigned_current / 100
                        if unsigned_current > 32767:
                            current = (32767 - unsigned_current) / 100
                        current = -current
                        print(f" BMS - Prúd: {current} A")

                        capacity = struct.unpack_from('>B', data, bytecount + 18)[0]
                        print(f" BMS - Zostávajúca kapacita: {capacity} %")

                        bc = param.Params.BATTERY_CAPACITY
                        blynk_write(70, str(capacity))

                        allBmsData = f"""
.......................................
\tUDAJE BMS :
Temp1: {temp_1} °C , Temp2: {temp_2} °C
Napätie batérie: {voltage} V
Prúd: {current} A
Zostávajúca kapacita: {capacity} %
.......................................
\n"""
                        blynk_write(13, allBmsData)
                        blynk_write(13, datetime.datetime.now().strftime("%H:%M:%S"))
                        blynk_write(13, f"\n")
                        blynk_write(13, f"\n")

                        # Uloženie posledných platných údajov
                        last_bms_data = {
                            'capacity': capacity,
                            'voltage': voltage,
                            'current': current,
                            'temp_1': temp_1,
                            'temp_2': temp_2
                        }

                        bms.reset_input_buffer()
                        return last_bms_data
            else:
                bms.reset_input_buffer()
                print(f" Chyba: Žiadne údaje z BMS (pokus {attempt + 1}/{max_retries})")
                continue
        except Exception as e:
            print(f" Chyba pri čítaní BMS (pokus {attempt + 1}/{max_retries}): \n\t{e}")
            if bms is not None:
                bms.reset_input_buffer()
            continue
    print(f" Chyba: Nepodarilo sa načítať BMS po {max_retries} pokusoch")
    return last_bms_data  # Vráti posledné platné údaje namiesto default_data