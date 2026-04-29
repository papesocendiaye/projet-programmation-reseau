from battle.map import Map
import time
import sys, os

if os.name != 'nt':
    import termios
    import tty
else:
    termios = None
    tty = None
from collections import deque
from random import randint
from numpy import mean

from ia.registry import AI_REGISTRY
from reports.reporter import generate_report 

### IMPORTATIONS POUR LE RÉSEAU ###
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from partie_c.client import IPCClient
    from partie_c.protocol import Message, ActionType
except ImportError:
    print("[!] Attention : client.py ou protocol.py introuvables. Le réseau sera désactivé.")
    IPCClient, Message, ActionType = None, None, None
#############################################

def fix_string(string):
    str_void = ""
    bad_chars = [' ', '-', '_', '.', ',', ';', ':', '!', '?', '/', '\\', '|', '@', '#', '$', '%', '^', '&', '*', '(', ')', '[', ']', '{', '}', '<', '>', '~', '`', '"', "'"]
    for char in string:
        if char in bad_chars:
            continue
        str_void += char.lower()
    return str_void


def get_key():
    if os.name == 'nt':
        import msvcrt
        if msvcrt.kbhit():
            try:
                ch = msvcrt.getch()
                if ch in (b'\x00', b'\xe0'):
                    ch = msvcrt.getch()
                return ch.decode('utf-8', errors='ignore')
            except:
                return None
        return None
    else:
        import select
        keys = ""
        try:
            fd = sys.stdin.fileno()
            while select.select([fd], [], [], 0)[0]:
                keys += os.read(fd, 1).decode('utf-8', errors='ignore')
        except:
            return None
        if keys:
            return keys
        return None


def randomize_order(units):
    for i in range(len(units) - 1, 0, -1):
        j = randint(0, i)
        units[i], units[j] = units[j], units[i]


class Engine:
    def __init__(self, scenario, ia1, ia2, view_type, tournaments=False, local_team='R'):

        self.scenario_name = scenario
        self.ia1 = fix_string(ia1)
        self.ia2 = fix_string(ia2)

        self.game_map = None
        self.units = []
        self.projectiles = []
        self.game_pause = False
        self.current_turn = 0
        self.is_running = False
        self.winner = None
        self.view = None
        self.pressed_keys = set()
        self.real_tps = 0
        self.tournaments = tournaments
        self.tab_game_tps = deque(maxlen=10)
        self.tab_tps_affichage = deque(maxlen=120)

        self.star_execution_time = None
        self.ia_thinking_time = {'R': 0.0, 'B': 0.0}
        self.initial_units_count = {'R': 0, 'B': 0}
        self.history = {'turns': [], 'red_units': [], 'blue_units': []}

        self.view_type = view_type
        self.max_fps = 60
        self.min_fps = 10 
        self.min_frame_delay = 1 / self.max_fps 
        self.max_frame_delay = 1 / self.min_fps
        self.tps = 60 
        self.turn_time_target = 1.0 / self.tps
        self.star_execution_time = None
        self.turn_time = 0

        self.max_turns = 40000
        self.turn_fps = 0
        self.time_turn = 0
        self.units = []
        
        self.spawn_queue = []
        self.spawn_interval = 0.15 
        self.time_since_last_spawn = 0.0
        self.unit_id_counter = 0

       ### Initialisation IPC & Sécurités ###
        self.local_team = local_team # 'R' ou 'B'
        self.player_id = 1 if local_team == 'R' else 2
        self.dead_units_sync = set() # Pour ne pas spammer la mort d'une unité
        self.winner_state = "EN ATTENTE" # Gère l'affichage victoire continue
        
        if IPCClient:
            try:
                # --- CORRECTION DU BUG DE L'AVEUGLE ---
                # Les deux PC écoutent sur le port 5001 (le port visé par le routeur C)
                port_ecoute = 5001 
                
                # Les deux Python envoient à leur programme C respectif (qui écoute sur 5000)
                port_cible = 5000 
                
                self.ipc = IPCClient(port_ecoute=port_ecoute, port_c=port_cible)
                print(f"[RESEAU] IPC Local OK : J'écoute sur {port_ecoute} et j'envoie au C sur {port_cible}")
                # ------------------------------------------------------------
                
            except Exception as e:
                print(f"[RESEAU] Erreur de connexion IPC : {e}")
                self.ipc = None
        else:
            self.ipc = None
        ####################################

    def initialize_units(self):
        for (x,y) in self.game_map.map:
            self.game_map.get_unit(x,y).direction = (0,0)
            self.units.append(self.game_map.get_unit(x,y))

    def load_scenario(self):
        if not self.tournaments: print(f"Loading scenario: {self.scenario_name}")
        self.game_map = Map()
    
        Map.load(self.game_map, self.scenario_name)
        
        # --- CORRECTIF 1 : PURGE DE L'ARMÉE ADVERSE AU CHARGEMENT ---
        # On retire de la grille de la carte les unités qui ne sont pas de notre équipe
        unites_a_purger = []
        for pos, unit in self.game_map.map.items():
            if unit and unit.team != self.local_team:
                unites_a_purger.append(pos)
                
        for pos in unites_a_purger:
            self.game_map.map.pop(pos, None)
        # -------------------------------------------------------------

        if not self.tournaments: 
           self.build_spawn_queue()

    def build_spawn_queue(self):
        from battle.scenario import Scenario
        _, scenario = Scenario().get_list_by_name(self.scenario_name)

        red_units = []
        blue_units = []

        if "lanchester" in self.scenario_name:
            for x, y, unit_type in scenario:
                if x < self.game_map.p // 2:
                    red_units.append((x, y, unit_type, 'R'))
                else:
                    blue_units.append((x, y, unit_type, 'B'))
        else:
            for x, y, unit_type in scenario:
                red_units.append((x, y, unit_type, 'R'))
                blue_units.append((self.game_map.p - x, y, unit_type, 'B'))

        self.spawn_queue = []
        max_len = max(len(red_units), len(blue_units))
        for i in range(max_len):
            if i < len(red_units):
                self.spawn_queue.append(red_units[i])
            if i < len(blue_units):
                self.spawn_queue.append(blue_units[i])

    def process_spawns(self):
        if not self.spawn_queue:
            return
        self.time_since_last_spawn += 1.0 / 60.0
        while self.time_since_last_spawn >= self.spawn_interval and self.spawn_queue:
            self.time_since_last_spawn -= self.spawn_interval
            x, y, unit_type, team = self.spawn_queue.pop(0)
            
            # --- CONCURRENCE SAUVAGE : On ne fait apparaitre QUE nos unités ---
            if team != self.local_team:
                continue
            # ------------------------------------------------------------------

            self.game_map.add_unit(x, y, unit_type, team)
            new_unit = self.game_map.get_unit(x, y)
            
            if new_unit and new_unit not in self.units:
                new_unit.direction = (0, 0)
                new_unit.unit_id = f"{team}_{unit_type}_{self.unit_id_counter}"
                
                # --- NOUVEAU V2 : On prend la propriété réseau de nos soldats ! ---
                new_unit.network_owner = self.player_id
                # ------------------------------------------------------------------
                
                self.unit_id_counter += 1
                self.units.append(new_unit)
                self.ia1.initialize()
                self.ia2.initialize()
                
                ### ANNONCE SPAWN (Mise à jour Format V2) ###
                if self.ipc and team == self.local_team:
                    msg = Message(
                        id_joueur=self.player_id,
                        pos_x=x,
                        pos_y=y,
                        hp=new_unit.current_hp,       # <-- Ajout des HP
                        action=ActionType.SPAWN,
                        timestamp=time.time(),        # <-- Ajout du timestamp
                        target_id=new_unit.unit_id
                    )
                    self.ipc.send_action(msg)
                ##############################################

    def find_unit_by_id(self, unit_id):
        for unit in self.units:
            if getattr(unit, 'unit_id', None) == unit_id:
                return unit
        return None

    def apply_network_message(self, msg):
        """Applique les actions distantes, la propriété réseau V2 et convertit les floats pour la map"""
        unit = self.find_unit_by_id(msg.target_id)
        
        # 1. CONCURRENCE SAUVAGE : On reçoit un soldat inconnu ? On le crée direct !
        if not unit and msg.pos_x != -1000:
            parts = msg.target_id.split('_')
            team = parts[0] if len(parts) > 0 else 'B'
            u_type = parts[1] if len(parts) > 1 else 'unknown'
            
            # Forçage des float en INT pour l'affichage graphique Pygame
            pos_x_int = int(msg.pos_x)
            pos_y_int = int(msg.pos_y)
            
            old_marge = self.game_map.marge
            self.game_map.marge = 0 
            self.game_map.add_unit(pos_x_int, pos_y_int, u_type, team)
            self.game_map.marge = old_marge 

            unit = self.game_map.get_unit(pos_x_int, pos_y_int)
            
            if unit and unit not in self.units:
                print(f"[RESEAU] ⚠️ Joueur distant détecté ! Apparition sauvage de {msg.target_id}")
                unit.direction = (0, 0)
                unit.unit_id = msg.target_id
                unit.last_seen = time.time()
                unit.current_hp = msg.hp 
                
                # Le créateur est le propriétaire réseau par défaut
                unit.network_owner = msg.id_joueur 
                
                self.units.append(unit)
                
                self.ia1.initialize()
                self.ia2.initialize()
                
                # --- LE HANDSHAKE ---
                if self.ipc:
                    for local_u in self.units:
                        if local_u.team == self.local_team and local_u.is_alive and hasattr(local_u, 'unit_id'):
                            ans_msg = Message(
                                id_joueur=self.player_id, 
                                pos_x=local_u.position[0], 
                                pos_y=local_u.position[1], 
                                hp=local_u.current_hp,
                                action=ActionType.MOVE, 
                                timestamp=time.time(),
                                target_id=str(local_u.unit_id)
                            )
                            self.ipc.send_action(ans_msg)

        # 2. Application des actions sur l'unité :
        if unit:
            # Synchronisation continue des HP si on n'est pas le propriétaire
            if getattr(unit, 'network_owner', self.player_id) != self.player_id and msg.hp > 0:
                unit.current_hp = msg.hp

            if msg.action == ActionType.MOVE or msg.action == ActionType.SPAWN:
                if msg.pos_x <= -1000.0 and msg.pos_y <= -1000.0:
                    print(f"[RESEAU] Mort confirmée de l'unité adverse : {msg.target_id}")
                    unit.is_alive = False
                    unit.current_hp = 0
                    unit.state = "dead"
                else:
                    nouvelle_pos = (int(msg.pos_x), int(msg.pos_y)) # INT ici aussi !
                    if unit.position != nouvelle_pos:
                        self.game_map.maj_unit_posi(unit, nouvelle_pos)
                    unit.last_seen = time.time()
                    
            elif msg.action == ActionType.ATTACK:
                unit.last_seen = time.time()
                unit.state = "attacking"
                if unit.type in ['C', 'S'] and unit.time_until_next_attack <= 0:
                    class MockTarget:
                        def __init__(self, pos):
                            self.position = pos
                            self.direction = (0, 0)
                            self.speed = 0
                            self.size = 1.0          
                            self.team = 'None'       
                            self.is_alive = True     
                        def take_damage(self, attacker):
                            pass 
                    
                    # 1. On DÉFINIT bien tx et ty ici :
                    tx = int(msg.pos_x)
                    ty = int(msg.pos_y)
                    ux = int(unit.position[0])
                    uy = int(unit.position[1])
                    
                    # 2. On applique la sécurité anti-crash :
                    if tx == ux and ty == uy:
                        tx += 1 
                        
                    # 3. On tire en utilisant tx et ty (qui existent bien maintenant !)
                    self.game_map.fire_projectile(unit, MockTarget((tx, ty)))
                    unit.time_until_next_attack = unit.reload_time
            # --- PROTOCOLE OWNERSHIP V2 ---
            elif msg.action == ActionType.REQ_OWNERSHIP:
                if getattr(unit, 'network_owner', self.player_id) == self.player_id:
                    print(f"[V2] Cession de la propriété réseau de {unit.unit_id} au joueur {msg.id_joueur}")
                    unit.network_owner = msg.id_joueur
                    
                    if self.ipc:
                        ack_msg = Message(
                            id_joueur=self.player_id,
                            pos_x=unit.position[0],
                            pos_y=unit.position[1],
                            hp=unit.current_hp,
                            action=ActionType.ACK_OWNERSHIP,
                            timestamp=time.time(),
                            target_id=unit.unit_id
                        )
                        self.ipc.send_action(ack_msg)
                        
            elif msg.action == ActionType.ACK_OWNERSHIP:
                # 'unit' = la VICTIME dont on vient d'acquérir la propriété réseau.
                print(f"[V2] Propriété réseau acquise pour {unit.unit_id} ! (HP actuels: {msg.hp})")
                unit.network_owner = self.player_id
                unit.current_hp = msg.hp
                nouvelle_pos = (int(msg.pos_x), int(msg.pos_y)) # INT ici aussi !
                if unit.position != nouvelle_pos:
                    self.game_map.maj_unit_posi(unit, nouvelle_pos)

                if msg.hp <= 0:
                    # Cible déjà morte côté pair : on propage le décès localement
                    unit.is_alive = False
                    unit.current_hp = 0
                    unit.state = "dead"

                # Sortie de "waiting_ownership" : on débloque l'attaquant local qui
                # patientait. Sans ce reset il reste figé indéfiniment et le combat
                # ne démarre jamais (apparait comme un crash côté joueur).
                for attacker in self.units:
                    if (getattr(attacker, 'state', None) == "waiting_ownership"
                            and getattr(attacker, 'target', None) is unit):
                        attacker.req_sent = False
                        attacker.req_sent_at = None
                        if msg.hp <= 0:
                            # Cohérence PDF §2.d : pas de riposte sur un mort
                            attacker.target = None
                        attacker.state = "idle"

    def initialize_ai(self):
        if self.ia1 not in AI_REGISTRY: raise ValueError(f"IA '{self.ia1}' non reconnue.")
        if self.ia2 not in AI_REGISTRY: raise ValueError(f"IA '{self.ia2}' non reconnue.") 
        
        self.ia1 = AI_REGISTRY[self.ia1]("R", self.game_map)
        self.ia2 = AI_REGISTRY[self.ia2]("B", self.game_map)

        self.ia1.initialize()
        self.ia2.initialize()
        if not self.tournaments: print(f"Initializing AIs: {self.ia1.name} vs {self.ia2.name}")
    
    def start(self):
        if not self.tournaments:
            print("=== Starting Battle ===")
            old_settings = None
            if os.name != 'nt' and sys.stdin.isatty():
                old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())

            try:
                self.load_scenario()
                self.initialize_ai()

                if (not self.tournaments) or self.view_type > 0:
                    self.initialize_view()

                self.is_running = True
                self.star_execution_time = time.time()

                self.game_loop()
            finally:
                if old_settings:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            return self.end_battle()
            
        if self.tournaments:
            self.load_scenario()
            self.initialize_ai()
            self.initialize_units()
            self.is_running = True
            self.star_execution_time = time.time()
            randomize_order(self.units)
            self.game_loop()
            return self.end_battle()
        else:
            print('problème')

    def game_loop(self):
        view_frame_time = max(1 / 100, 2 / (self.max_fps + self.min_fps)) 
        self.turn_time_target = 1.0 / self.tps 
        max_turn_time = self.turn_time_target

        next_view_time = time.time()

        while self.is_running:
            turn_start = time.time()

            ### LECTURE RESEAU ET GESTION DECONNEXION ###
            if self.ipc:
                messages = self.ipc.get_pending_messages()
                for msg in messages:
                    self.apply_network_message(msg)
                    
               # 3. Disparition absolue des joueurs déconnectés
                temps_actuel = time.time()
                unites_a_supprimer = []
                
                for u in self.units:
                    if u.team != self.local_team and hasattr(u, 'last_seen'):
                        # ---> CORRECTIF : On passe à 4.0 secondes de tolérance pour le Wi-Fi
                        if temps_actuel - u.last_seen > 4.0:
                            print(f"[RESEAU] Timeout distant. Disparition complète de {u.unit_id}")
                            unites_a_supprimer.append(u)
                            
                for u in unites_a_supprimer:
                    u.is_alive = False
                    if u in self.units:
                        self.units.remove(u)
                    self.game_map.remove_unit(u.position[0], u.position[1])
                ##############################################

            if self.tournaments:
                self.process_turn()
                self.process_spawns()
                self.check_victory()
                self.current_turn += 1
                self.update_units(1 / 60)
                self.update_projectiles()
                turn_time = time.time() - turn_start
                if turn_time > 0:
                    self.tab_game_tps.append((1.0 / turn_time))
                self.real_tps = (sum(self.tab_game_tps) / len(self.tab_game_tps)) if self.tab_game_tps else 0
            else:
                if not self.game_pause:
                    if self.view_type > 1 and self.current_turn % 5 == 0:
                        if self.real_tps == 0: tps =60 
                        else: tps = self.real_tps
                        if self.tps <= 0: 
                            self.tps =0
                            perf =1
                        else: perf = tps / (self.tps) 
                        
                        view_frame_time= max(min(( view_frame_time / perf), self.max_frame_delay), self.min_frame_delay)
                        self.turn_time_target = max(min(( self.turn_time_target * perf), 1/(self.tps+3)), 1/(self.tps+30))
                        view_frame_time =max( 1/tps , view_frame_time) 
                        self.turn_fps = 1 / view_frame_time
                        max_turn_time = self.turn_time_target 

                    self.process_turn()
                    self.process_spawns()
                    if self.view_type == 1:
                        self.handle_input()
                    if turn_start >= next_view_time and self.view_type > 0:
                        next_view_time = turn_start + view_frame_time
                        self.update_view()
                        
                    self.check_victory()
                    self.current_turn += 1
                    self.update_units(1 / 60)
                    self.update_projectiles()
                    
                    self.turn_time = time.time() - turn_start
                    if self.view and self.turn_time < max_turn_time:
                        time.sleep(max_turn_time - self.turn_time)
                    turn_time_plusp = time.time() - turn_start
                    if turn_time_plusp != 0:
                        self.tab_game_tps.append((1.0 / turn_time_plusp))
                        self.tab_tps_affichage.append(1.0 / turn_time_plusp)
                    self.real_tps = (sum(self.tab_game_tps) / len(self.tab_game_tps)) if self.tab_game_tps else 0
                    self.time_turn = time.time()

                else:
                    if self.view_type == 1: self.handle_input()
                    if turn_start >= next_view_time:
                        next_view_time = turn_start + view_frame_time
                        if self.view_type > 0:
                            self.update_view()
                    turn_time = time.time() - turn_start
                    if self.view and turn_time < max_turn_time:
                        time.sleep(max_turn_time - turn_time)
                    turn_time_plusp = time.time() - turn_start
                    if turn_time_plusp != 0:
                        self.tab_game_tps.append((1.0 / turn_time_plusp))


    def update_units(self,time_per_tick):
        for unit in self.units:
            unit.update(time_per_tick)

    def update_projectiles(self):
            self.game_map.update_projectiles()

    def handle_input(self):
        key_input = get_key()
        if key_input is None:
            self.pressed_keys.clear()
            return
        if key_input.startswith('\x1b'):
            mapping = {'\x1b[A': 'z', '\x1b[B': 's', '\x1b[D': 'q', '\x1b[C': 'd'}
            if key_input in mapping:
                key_input = mapping[key_input]
            else: return

        for char in key_input:
            key = char.lower()
            if key == '\t': key = 'tab'
            if key in self.pressed_keys: continue
            self.pressed_keys.add(key)

            if key == 'z': self.view.move(0, -1)
            elif key == 's': self.view.move(0, 1)
            elif key == 'q': self.view.move(-10, 0)
            elif key == 'd': self.view.move(10, 0)
            elif key == 'p': self.game_pause = not self.game_pause
            elif key == 'c': self.change_view(2)
            elif key == 'tab': self.rapport_in_game()
            elif key == 't': self.game_map.save_file(self.scenario_name, self.ia1.name, self.ia2.name)
            elif key == 'y':
                self.stop()
                name = "autosave"
                name = name[:-5] if name.endswith("_save") else name
                if os.path.exists(f"data/savedata/{name}_engine_data.txt"):
                    with open(f"data/savedata/{name}_engine_data.txt", "r") as f:
                        data = f.read().split("\n")
                        line = data[0].split(',')
                        scenario, ia1, ia2 = str(line[0]), str(line[1]), str(line[2])
                else:
                    scenario, ia1, ia2 = "stest1", "major_daft", "major_daft"
                    name = "stest1"

                print(f"[LOAD] Loading saved battle from: {name}_save")
                view_type = 2
                engine = Engine(name, ia1, ia2, view_type, local_team=self.local_team)
                engine.start()

    ### Emission de Tirs et de Mort ###
    def process_turn(self):
        import time # Juste au cas où ce n'est pas importé en haut
        red_alive = 0
        blue_alive = 0
        for unit in self.units:
            if not unit.is_alive:
                # 4. Transmettre la mort UNE SEULE FOIS aux adversaires
                if unit.team == self.local_team and hasattr(unit, 'unit_id'):
                    if unit.unit_id not in self.dead_units_sync:
                        if self.ipc:
                            # --- MISE A JOUR FORMAT V2 ---
                            msg = Message(
                                id_joueur=self.player_id, 
                                pos_x=-1000.0, 
                                pos_y=-1000.0, 
                                hp=0.0,
                                action=ActionType.MOVE, 
                                timestamp=time.time(),
                                target_id=str(unit.unit_id)
                            )
                            self.ipc.send_action(msg)
                        self.dead_units_sync.add(unit.unit_id)
                continue
                
            if unit.team == 'R': red_alive += 1
            elif unit.team == 'B': blue_alive += 1

            if unit.team == self.local_team:
                old_pos = unit.position

                if unit.team == 'R': self.ia1.play_turn(unit, self.current_turn)
                elif unit.team == 'B': self.ia2.play_turn(unit, self.current_turn)

                # ============================================================
                # --- V2 : GESTION DE L'ATTENTE DE PROPRIÉTÉ RÉSEAU ---
                # Verrou "sémaphore binaire" : timestamp `req_sent_at` qui sert
                # à la fois de retry (perte UDP) et d'abandon (pair planté).
                # ============================================================
                if unit.state == "waiting_ownership" and unit.target:
                    now = time.time()
                    last_req = getattr(unit, 'req_sent_at', None)

                    if last_req is None:
                        print(f"[V2] {unit.unit_id} demande l'autorisation d'attaquer {unit.target.unit_id}...")
                        send_req = True
                    elif now - last_req > 2.0:
                        # Pair injoignable depuis 2 s : on libère l'unité
                        print(f"[V2] Timeout REQ pour {unit.unit_id} (cible {unit.target.unit_id}), abandon.")
                        unit.state = "idle"
                        unit.target = None
                        unit.req_sent = False
                        unit.req_sent_at = None
                        continue
                    elif now - last_req > 0.5:
                        # Possible perte UDP : on retransmet
                        send_req = True
                    else:
                        send_req = False

                    if send_req:
                        if self.ipc:
                            msg = Message(
                                id_joueur=self.player_id,
                                pos_x=0.0,
                                pos_y=0.0,
                                hp=0.0,
                                action=ActionType.REQ_OWNERSHIP,
                                timestamp=now,
                                target_id=str(unit.target.unit_id)
                            )
                            self.ipc.send_action(msg)
                        unit.req_sent = True
                        unit.req_sent_at = now
                    continue # L'unité passe son tour en attendant la réponse du réseau
                # ============================================================

                if self.ipc:
                    if unit.state == "attacking" and unit.target:
                        # --- MISE A JOUR FORMAT V2 ---
                        msg = Message(
                            id_joueur=self.player_id,
                            pos_x=unit.target.position[0],
                            pos_y=unit.target.position[1],
                            hp=unit.current_hp,
                            action=ActionType.ATTACK,
                            timestamp=time.time(),
                            target_id=str(unit.unit_id)
                        )
                        self.ipc.send_action(msg)
                        
                    # --- CORRECTIF 3 : LE BATTEMENT DE COEUR (HEARTBEAT) ---
                    elif unit.position != old_pos or self.current_turn % 30 == 0:
                        # --- MISE A JOUR FORMAT V2 ---
                        msg = Message(
                            id_joueur=self.player_id, 
                            pos_x=unit.position[0], 
                            pos_y=unit.position[1], 
                            hp=unit.current_hp,
                            action=ActionType.MOVE, 
                            timestamp=time.time(),
                            target_id=str(unit.unit_id)
                        )
                        self.ipc.send_action(msg)
                    # -------------------------------------------------------

        if "lanchester" in self.scenario_name.lower() and self.current_turn % 10 == 0:
            self.history['turns'].append(self.current_turn)
            self.history['red_units'].append(red_alive)
            self.history['blue_units'].append(blue_alive)

    def change_view(self, view_type):
        self.view_type = view_type
        self.initialize_view()
        self.update_view()
        
    def initialize_view(self):
        import visuals.terminal_view as term
        import visuals.gui_view as gui
        match self.view_type:
            case 0: pass
            case 1: self.view = term.Terminal_view(self.game_map.p, self.game_map.q)
            case 2: self.view = gui.GUI_view(self.game_map.p, self.game_map.q)

    def update_view(self):
        a = self.view.display(self.game_map, self.get_game_info())
        if self.view_type == 2:
            if a["change_view"]: self.change_view(a["change_view"])
            if a['pause']: self.game_pause = not self.game_pause
            if a["quit"]: self.end_battle()
            if a["quicksave"]: self.game_map.save_file(self.scenario_name, self.ia1.name, self.ia2.name)
            if a["quickload"]:
                self.stop()
                name="autosave"
                name=name[:-5] if name.endswith("_save") else name
                if os.path.exists(f"data/savedata/{name}_engine_data.txt"):
                    with open(f"data/savedata/{name}_engine_data.txt", "r") as f:
                        data = f.read().split("\n")
                        line = data[0].split(',')
                        scenario,ia1,ia2 = str(line[0]) ,str(line[1]),str(line[2])
                else:
                    scenario,ia1,ia2 = "stest1","major_daft","major_daft"
                    name="stest1"
                view_type = 2
                engine = Engine(name, ia1, ia2, view_type, local_team=self.local_team)
                engine.start()

            if a["increase_speed"]: self.tps += 10
            if a["decrease_speed"]: self.tps -= 10
            if a["generate_rapport"]: self.rapport_in_game()

    def get_game_info(self):
        return {
            'turn': self.current_turn,
            'ia1': self.ia1.name,
            'ia2': self.ia2.name,
            'game_pause': self.game_pause,
            'units_ia1': len([u for u in self.units if u.team == 'R' and u.is_alive]),
            'units_ia2': len([u for u in self.units if u.team == 'B' and u.is_alive]),
            'target_tps' : self.tps,
            'real_tps': mean(self.tab_tps_affichage) if len(self.tab_tps_affichage) > 0 else 0,
            'turn_fps': round(self.turn_fps),
            'time_from_start': f'{(time.time() - self.star_execution_time):.2f}s',
            'in_game_time': f'{(self.current_turn / 60):.2f}s',
            'performance': f'{round(self.real_tps*100 / 60)}%',
            'time_delta': f'{((self.current_turn / 60)-(time.time() - self.star_execution_time)):.2f}s',
            'winner_status': getattr(self, 'winner_state', 'EN ATTENTE...'), # EXPORT POUR GUI
        }

    ### On définit l'Etat du Jeu (Gagnant/Perdant) sans l'arrêter ! ###
    def check_victory(self):
        units_team1 = len([u for u in self.units if u.team == self.local_team and u.is_alive])
        units_team2 = len([u for u in self.units if u.team != self.local_team and u.is_alive])

        if self.current_turn > 60: # Laisse 1 sec aux joueurs pour apparaître
            if units_team1 == 0 and units_team2 > 0:
                nouvel_etat = "DEFAITE"
            elif units_team2 == 0 and units_team1 > 0:
                nouvel_etat = "VICTOIRE"
            elif units_team1 > 0 and units_team2 > 0:
                nouvel_etat = "COMBAT EN COURS"
            else:
                nouvel_etat = "EGALITE (ARENE VIDE)"
                
            # Si le statut change, on prévient le terminal
            if hasattr(self, 'winner_state') and self.winner_state != nouvel_etat:
                print(f"\n[JEU] ---> ETAT DU MATCH : {nouvel_etat} <---")
            self.winner_state = nouvel_etat
    ##############################################################################

    def end_battle(self):
        if self.view == 1 and not self.tournaments: self.update_view()
        if not self.tournaments and "lanchester" in self.scenario_name.lower():
            self.rapport_lanchester()

        if not self.tournaments:
            print("\n=== Battle Ended ===")
            print(f"Total turns: {self.current_turn}")
            return None
        else:
            return {
                'turn': self.current_turn,
                'scenario': str(self.scenario_name),
                'ia1': str(self.ia1.name),
                'ia2': str(self.ia2.name),
                'units_ia1': len([u for u in self.units if u.team == 'R' and u.is_alive]),
                'units_ia2': len([u for u in self.units if u.team == 'B' and u.is_alive]),
                'real_tps': self.real_tps,
                'time_from_start': time.time() - self.star_execution_time,
                'winner_ia': "draw",
                'winner_team': None
            }

    def pause(self): self.is_running = False
    def resume(self): self.is_running = True
    def stop(self): self.is_running = False

    def rapport_lanchester(self):
        info = self.get_game_info()
        filename = f"lanchester_report_{int(time.time())}.html"
        if not self.history['turns'] or self.history['turns'][-1] != self.current_turn:
            red_alive = len([u for u in self.units if u.team == 'R' and u.is_alive])
            blue_alive = len([u for u in self.units if u.team == 'B' and u.is_alive])
            self.history['turns'].append(self.current_turn)
            self.history['red_units'].append(red_alive)
            self.history['blue_units'].append(blue_alive)

        report_data = {
            'scenario': self.scenario_name,
            'turn': self.current_turn,
            'ia1': info['ia1'],
            'ia2': info['ia2'],
            'winner': self.winner_state,
            'history': self.history,
            'initial_red': self.history['red_units'][0] if self.history['red_units'] else 0,
            'initial_blue': self.history['blue_units'][0] if self.history['blue_units'] else 0,
            'final_red': self.history['red_units'][-1] if self.history['red_units'] else 0,
            'final_blue': self.history['blue_units'][-1] if self.history['blue_units'] else 0,
        }
        generate_report('lanchester', report_data, filename)

    def rapport_in_game(self):
        info = self.get_game_info()
        filename = f"game_report_{info['turn']}.html"

        teams_data = {}
        teams = {'R': 'Rouge', 'B': 'Bleue'}
        for team_code, team_name in teams.items():
            team_units = [u for u in self.units if u.team == team_code]
            alive_units = [u for u in team_units if u.is_alive]

            total_hp = sum(u.current_hp for u in alive_units)
            max_hp = sum(u.max_hp for u in alive_units)
            hp_percent = (total_hp / max_hp * 100) if max_hp > 0 else 0

            unit_types = {}
            for u in alive_units:
                if u.type not in unit_types: unit_types[u.type] = {'count': 0, 'hp': 0, 'max_hp': 0}
                unit_types[u.type]['count'] += 1
                unit_types[u.type]['hp'] += u.current_hp
                unit_types[u.type]['max_hp'] += u.max_hp

            types_stats = {}
            for u_type, stats in unit_types.items():
                types_stats[u_type] = {
                    'count': stats['count'],
                    'avg_hp': stats['hp'] / stats['count'],
                    'percent': (stats['hp'] / stats['max_hp'] * 100)
                }

            teams_data[team_code] = {
                'name': team_name, 'alive_count': len(alive_units), 'total_count': len(team_units),
                'total_hp': total_hp, 'max_hp': max_hp, 'hp_percent': hp_percent, 'types': types_stats
            }

        units_list = []
        for u in self.units:
            units_list.append({
                'team_code': u.team, 'type': u.type, 'hp': u.current_hp, 'max_hp': u.max_hp,
                'hp_percent': (u.current_hp / u.max_hp * 100) if u.max_hp > 0 else 0,
                'pos_x': u.position[0], 'pos_y': u.position[1], 'is_alive': u.is_alive
            })

        report_data = {
            'turn': info['turn'], 'in_game_time': info['in_game_time'], 'ia1': info['ia1'], 'ia2': info['ia2'],
            'performance': info['performance'], 'real_tps': info['real_tps'], 'teams': teams_data, 'units': units_list
        }
        generate_report('battle', report_data, filename)
        if self.view_type == 1:
            print("Appuyez sur Entrée pour reprendre...")
            input()