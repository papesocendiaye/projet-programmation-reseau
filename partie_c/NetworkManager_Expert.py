import time
from protocol_expert import ProtocolExpert

class NetworkManagerExpert:
    def __init__(self, player_id):
        self.player_id = player_id
        self.protocol = ProtocolExpert()
        # Table de propriété : {unit_id: {"owner": p_id, "timestamp": ts, "hp": hp}}
        self.ownership_table = {}
        # Unités que JE contrôle actuellement [cite: 51]
        self.my_units = set()

    def request_ownership(self, unit_id, target_x, target_y):
        """ 
        Logique V2 : On ne peut pas agir sans la propriété réseau.
        On envoie une requête ACTION_REQ_OWNERSHIP. [cite: 165]
        """
        print(f"[COHÉRENCE] Demande de propriété pour l'unité {unit_id}...")
        # On prépare le message binaire de type 3 (REQ_OWNERSHIP) [cite: 165]
        return self.protocol.pack_message(self.player_id, target_x, target_y, 3, unit_id)

    def resolve_conflict(self, unit_id, remote_timestamp):
        """
        DÉTERMINISME : Si deux joueurs demandent la même unité, 
        le timestamp le plus ancien gagne. [cite: 47, 93, 102]
        """
        local_timestamp = self.ownership_table.get(unit_id, {}).get("timestamp", float('inf'))
        if remote_timestamp < local_timestamp:
            print(f"[SYSTEME] Conflit résolu : L'IA distante est prioritaire.")
            return False # On cède la propriété
        return True # On garde la propriété

    def on_receive_ack(self, unit_id, state_data):
        """
        Vérification à la réception : L'action n'est validée visuellement 
        qu'après réception de l'ACK. [cite: 166, 167, 168]
        """
        self.my_units.add(unit_id)
        self.ownership_table[unit_id] = {"owner": self.player_id, "state": state_data}
        print(f"[VISUEL] Propriété de {unit_id} confirmée. Mise à jour de la scène.")