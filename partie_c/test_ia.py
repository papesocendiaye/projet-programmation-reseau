import socket
from protocol import Message  # Message est dans protocol.py
from tampon import TCPBuffer   # TCPBuffer est dans tampon.py

# On crée un serveur qui attend le programme C
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('0.0.0.0', 5000))
server.listen(1)
print("IA en attente du programme C...")

conn, addr = server.accept()
buf = TCPBuffer()

data = conn.recv(1024)
if data:
    buf.add_data(data)
    msg_str = buf.get_next_message()
    if msg_str:
        msg = Message.deserialize(msg_str)
        print(f"IA a reçu : Joueur {msg.id_joueur} se déplace en ({msg.pos_x}, {msg.pos_y})")

conn.close()
server.close()