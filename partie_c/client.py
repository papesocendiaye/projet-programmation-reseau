import socket
import sys
import os
import time

# --- Résolution du problème d'import ---
# On ajoute le dossier parent (la racine du projet) au chemin Python
# pour qu'il puisse trouver ton fichier protocol.py
dossier_parent = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(dossier_parent)

# Import du dictionnaire commun que ton équipe a défini
from protocol import Message, ActionType

class IPCClient:
    def __init__(self, port_ecoute=5001, port_c=5000):
        """
        Initialise la connexion locale (IPC) avec le programme C via UDP.
        port_ecoute: Le port sur lequel ce script Python écoute (5001 par défaut)
        port_c: Le port sur lequel le programme C écoute (5000 par défaut)
        """
        # 1. Utilisation de l'UDP (AF_INET et SOCK_DGRAM)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 2. On attache la socket au port d'écoute Python
        self.sock.bind(("127.0.0.1", port_ecoute))
        
        # 3. NON-BLOQUANT : Indispensable pour ne pas figer le jeu plus tard
        self.sock.setblocking(False) 
        
        # L'adresse locale du programme C
        self.c_address = ("127.0.0.1", port_c)

    def send_action(self, msg: Message):
        """
        Transforme l'objet Message en texte (serialize) et l'envoie au C.
        """
        try:
            self.sock.sendto(msg.serialize(), self.c_address)
        except Exception as e:
            print(f"[PYTHON -> C] Erreur d'envoi : {e}")

    def get_pending_messages(self):
        """
        Lit instantanément tous les messages UDP en attente.
        Retourne une liste d'objets Message.
        """
        msgs = []
        try:
            while True:
                data, _ = self.sock.recvfrom(1024)
                # Transforme le texte reçu en objet Message (deserialize)
                msg_obj = Message.deserialize(data.decode('utf-8'))
                if msg_obj:
                    msgs.append(msg_obj)
        except BlockingIOError:
            # S'il n'y a plus rien à lire, on sort de la boucle tranquillement
            pass 
        return msgs

# ==========================================
#         ZONE DE TEST INDÉPENDANTE
# ==========================================
# Ce code s'exécute uniquement si on lance directement "python client.py"
# Il ne gênera pas engine.py plus tard.

if __name__ == "__main__":
    print("--- Démarrage du Test Client Python ---")
    print("⚠️  IMPORTANT : Lance le programme C (main) AVANT ce script Python !")
    print("---------------------------------------\n")
    
    try:
        ipc = IPCClient()
        print("[OK] Socket Python initialisée sur le port 5001.")
        
        # Création d'un message test respectant votre protocole
        msg_spawn = Message(
            id_joueur=1,
            pos_x=10,
            pos_y=10,
            action=ActionType.SPAWN,
            target_id="CAVALIER_R1"
        )
        
        print("Envoi en boucle... (Appuie sur Ctrl+C pour arrêter)\n")
        compteur = 0
        
        while True:
            # On simule un mouvement en changeant la position X à chaque fois
            msg_spawn.pos_x += 5
            
            # On envoie le message au C
            ipc.send_action(msg_spawn)
            compteur += 1
            print(f"[{compteur}] Envoyé : {msg_spawn.serialize().decode('utf-8')}")
            
            # On vérifie si le C nous renvoie quelque chose
            reponses = ipc.get_pending_messages()
            for rep in reponses:
                print(f"   >>> Reçu du réseau : {rep.action.name} sur {rep.target_id} en ({rep.pos_x}, {rep.pos_y})")
                
            # Pause d'1 seconde avant le prochain paquet
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[!] Test arrêté par l'utilisateur.")
        ipc.sock.close()
