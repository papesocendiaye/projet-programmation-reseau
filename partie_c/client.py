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
            # En V2 binaire, msg.serialize() renvoie directement des octets bruts !
            self.sock.sendto(msg.serialize(), self.c_address)
        except Exception as e:
            pass

    def get_pending_messages(self):
        msgs = []
        try:
            while True:
                # Lecture binaire (plus de .decode() ni de .strip() !)
                data, _ = self.sock.recvfrom(1024)
                try:
                    msg_obj = Message.deserialize(data)
                    if msg_obj:
                        msgs.append(msg_obj)
                except Exception as e:
                    print(f"[PYTHON] ❌ Erreur de désérialisation binaire : {e}")

        except BlockingIOError:
            pass 
        except ConnectionResetError:
            pass
            
        return msgs