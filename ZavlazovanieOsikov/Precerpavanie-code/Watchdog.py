# Watchdog.py
# Import potrebných modulov
import os
import subprocess
import time

#?###########################################################

try:
    while True:
        print("Starting Main.py...")
        env = os.environ.copy()
        env['PYTHONPATH'] = '/usr/lib/python3/dist-package/RPi.GPIO' # cesta k modulu RPi.GPIO
        proc = subprocess.Popen(["/usr/bin/python3.9", "Main.py"], stdin=subprocess.PIPE, env=env)  # spustenie Main.py v novom procese a handle procesu je uložený v premennej proc.

        while True:
            if proc.poll() is not None: # kontrola ukončenia procesu (ak sa proces ukončil)
                if proc.returncode != 0:
                    print(f"Main.py exited with code {proc.returncode}")
                else:
                    print("Main.py exited normally") # ukončenie bez chyby
                break

            #ak proces stále beží
            try:
                proc.stdin.write(b'\x00') # zaslanie fiktívneho bajt procesu, aby skontroloval, či je proces stále nažive
                proc.stdin.flush()

            # ak nastane chyba - BrokenPipeError
            except BrokenPipeError:
                print("BrokenPipeError occurred, killing Main.py...")
                proc.kill() # ukončenie procesu
                break

            # ak nastane chyba - ConnectionRefusedError
            except ConnectionRefusedError:
                print("ConnectionRefusedError occurred, killing Main.py...")
                proc.kill() # ukončenie procesu
                break

            # ak nastane chyba - ValueError
            except ValueError:
                print("ValueError occurred, killing Main.py...")
                proc.kill() # ukončenie procesu
                break

            # ak nastane iná chyba
            except Exception as e:
                print(f"Error occurred: {str(e)}, killing Main.py...")
                proc.kill() # ukončenie procesu
                break

            time.sleep(1)

        time.sleep(1)

#?###########################################################

except KeyboardInterrupt:
    print("Keyboard interrupt detected, stopping script...") # ukončenie behu používateľom