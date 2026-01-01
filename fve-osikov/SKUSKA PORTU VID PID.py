import serial.tools.list_ports

ports = serial.tools.list_ports.comports()
for port in ports:
    print(f"Port: {port.device}, VID: {port.vid}, PID: {port.pid}, Description: {port.description}")
