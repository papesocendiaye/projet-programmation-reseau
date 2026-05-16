import socket
import sys
import os
import time

dossier_parent = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(dossier_parent)
from protocol import Message, ActionType

class IPCClient:
    def __init__(self, port_ecoute=5001, port_c=5000):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", port_ecoute))
        self.sock.setblocking(False) 
        self.c_address = ("127.0.0.1", port_c)

    def send_action(self, msg: Message):
        try:
            self.sock.sendto(msg.serialize(), self.c_address)
        except Exception as e:
            pass

    def get_pending_messages(self):
        msgs = []
        try:
            while True:
                data, _ = self.sock.recvfrom(1024)
                # 1. NETTOYAGE VITAL : Enlève les caractères invisibles envoyés par le C (\x00, \n, etc.)
                raw_str = data.decode('utf-8').strip('\x00').strip() 
                
                try:
                    msg_obj = Message.deserialize(raw_str)
                    if msg_obj:
                        msgs.append(msg_obj)
                    else:
                        print(f"[PYTHON] ⚠️ deserialize() a retourné None pour : '{raw_str}'")
                except Exception as e:
                    print(f"[PYTHON] ❌ Erreur fatale de lecture du message '{raw_str}' : {e}")

        except BlockingIOError:
            pass 
        except ConnectionResetError:
            pass
            
        return msgs

if __name__ == "__main__":
    print("--- Démarrage du Test Client Python ---")
    ipc = IPCClient()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        ipc.sock.close()