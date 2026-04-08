from battle.unit import P, C, K, L, S

def traiter_message_reseau(msg, engine):
    data = msg.split(':')
    if len(data) < 2: 
        return
    
    cmd = data[0]

    # --- CAS A : Apparition d'une unité distante ---
    if cmd == "SPAWN":
        # Format : SPAWN:ID:TYPE:X:Y
        unite_id = data[1]
        unite_type = data[2]
        pos = (float(data[3]), float(data[4]))

        # On vérifie si on ne connaît pas déjà cette unité
        if any(hasattr(u, 'network_id') and u.network_id == unite_id for u in engine.units):
            return

        # Mapping des types vers les classes de ton projet AOE
        classes = {'P': P, 'C': C, 'K': K, 'L': L, 'S': S}
        unit_class = classes.get(unite_type, P)

        # On crée l'unité dans l'équipe adverse ('B' pour Blue par exemple)
        new_unit = unit_class('B', pos)
        new_unit.network_id = unite_id  # On lui injecte l'ID pour la retrouver plus tard
        engine.units.append(new_unit)
        print(f"[RESEAU] Spawn fantôme {unite_id} à {pos}")

    # --- CAS B : Mise à jour d'une unité (Position / Vie) ---
    elif cmd == "UPDATE":
        # Format : UPDATE:ID:X:Y:HP
        unite_id = data[1]
        new_pos = (float(data[2]), float(data[3]))
        new_hp = int(data[4])

        for u in engine.units:
            if hasattr(u, 'network_id') and u.network_id == unite_id:
                u.position = new_pos
                u.current_hp = new_hp
                break