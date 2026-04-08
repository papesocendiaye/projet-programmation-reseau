class TCPBuffer:
    def __init__(self):
        self.buffer = ""

    def add_data(self, data_bytes: bytes):
        """Ajoute les nouvelles données reçues du socket."""
        self.buffer += data_bytes.decode('utf-8')

    def get_next_message(self):
        """
        Extrait un message complet s'il y en a un (termine par \n).
        Retourne le message (sans le \n), ou None si le message est incomplet.
        """
        if '\n' in self.buffer:
            # Sépare le premier message du reste du buffer
            message, self.buffer = self.buffer.split('\n', 1)
            return message
        return None

# --- EXEMPLE D'UTILISATION ---
# buf = TCPBuffer()
# buf.add_data(b"1|120|250|1|Pb1\n2|") # On reçoit un message entier + un bout
# print(buf.get_next_message()) # Affiche: 1|120|250|1|Pb1
# print(buf.get_next_message()) # Affiche: None (le message 2 n'est pas fini)
# buf.add_data(b"300|300|0|Pc3\n") # La suite arrive
# print(buf.get_next_message()) # Affiche: 2|300|300|0|Pc3