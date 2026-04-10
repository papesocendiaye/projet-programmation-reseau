from dataclasses import dataclass
from enum import IntEnum
import socket

class ActionType(IntEnum):
    MOVE = 0
    ATTACK = 1
    SPAWN = 2
    REQ_OWNERSHIP = 3
    DIE = 4             # Pour forcer la suppression d'une unité (ex: quand on perd la connexion, ou pour les unités contrôlées par l'adversaire qui disparaissent)
    VICTORY = 5         # Pour annoncer la fin de la bataille (ex: quand on gagne, ou pour forcer l'adversaire à afficher sa défaite)
    UPDATE_STATS = 6    # Pour synchroniser sur les stats d'une unité (ex: après une attaque, pour que les deux joueurs aient les mêmes infos sur la santé des unités)

@dataclass
class Message:
    id_joueur: int
    pos_x: float
    pos_y: float
    action: ActionType
    target_id: str

    def serialize(self) -> bytes:
        # Format simple sans \n (UDP s'occupe de la séparation)
        msg_str = f"{self.id_joueur}|{int(self.pos_x)}|{int(self.pos_y)}|{self.action.value}|{self.target_id}"
        return msg_str.encode('utf-8')

    @classmethod
    def deserialize(cls, data_str: str):
        parts = data_str.strip().split("|")
        if len(parts) != 5:
            return None
        try:
            return cls(
                id_joueur=int(parts[0]),
                pos_x=int(parts[1]),
                pos_y=int(parts[2]),
                action=ActionType(int(parts[3])),
                target_id=parts[4],
            )
        except Exception:
            return None
