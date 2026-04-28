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
        # On multiplie par 1000 et on force en entier (évite les bugs de virgule du C)
        pos_x_int = int(self.pos_x * 1000)
        pos_y_int = int(self.pos_y * 1000)
        msg_str = f"{self.id_joueur}|{pos_x_int}|{pos_y_int}|{self.action.value}|{self.target_id}"
        return msg_str.encode('utf-8')

    @classmethod
    def deserialize(cls, data_str: str):
        parts = data_str.strip().split("|")
        if len(parts) != 5:
            return None
        try:
            return cls(
                id_joueur=int(parts[0]),
                # On re-divise par 1000 à la réception pour retrouver les décimales
                pos_x=(float(parts[1]) / 1000.0), 
                pos_y=(float(parts[2]) / 1000.0), 
                action=ActionType(int(parts[3])),
                target_id=parts[4],
            )
        except Exception:
            return None
        
