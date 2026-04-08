def traiter_message_reseau(msg, engine):
    data = msg.split(':')
    if not data: return
    
    cmd = data[0]
    if cmd == "UPDATE":
        unite_id = data[1]
        # Chercher l'unité dans engine.units et mettre à jour sa position/vie
        # Si elle n'existe pas, la créer (SPAWN sauvage) [cite: 160, 161]