import socket
import sys
import os
import time

# --- Résolution du problème d'import ---
dossier_parent = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(dossier_parent)

# Import du dictionnaire commun (V2 avec binaire/struct)
from protocol import Message, ActionType

class IPCClient:
    def __init__(self, port_ecoute=5001, port_c=5000):
        """
        Initialise la connexion locale (IPC) avec le programme C via UDP.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # On attache la socket au port d'écoute Python (5001 ou 5002)
        self.sock.bind(("127.0.0.1", port_ecoute))
        
        # NON-BLOQUANT : Indispensable pour ne pas figer le jeu
        self.sock.setblocking(False) 
        self.c_address = ("127.0.0.1", port_c)

    def send_action(self, msg: Message):
        """
        Envoie l'objet Message (déjà converti en binaire par serialize()) au C.
        """
        try:
            # msg.serialize() renvoie maintenant des BYTES (binaire), plus besoin de .encode()
            self.sock.sendto(msg.serialize(), self.c_address)
        except Exception as e:
            pass

    def get_pending_messages(self):
        """
        Lit les paquets binaires en attente.
        """
        msgs = []
        try:
            while True:
                # On lit 1024 octets (notre message en fait 60)
                data, _ = self.sock.recvfrom(1024)
                
                # --- CORRECTION V2 ---
                # On passe directement 'data' (les octets) à deserialize.
                # PLUS DE .decode('utf-8') ICI !
                msg_obj = Message.deserialize(data)
                
                if msg_obj:
                    msgs.append(msg_obj)
        except BlockingIOError:
            pass 
        except Exception as e:
            print(f"[IPC] Erreur réception : {e}")
            
        return msgs

# Zone de test mise à jour pour le protocole V2
if __name__ == "__main__":
    print("--- Démarrage du Test Client Python V2 (Binaire) ---")
    try:
        ipc = IPCClient()
        # Message test avec les nouveaux champs V2 (hp, timestamp)
        msg_test = Message(
            id_joueur=1,
            pos_x=10.0,
            pos_y=10.0,
            hp=100.0,
            action=ActionType.SPAWN,
            timestamp=time.time(),
            target_id="TEST_UNIT"
        )
        
        while True:
            ipc.send_action(msg_test)
            print(f"Envoyé : {msg_test.target_id} en binaire")
            
            reponses = ipc.get_pending_messages()
            for rep in reponses:
                print(f">>> Reçu du C : {rep.action.name} pour {rep.target_id}")
                
            time.sleep(1)
    except KeyboardInterrupt:
        ipc.sock.close()