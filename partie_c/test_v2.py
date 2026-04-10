import socket
import time
from protocol import Message, ActionType

# Configuration
ADDR_C = ("127.0.0.1", 5000)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("--- Test de communication Binaire Version 2 ---")

# Création du message avec timestamp actuel
msg = Message(
    id_joueur=1,
    pos_x=150,
    pos_y=250,
    action=ActionType.MOVE,
    timestamp=time.time(),
    target_id="CAVALIER_01"
)

# Envoi au nœud C
sock.sendto(msg.serialize(), ADDR_C)
print(f"Message binaire envoyé au C ! (Action: {msg.action.name})")