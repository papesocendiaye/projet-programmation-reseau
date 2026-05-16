import struct
import time
import socket

PORT = 5000
DEST_IP = "127.0.0.1"

def test_envoi_coherence():
    # NOUVEAU FORMAT SYNCHRONISÉ : 
    # ! = Réseau, I = id, i = x, i = y, I = action, d = timestamp, 32s = unit_id, H = checksum
    format_bin = "!Iiii d 32s H"
    
    player_id = 1
    x, y = 10, 20 # Entiers pour correspondre au int32_t du C
    action_type = 3
    unit_id = b"Orc_01".ljust(32, b'\x00') # Taille 32 pour correspondre au C
    ts = time.time()
    
    # Checksum identique au calcul du C
    checksum = (player_id + x + y + action_type) % 65535
    
    # ATTENTION : L'ordre doit être identique au struct C !
    paquet = struct.pack(format_bin, player_id, x, y, action_type, ts, unit_id, checksum)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(paquet, (DEST_IP, PORT))
    
    print(f"--- TEST ABIDA V2 ---")
    print(f"[PYTHON] Envoyé: {len(paquet)} octets | Checksum: {checksum}")

"""def test_envoi_coherence():
   
    # Format : ! (Réseau), I (uint32), f (float), f (float), I (uint32), 16s (ID), d (double), H (uint16)
    format_bin = "!IffI16sdH"

    player_id = 1
    x, y = 10.0, 20.0
    action_type = 3  # REQ_OWNERSHIP
    unit_id = b"Orc_01".ljust(16, b'\x00')
    ts = time.time()
    
    # --- SYNCHRONISATION DU CHECKSUM ---
    # On convertit tout en entier AVANT l'addition pour correspondre au code C
    checksum = (int(player_id) + int(x) + int(y) + int(action_type)) % 65535
    
    paquet = struct.pack(format_bin, player_id, x, y, action_type, unit_id, ts, checksum)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(paquet, (DEST_IP, PORT))
    
    print("--- TEST ABIDA V2 ---")
    print(f"[PYTHON] Requête envoyée (Taille: {len(paquet)} octets)")
    print(f"[DEBUG] Checksum envoyé: {checksum}") """

if __name__ == "__main__":
    test_envoi_coherence() 