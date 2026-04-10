from dataclasses import dataclass
from enum import IntEnum

class ActionType(IntEnum):
    MOVE = 0
    ATTACK = 1
    SPAWN = 2
    # --- Nouveaux types pour la V2 ---
    REQ_OWNERSHIP = 3  # Demander le jeton d'une unité
    GIVE_OWNERSHIP = 4 # Transférer le jeton + l'état actuel
    RELEASE_OWNERSHIP = 5 # Relâcher le jeton
    SYNC_STATE = 6     # Mise à jour forcée de l'état (ex: PV après attaque)
    HELLO = 7          # Découverte des pairs

@dataclass
class Message:
    id_joueur: int    # ID de l'émetteur
    target_id: str    # ID de l'unité concernée (la ressource)
    action: ActionType
    pos_x: float = 0.0
    pos_y: float = 0.0
    hp: int = -1       # État de santé actuel de l'unité
    equipe: int = -1   # Équipe de l'unité
    timestamp: float = 0.0 # Pour l'arbitrage en cas de requêtes simultanées

    def serialize(self) -> bytes:
        # Passage en format binaire recommandé pour la V2
        # On peut garder le format texte pour un premier test, 
        # mais le cahier des charges demande de l'efficacité.
        msg_str = f"{self.id_joueur}|{self.target_id}|{self.action.value}|{self.pos_x}|{self.pos_y}|{self.hp}|{self.equipe}|{self.timestamp}"
        return msg_str.encode('utf-8')

    @classmethod
    def deserialize(cls, data: str):
        try:
            p = data.strip().split('|')
            return cls(
                id_joueur=int(p[0]),
                target_id=p[1],
                action=ActionType(int(p[2])),
                pos_x=float(p[3]),
                pos_y=float(p[4]),
                hp=int(p[5]),
                equipe=int(p[6]),
                timestamp=float(p[7])
            )
        except Exception:
            return None