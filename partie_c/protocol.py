import struct
from dataclasses import dataclass
from enum import IntEnum
import time

class ActionType(IntEnum):
    MOVE = 0
    ATTACK = 1
    SPAWN = 2
    REQ_OWNERSHIP = 3
    ACK_OWNERSHIP = 4
    HELLO = 5

@dataclass
class Message:
    id_joueur: int
    pos_x: float
    pos_y: float
    hp: float         # NOUVEAU : l'état de la ressource
    action: ActionType
    timestamp: float  # NOUVEAU : gestion des conflits
    target_id: str

    # Le format de traduction Python <-> C :
    # <  : little-endian (standard des PC actuels)
    # 5i : 5 entiers de 32 bits (id_joueur, pos_x, pos_y, hp, action)
    # d  : 1 double (timestamp)
    # 32s: 1 tableau de 32 caractères (target_id)
    STRUCT_FORMAT = "<iiiiid32s"

    def serialize(self) -> bytes:
        # On garde notre ruse du x1000 pour la précision des mouvements sans float côté C
        pos_x_int = int(self.pos_x * 1000)
        pos_y_int = int(self.pos_y * 1000)
        hp_int = int(self.hp * 1000) # Pareil pour les HP
        
        # On convertit le texte en binaire, et on force la taille à 32 octets exactement (avec des \0)
        target_bytes = self.target_id.encode('utf-8')[:32].ljust(32, b'\0')
        
        # struct.pack compresse tout ça en un seul bloc binaire !
        return struct.pack(
            self.STRUCT_FORMAT,
            self.id_joueur,
            pos_x_int,
            pos_y_int,
            hp_int,
            self.action.value,
            self.timestamp,
            target_bytes
        )

    @classmethod
    def deserialize(cls, data: bytes):
        # Si la taille ne correspond pas exactement au struct C, on ignore
        if len(data) != struct.calcsize(cls.STRUCT_FORMAT):
            return None
        
        try:
            # On décompresse le binaire
            unpacked = struct.unpack(cls.STRUCT_FORMAT, data)
            
            # On re-transforme les octets en texte et on enlève les \0 à la fin
            target_str = unpacked[6].decode('utf-8', errors='ignore').rstrip('\x00')
            
            return cls(
                id_joueur=unpacked[0],
                pos_x=unpacked[1] / 1000.0,  # On re-divise pour retrouver les décimales
                pos_y=unpacked[2] / 1000.0,
                hp=unpacked[3] / 1000.0,
                action=ActionType(unpacked[4]),
                timestamp=unpacked[5],
                target_id=target_str
            )
        except Exception as e:
            print(f"[ERREUR BINAIRE] {e}")
            return None