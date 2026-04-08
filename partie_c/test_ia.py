import socket
# On importe le nouveau protocole simplifié
from protocol import Message, ActionType 

# Configuration
DEST_IP = "127.0.0.1"
PORT = 5000

# Création d'un message de test
# (Joueur 2, Unité U99, Attaque, position 450,300)
msg = Message(
    id_joueur=2, 
    pos_x=450, 
    pos_y=300, 
    action=ActionType.ATTACK, 
    target_id="U99"
)

# Envoi via UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(msg.serialize(), (DEST_IP, PORT))

print(f"Message envoyé : {msg.target_id} attaque !")