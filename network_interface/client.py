# client.py pour la communication avec le C

import socket
import threading
import queue
import time

SOCKET_PATH = "/tmp/medievai_ipc.sock"

class IPCClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.msg_queue = queue.Queue() # File d'attente thread-safe
        self.running = True

    def connect(self):
        try:
            self.sock.connect(SOCKET_PATH)
            print("Python : Connecté au processus système C !")
            
            # Lancement du thread d'écoute en arrière-plan
            listener_thread = threading.Thread(target=self.listen_loop, daemon=True)
            listener_thread.start()
        except Exception as e:
            print(f"Erreur de connexion IPC : {e}")

    def listen_loop(self):
        """Ce code tourne dans un thread séparé et bloque sur recv() sans gêner le jeu"""
        while self.running:
            try:
                data = self.sock.recv(1024)
                if not data:
                    break
                
                # Gestion des délimiteurs \n
                messages = data.decode('utf-8').strip().split('\n')
                for msg in messages:
                    if msg:
                        self.msg_queue.put(msg) # On empile le message reçu
            except Exception:
                break

    def send_action(self, message):
        """Envoie une action locale vers le processus C"""
        try:
            self.sock.sendall((message + "\n").encode('utf-8'))
        except Exception as e:
            print(f"Erreur d'envoi IPC : {e}")

    def get_pending_messages(self):
        """Récupère tous les messages en attente pour les appliquer au jeu"""
        msgs = []
        while not self.msg_queue.empty():
            msgs.append(self.msg_queue.get())
        return msgs

# === SIMULATION DU main.py ===
if __name__ == "__main__":
    ipc = IPCClient()
    ipc.connect()
    
    # Envoi de la position de départ (comme demandé dans la V1)
    ipc.send_action("SPAWN:P1:CAVALIER:10:10")
    
    print("Boucle de jeu démarrée...")
    frame_count = 0
    
    try:
        while True:
            # 1. Traitement des événements distants (Ne bloque PAS)
            for msg in ipc.get_pending_messages():
                print(f"[JEU] Appliquer l'action distante : {msg}")
                # Ex: if msg.startswith("UPDATE"): update_enemy_position(msg)

            # 2. Simulation de la boucle de jeu classique (Affichage, IA)
            frame_count += 1
            if frame_count % 3 == 0: # Le joueur bouge toutes les 3 frames
                ipc.send_action(f"UPDATE:P1:{frame_count}:10:100")
            
            time.sleep(1) # Simulation de la vitesse du jeu
            
    except KeyboardInterrupt:
        print("Arrêt...")
        ipc.running = False