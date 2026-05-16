import struct
import json
import time

class ProtocolExpert:
    def __init__(self):
        # Format : 4 int (i), 1 double (d), 32 char (s), 1 unsigned short (H)
        self.format = "!IffI16sdH" 

    def create_json_rules(self, team_name):
        """ Sécurité : Génère les règles communes en JSON avant la partie  """
        rules = {
            "team": team_name,
            "version": "V2_ABIDA",
            "security_level": "High",
            "timestamp_init": time.time()
        }
        return json.dumps(rules)

    def pack_message(self, p_id, x, y, action, unit_id):
        """ Sérialisation binaire pour l'efficacité [cite: 113, 147] """
        ts = time.time() # Horodatage pour le déterminisme [cite: 93]
        u_id_bytes = unit_id.encode('utf-8').ljust(16, b'\x00')
        # on va calculer un checksum simple pour la sécurité 
        checksum = (int(p_id) + int(x) + int(y) + int(action)) % 65535 
        
        return struct.pack(self.format, p_id, x, y, action, ts, u_id_bytes, checksum)