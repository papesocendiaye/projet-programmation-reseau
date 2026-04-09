from battle.unit import Unit

def traiter_message_reseau(msg, engine):
    data = msg.split(':')
    if len(data) < 2: 
        return
    
    cmd = data[0]

    # --- CAS A : Apparition d'une unité distante ---
    if cmd == "SPAWN":
        # Format attendu : SPAWN:ID:TYPE:X:Y
        unite_id = data[1]
        unite_type = data[2]
        pos = (float(data[3]), float(data[4]))

        # On vérifie si on ne connaît pas déjà cette unité
        if any(hasattr(u, 'network_id') and u.network_id == unite_id for u in engine.units):
            return

        # Création de l'unité avec la vraie méthode de ton projet (get_by_type)
        # On assigne arbitrairement l'équipe 'B' (Bleue) pour les unités distantes
        new_unit = Unit().get_by_type(unite_type, 'B', pos)
        
        # On lui injecte l'ID réseau pour la suivre lors des prochains tours
        new_unit.network_id = unite_id 
        
        # Ajout à la liste des unités
        engine.units.append(new_unit)

        # ---> AJOUT POUR LA MINIMAP ET L'IA : Placement sur la carte
        engine.game_map.map[pos] = new_unit
        
        print(f"[RESEAU] Spawn fantôme {unite_type} ({unite_id}) à la position {pos}")

    # --- CAS B : Mise à jour d'une unité (Position / Vie) ---
    elif cmd == "UPDATE":
        # Format attendu : UPDATE:ID:X:Y:HP
        unite_id = data[1]
        new_pos = (float(data[2]), float(data[3]))
        new_hp = float(data[4]) # Modifié en float au cas où des dégâts décimaux transitent

        for u in engine.units:
            if hasattr(u, 'network_id') and u.network_id == unite_id:
                
                # ---> AJOUT POUR LA MINIMAP ET L'IA : Mise à jour de la carte
                # 1. On retire l'unité de son ancienne position sur la carte
                if u.position in engine.game_map.map:
                    del engine.game_map.map[u.position]
                
                # 2. Mise à jour de ses statistiques réelles
                u.position = new_pos
                u.current_hp = new_hp
                
                # 3. On replace l'unité à ses nouvelles coordonnées sur la carte
                engine.game_map.map[new_pos] = u
                
                break