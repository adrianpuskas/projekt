import logging

# Nastavenie logovania
logging.basicConfig(
    filename="system.log",  # Môžeš zmeniť na iný súbor alebo použiť konzolu
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log(msg, source="General"):
    """Funkcia na logovanie s označením zdroja správy."""
    logging.info(f"[{source}] {msg}")
    print(f"[{source}] {msg}")  # Voliteľné, ak chceš vidieť výstup aj v konzole
