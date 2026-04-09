from dataclasses import dataclass
from enum import IntEnum

class ActionType(IntEnum):
    MOVE = 0
    ATTACK = 1
    SPAWN = 2
    REQ_OWNERSHIP = 3
    HELLO = 4 # Ajouté pour être synchro avec le C
    DEATH = 5 # Mort d'une unité (V1 MAJ)

@dataclass
class Message:
    id_joueur: int
    pos_x: int
    pos_y: int
    action: ActionType
    target_id: str

    def serialize(self) -> bytes:
        return f"{self.id_joueur}|{self.pos_x}|{self.pos_y}|{int(self.action)}|{self.target_id}".encode('utf-8')

    @classmethod
    def deserialize(cls, data: str):
        try:
            p = data.strip().split('|')
            return cls(int(p[0]), int(p[1]), int(p[2]), ActionType(int(p[3])), p[4])
        except: return None