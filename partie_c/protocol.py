from dataclasses import dataclass
from enum import IntEnum
import socket

class ActionType(IntEnum):
    MOVE = 0
    ATTACK = 1
    SPAWN = 2
    REQ_OWNERSHIP = 3

@dataclass
class Message:
    id_joueur: int
    pos_x: float
    pos_y: float
    action: ActionType
    target_id: str

    
    def serialize(self) -> bytes:
        # On utilise des float avec 2 ou 3 décimales pour la précision du mouvement
        msg_str = f"{self.id_joueur}|{self.pos_x:.3f}|{self.pos_y:.3f}|{self.action.value}|{self.target_id}"
        return msg_str.encode('utf-8')

    @classmethod
    def deserialize(cls, data_str: str):
        parts = data_str.strip().split("|")
        if len(parts) != 5:
            return None
        try:
            return cls(
                id_joueur=int(parts[0]),
                pos_x=float(parts[1]), # <-- Changé en float
                pos_y=float(parts[2]), # <-- Changé en float
                action=ActionType(int(parts[3])),
                target_id=parts[4],
            )
        except Exception:
            return None