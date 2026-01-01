####
import time
import serial  ## pre komunikaciu s meničom
import crcmod
import serial.tools.list_ports
import threading

stop_threads = False

ser = None


def find_specific_serial_port(target_vid, target_pid):
    ports = serial.tools.list_ports.comports()

    for port in ports:
        if port.vid == target_vid and port.pid == target_pid:
            print(f"Nájdený port: {port.device}")
            return port.device

    raise Exception("Žiadny vhodný port pre menič nebol nájdený")


def initializePort():
    global ser

    if ser is not None:
        ser.close()

    # Zadaj VID a PID meniča
    target_vid = 1659  # VID tvojho meniča
    target_pid = 8963  # PID tvojho meniča

    # Hľadaj port pre konkrétny menič
    port = find_specific_serial_port(target_vid, target_pid)

    ser = serial.Serial(port, 2400)


def closePort():
    global ser
    if ser is not None:
        print("Zatváram sériový port...")
        ser.close()
        ser = None
    else:
        print("Sériový port je už zavretý.")


lock = threading.Lock()

###################################################################################

# Pomocné premenné / konštanty
flags_enabled = []
flags_disabled = []

###################################################################################
def run_command_get(command):
    xmodem_crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0x0000, xorOut=0x0000)

    crc = xmodem_crc_func(command)

    crc1 = (crc >> 8) & 0xFF
    crc2 = crc & 0xFF
    full_command = command + bytes([crc1, crc2]) + b'\r'

    ser.close()
    ser.open()
    ser.write(full_command)
    time.sleep(0.5)
    response = ser.read_all()
    ser.close()

    if (len(response) == 0):
        print("Chyba pri čítaní nastavených dát z meniča", end="", flush=True)
        for i in range(0, 3):
            print(".", end="", flush=True)
            time.sleep(1)
        print("\n")

    else:
        return response


def run_command_set(command, value):
    xmodem_crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0x0000, xorOut=0x0000)

    value_str = str(value).replace('.', ',')

    value_bytes = value_str.encode('latin-1')
    command_with_value = command + value_bytes
    crc = xmodem_crc_func(command_with_value)

    crc1 = (crc >> 8) & 0xFF
    crc2 = crc & 0xFF

    full_command = command_with_value + bytes([crc1, crc2]) + b'\r'
    print("FULL COMMAND:", full_command)

    ser.close()
    ser.open()
    ser.write(full_command)
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