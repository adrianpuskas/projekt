import time
import serial
import crcmod
import serial.tools.list_ports
import threading
import datetime  # Opravený import

stop_threads = False
ser = None
lock = threading.Lock()
flags_enabled = []
flags_disabled = []

def find_specific_serial_port(target_vid, target_pid):
    try:
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.vid == target_vid and port.pid == target_pid:
                print(f"\tNájdený port: {port.device}")
                return port.device
        raise Exception("Žiadny vhodný port pre menič nebol nájdený")
    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tChyba pri hľadaní portu: \n\t\t{e}")
        raise

def initializePort():
    global ser
    try:
        if ser is not None and ser.is_open:
            print(z&"Port je už otvorený, preskakujem inicializáciu.")
            return
        # Zadaj VID a PID meniča
        target_vid = 1659  # VID tvojho meniča
        target_pid = 8963  # PID tvojho meniča
        port = find_specific_serial_port(target_vid, target_pid)
        ser = serial.Serial(port, 2400, timeout=1)
        print(f"\tPort inicializovaný: {port}")
    except Exception as e:
        print(f"\tChyba pri inicializácii portu: \n\t\t{e}")
        ser = None
        raise

def closePort():
    global ser
    try:
        if ser is not None and ser.is_open:
            ser.close()
            print(f"\tSériový port zatvorený.")
        else:
            print(f"\tSériový port je už zavretý.")
    except Exception as e:
        print(f"\tChyba pri zatváraní portu: \n\t\t{e}")
    finally:
        ser = None

def run_command_get(command):
    xmodem_crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0x0000, xorOut=0x0000)
    with lock:
        for attempt in range(5):
            try:
                if ser is None or not ser.is_open:
                    initializePort()
                crc = xmodem_crc_func(command)
                crc1 = (crc >> 8) & 0xFF
                crc2 = crc & 0xFF
                full_command = command + bytes([crc1, crc2]) + b'\r'
                ser.write(full_command)
                time.sleep(1)  # Zvýšené oneskorenie
                response = ser.read_all()
                if len(response) == 0 or b"NAKss" in response:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tChyba: Neprišla žiadna odpoveď na príkaz {command.decode('latin-1')}")
                    raise Exception("Žiadna odpoveď od meniča")
                return response
            except Exception as e:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tPokus {attempt + 1}/5: Chyba pri príkaze {command.decode('latin-1')}: \n\t\t{e}")
                try:
                    closePort()
                    time.sleep(1) ## zmena z (3)
                    initializePort()
                except Exception as e2:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tChyba pri reinicializácii portu: \n\t\t{e2}")
                if attempt == 5:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tNepodarilo sa získať odpoveď po 5 pokusoch.")
                    return None
            time.sleep(1) ## zmena z (3)

def run_command_set(command, value):
    xmodem_crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0x0000, xorOut=0x0000)
    with lock:
        for attempt in range(5):
            try:
                if ser is None or not ser.is_open:
                    initializePort()
                value_str = str(value).replace('.', ',')
                value_bytes = value_str.encode('latin-1')
                command_with_value = command + value_bytes
                crc = xmodem_crc_func(command_with_value)
                crc1 = (crc >> 8) & 0xFF
                crc2 = crc & 0xFF
                full_command = command_with_value + bytes([crc1, crc2]) + b'\r'
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tFULL COMMAND: {full_command}")
                ser.write(full_command)
                time.sleep(1)  # Zvýšené oneskorenie
                response = ser.read_all()
                if len(response) == 0 or b"NAKss" in response:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tChyba: Neprišla žiadna odpoveď na príkaz {command.decode('latin-1')}")
                    raise Exception("Žiadna odpoveď od meniča")
                return response
            except Exception as e:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tPokus {attempt + 1}/5: Chyba pri príkaze {command.decode('latin-1')}: \n\t\t{e}")
                try:
                    closePort()
                    time.sleep(3)
                    initializePort()
                except Exception as e2:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tChyba pri reinicializácii portu: \n\t\t{e2}")
                if attempt == 5:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \n\tNepodarilo sa získať odpoveď po 5 pokusoch.")
                    return None
            time.sleep(3)

def run_command_set_POP02():
    command_str = 'POP02'

    command_str += '\xE2'
    command_str += '\x0B'

    full_command_str = command_str + '\r'
    full_command_bytes = full_command_str.encode('latin-1')

    print("FULL COMMAND:", full_command_bytes)

    ser.close()
    ser.open()
    ser.write(full_command_bytes)
    time.sleep(0.5)
    response = ser.read_all()
    ser.close()

    if len(response) == 0:
        print("Chyba pri čítaní nastavených dát z meniča", end="", flush=True)
        for i in range(0, 3):
            print(".", end="", flush=True)
            time.sleep(1)
        print("\n")
    else:
        return response

"""
def run_command_set_POP02():
    xmodem_crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0x0000, xorOut=0x0000)
    command_str = 'POP02'
    with lock:
        for attempt in range(5):
            try:
                if ser is None or not ser.is_open:
                    initializePort()
                command_str_bytes = command_str.encode('latin-1')
                crc = xmodem_crc_func(command_str_bytes)
                crc1 = (crc >> 8) & 0xFF
                crc2 = crc & 0xFF
                full_command = command_str_bytes + bytes([crc1, crc2]) + b'\r'
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] FULL COMMAND: {full_command}")
                ser.write(full_command)
                time.sleep(1)  # Zvýšené oneskorenie
                response = ser.read_all()
                if len(response) == 0 or b"NAKss" in response:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Chyba: Neprišla žiadna odpoveď na príkaz POP02")
                    raise Exception("Žiadna odpoveď od meniča")
                return response
            except Exception as e:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Pokus {attempt + 1}/5: Chyba pri POP02: {e}")
                try:
                    closePort()
                    time.sleep(3)
                    initializePort()
                except Exception as e2:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Chyba pri reinicializácii portu: {e2}")
                if attempt == 2:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Nepodarilo sa získať odpoveď po 5 pokusoch.")
                    return None
            time.sleep(3)
            
"""    
