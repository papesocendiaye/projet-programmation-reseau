import socket
import time
from protocol import Message, ActionType

# Configuration
ADDR_C = ("127.0.0.1", 5000)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("--- Test Axe A : Envoi Binaire ---")

# Création d'un message avec TIMESTAMP (Tâche 2)
msg = Message(
    id_joueur=99,
    pos_x=450,
    pos_y=300,
    action=ActionType.MOVE,
    timestamp=time.time(), # Voici la preuve du temps
    target_id="UNITE_TEST_V2"
)

# Envoi
sock.sendto(msg.serialize(), ADDR_C)
print(f"Envoyé : ID {msg.id_joueur} à {msg.timestamp}")