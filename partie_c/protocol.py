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
    pos_x: int
    pos_y: int
    action: ActionType
    target_id: str

    def serialize(self) -> bytes:
        # Format simple sans \n (UDP s'occupe de la séparation)
        msg_str = f"{self.id_joueur}|{self.pos_x}|{self.pos_y}|{self.action.value}|{self.target_id}"
        return msg_str.encode('utf-8')

    @classmethod
    def deserialize(cls, data_str: str):
        parts = data_str.strip().split('|')
        if len(parts) != 5:
            return None
        return cls(
            id_joueur=int(parts[0]),
            pos_x=int(parts[1]),
            pos_y=int(parts[2]),
            action=ActionType(int(parts[3])),
            target_id=parts[4]
        )