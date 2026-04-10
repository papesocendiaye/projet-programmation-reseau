import struct
from dataclasses import dataclass
from enum import IntEnum

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
    pos_x: int
    pos_y: int
    action: ActionType
    timestamp: float
    target_id: str

    # Format : < (little-endian), iiii (4 int), d (1 double), 32s (string 32 bytes)
    _FORMAT = "<iiiid32s"

    def serialize(self) -> bytes:
        target_bytes = self.target_id.encode('utf-8').ljust(32, b'\x00')
        return struct.pack(self._FORMAT, 
                           self.id_joueur, 
                           self.pos_x, 
                           self.pos_y, 
                           int(self.action), 
                           self.timestamp, 
                           target_bytes)

    @classmethod
    def deserialize(cls, data: bytes):
        if len(data) != struct.calcsize(cls._FORMAT):
            return None
        unpacked = struct.unpack(cls._FORMAT, data)
        target_id = unpacked[5].decode('utf-8').rstrip('\x00')
        return cls(unpacked[0], unpacked[1], unpacked[2], ActionType(unpacked[3]), unpacked[4], target_id)