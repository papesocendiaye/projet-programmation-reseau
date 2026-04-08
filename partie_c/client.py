import socket
# ATTENTION : Il faut importer votre protocole commun !
from protocol import Message, ActionType 

class IPCClient:
    def __init__(self, port_ecoute=5001, port_c=5000):
        # 1. AF_INET pour marcher sur Windows et Mac/Linux
        # 2. SOCK_DGRAM car l'équipe C a choisi UDP !
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", port_ecoute))
        
        # 3. Le secret magique : Non-bloquant (Pas besoin de Thread !)
        self.sock.setblocking(False) 
        self.c_address = ("127.0.0.1", port_c)

    def send_action(self, msg: Message):
        """Utilise la fonction serialize() de protocol.py"""
        try:
            self.sock.sendto(msg.serialize(), self.c_address)
        except Exception as e:
            print(f"[RESEAU] Erreur d'envoi : {e}")

    def get_pending_messages(self):
        """Lit tous les paquets UDP reçus instantanément"""
        msgs = []
        try:
            while True:
                data, _ = self.sock.recvfrom(1024)
                # Utilise la fonction deserialize() de protocol.py
                msg_obj = Message.deserialize(data.decode('utf-8'))
                if msg_obj:
                    msgs.append(msg_obj)
        except BlockingIOError:
            # S'il n'y a plus rien à lire, on sort de la boucle tranquillement
            pass 
        return msgs

# === TEST ===
if __name__ == "__main__":
    ipc = IPCClient()
    
    # Création d'un "Vrai" message respectant le protocole C
    msg_spawn = Message(
        id_joueur=1,
        pos_x=10,
        pos_y=10,
        action=ActionType.SPAWN,
        target_id="CAVALIER"
    )
    
    ipc.send_action(msg_spawn)
    print("Action envoyée au C au bon format !")
