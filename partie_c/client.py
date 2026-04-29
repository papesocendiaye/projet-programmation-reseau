import socket
import sys
import os

dossier_parent = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(dossier_parent)

from protocol import Message, ActionType

class IPCClient:
    def __init__(self, port_ecoute=5001, port_c=5000):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # SO_REUSEADDR : indispensable sous Windows lors d'un restart rapide,
        # sinon l'ancien binding peut bloquer le nouveau pendant quelques secondes.
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except OSError:
            pass
        self.sock.bind(("127.0.0.1", port_ecoute))
        self.sock.setblocking(False)
        self.c_address = ("127.0.0.1", port_c)

    def send_action(self, msg: Message):
        try:
            self.sock.sendto(msg.serialize(), self.c_address)
        except Exception:
            pass # Si le C n'est pas prêt, on ignore

    def get_pending_messages(self):
        msgs = []
        try:
            while True:
                data, _ = self.sock.recvfrom(1024)
                msg_obj = Message.deserialize(data)
                if msg_obj:
                    msgs.append(msg_obj)
        except BlockingIOError:
            pass 
        except ConnectionResetError:
            pass # Capture et cache l'erreur Windows 10054
        except Exception as e:
            print(f"[IPC] Erreur réception : {e}")
            
        return msgs