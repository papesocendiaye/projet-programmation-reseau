from dataclasses import dataclass
from enum import IntEnum

class ActionType(IntEnum):
    MOVE = 0
    ATTACK = 1
    SPAWN = 2
    REQ_OWNERSHIP = 3
    DIE = 4             # Pour forcer la suppression d'une unité (ex: quand on perd la connexion, ou pour les unités contrôlées par l'adversaire qui disparaissent)
    VICTORY = 5         # Pour annoncer la fin de la bataille (ex: quand on gagne, ou pour forcer l'adversaire à afficher sa défaite)
    UPDATE_STATS = 6    # Pour synchroniser sur les stats d'une unité (ex: après une attaque, pour que les deux joueurs aient les mêmes infos sur la santé des unités)
    HELLO = 4 # Ajouté pour être synchro avec le C
    DEATH = 5 # Mort d'une unité (V1 MAJ)

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
        return f"{self.id_joueur}|{self.pos_x}|{self.pos_y}|{int(self.action)}|{self.target_id}".encode('utf-8')

    @classmethod
    def deserialize(cls, data: str):
        try:
            p = data.strip().split('|')
            return cls(int(p[0]), int(p[1]), int(p[2]), ActionType(int(p[3])), p[4])
        except: return None