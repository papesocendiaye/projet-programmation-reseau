import time
from network_interface.client import IPCClient
from battle.engine import Engine
from utils.network_logic import traiter_message_reseau

# --- CONFIGURATION ---
MY_TEAM = 'R'  
MY_PREFIX = "ELIEZER_" 

# 1. Initialisation du moteur
engine = Engine("stest1", "major_daft", "major_daft", view_type=2)
engine.load_scenario()



# AJOUT : On purge aussi le dictionnaire de la carte !
positions_a_effacer = []
for pos, u in engine.game_map.map.items():
    if u is not None and u.team != MY_TEAM:
        positions_a_effacer.append(pos)

for pos in positions_a_effacer:
    del engine.game_map.map[pos]

engine.initialize_ai()
engine.initialize_units()

# 2. Isolement de l'équipe locale
# On supprime l'équipe adverse du jeu local. 
# On ne les verra que quand le réseau enverra leurs SPAWN !
engine.units = [u for u in engine.units if u.team == MY_TEAM]

# 3. Amorçage manuel du système (remplace engine.start())
engine.initialize_view()                  # Crée la fenêtre graphique
engine.star_execution_time = time.time()  # Évite le crash dans get_game_info()
engine.is_running = True                  # Indique au moteur que la partie commence

# 4. Connexion au réseau
ipc = IPCClient()
ipc.connect()

# 5. Annonce (SPAWN initial)
for i, unit in enumerate(engine.units):
    if unit.team == MY_TEAM:
        unit.network_id = f"{MY_PREFIX}{i}"
        ipc.send_action(f"SPAWN:{unit.network_id}:{unit.type}:{unit.position[0]}:{unit.position[1]}")

print("V1 Répartie Lancée ! En attente d'autres IAs...")

# --- BOUCLE PRINCIPALE ---
try:
    while True:
        # A. RÉCEPTION (Fantômes)
        for msg in ipc.get_pending_messages():
            traiter_message_reseau(msg, engine)

        # On force l'interface graphique à afficher les nouvelles unités réseau
        if engine.view:
            engine.view.all_units = engine.units

        engine.ia1.update_perception()
        engine.ia2.update_perception()
        
        # B. LOGIQUE LOCALE
        engine.run_one_step()

        # C. ÉMISSION (Mouvements)
        for unit in engine.units:
            if unit.team == MY_TEAM:
                x, y = unit.position
                ipc.send_action(f"UPDATE:{unit.network_id}:{x}:{y}:{unit.current_hp}")
        
        time.sleep(0.01)
except KeyboardInterrupt:
    print("Arrêt de la bataille.")