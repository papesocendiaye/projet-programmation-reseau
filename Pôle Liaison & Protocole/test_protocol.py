# Fichier : test_protocol.py
from protocol import Message, ActionType
from tampon import TCPBuffer

print("--- DEBUT DU CRASH-TEST PYTHON ---")

# 1. On crée un faux buffer réseau
buffer = TCPBuffer()

# 2. SIMULATION DE COUPURE : Le réseau est lent
print("\n[Réseau] On reçoit un demi-message...")
buffer.add_data(b"1|120|250|0|No") # Attention, pas de \n à la fin !

message_lu = buffer.get_next_message()
print(f"-> Résultat de la lecture : {message_lu} (C'est normal, il manque la fin !)")

# 3. SIMULATION DE SPAM : La fin du message arrive, collée à 2 autres messages
print("\n[Réseau] On reçoit la fin, suivie de deux autres messages collés...")
# "ne\n" finit le premier message. Puis on colle le joueur 2 et le joueur 3.
buffer.add_data(b"ne\n2|50|50|1|Pb1\n3|300|300|2|Pc3\n")

print("\n--- EXTRACTION DES MESSAGES ---")
while True:
    msg_str = buffer.get_next_message()
    if msg_str is None:
        print("-> Plus de messages complets dans le buffer.")
        break
    
    print(f"\nMessage brut lu : {msg_str}")
    
    # 4. On vérifie que la désérialisation fonctionne
    try:
        msg_obj = Message.deserialize(msg_str)
        print(f"Succès ! Objet recréé : Le joueur {msg_obj.id_joueur} fait l'action n°{msg_obj.action.value} vers '{msg_obj.target_id}'")
    except Exception as e:
        print(f"Erreur de lecture du message : {e}")