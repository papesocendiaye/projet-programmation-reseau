from battle.map import Map
import time
import sys
import os

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

# --- Importations réseau (routeur C en partie_c/) ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from partie_c.client import IPCClient
    from partie_c.protocol import Message, ActionType
except ImportError:
    print("[!] Attention : client.py ou protocol.py introuvables. Le réseau sera désactivé.")
    IPCClient = None
    Message = None
    ActionType = None


# --- Constantes réseau / temporisation ---
HEARTBEAT_PERIOD_TURNS = 15        # ~4 Hz à 60 TPS (60 octets/msg, charge OK)
HELLO_PERIOD_S         = 2.0       # découverte de pair côté C
PEER_TIMEOUT_S         = 4.0       # tolérance Wi-Fi avant disparition
REQ_RETRY_S            = 0.3       # retransmission REQ_OWNERSHIP (perte UDP)
REQ_ABANDON_S          = 1.2       # abandon REQ_OWNERSHIP (pair planté)
DEATH_CLEANUP_S        = 3.0       # délai avant retrait visuel d'un mort
VICTORY_GRACE_TURNS    = 300       # 5 s pour la synchro réseau initiale
DEATH_SENTINEL         = -1000.0   # pos_x/pos_y == sentinelle => mort signalée


# =====================================================================
#  Helpers globaux
# =====================================================================
def fix_string(s):
    bad = set(' -_.,;:!?/\\|@#$%^&*()[]{}<>~`"\'')
    return ''.join(c.lower() for c in s if c not in bad)


def get_key():
    if os.name == 'nt':
        import msvcrt
        if not msvcrt.kbhit():
            return None
        try:
            ch = msvcrt.getch()
            if ch in (b'\x00', b'\xe0'):
                ch = msvcrt.getch()
            return ch.decode('utf-8', errors='ignore')
        except Exception:
            return None
    import select
    keys = ""
    try:
        fd = sys.stdin.fileno()
        while select.select([fd], [], [], 0)[0]:
            keys += os.read(fd, 1).decode('utf-8', errors='ignore')
    except Exception:
        return None
    return keys or None


def randomize_order(units):
    for i in range(len(units) - 1, 0, -1):
        j = randint(0, i)
        units[i], units[j] = units[j], units[i]


class _MockTarget:
    """Cible factice pour rejouer visuellement un tir distant (Projectile.arrow/lance)."""
    def __init__(self, pos):
        self.position = pos
        self.direction = (0, 0)
        self.speed = 0
        self.size = 1.0
        self.team = 'None'
        self.is_alive = True

    def take_damage(self, attacker):
        pass


class Engine:
    # =================================================================
    #  Cycle de vie
    # =================================================================
    def __init__(self, scenario, ia1, ia2, view_type, tournaments=False, local_team='R'):
        self.scenario_name = scenario
        self.ia1 = fix_string(ia1)
        self.ia2 = fix_string(ia2)
        self.view_type = view_type
        self.tournaments = tournaments
        self.local_team = local_team
        self.player_id = 1 if local_team == 'R' else 2
        self._init_state()
        self._init_timing()
        self._init_network()

    def _init_state(self):
        self.game_map = None
        self.units = []
        self.projectiles = []
        self.view = None
        self.is_running = False
        self.game_pause = False
        self.winner = None
        self.winner_state = "EN ATTENTE"
        self.current_turn = 0
        self.pressed_keys = set()
        self.unit_id_counter = 0
        self.spawn_queue = []
        self.dead_units_sync = set()
        self.history = {'turns': [], 'red_units': [], 'blue_units': []}
        self.initial_units_count = {'R': 0, 'B': 0}
        self.ia_thinking_time = {'R': 0.0, 'B': 0.0}

    def _init_timing(self):
        self.max_fps = 60
        self.min_fps = 10
        self.min_frame_delay = 1 / self.max_fps
        self.max_frame_delay = 1 / self.min_fps
        self.tps = 60
        self.turn_time_target = 1.0 / self.tps
        self.turn_time = 0
        self.turn_fps = 0
        self.real_tps = 0
        self.time_turn = 0
        self.max_turns = 40000
        self.spawn_interval = 0.15
        self.time_since_last_spawn = 0.0
        self.star_execution_time = None
        self.tab_game_tps = deque(maxlen=10)
        self.tab_tps_affichage = deque(maxlen=120)

    def _init_network(self):
        if not IPCClient:
            self.ipc = None
            return
        try:
            # Routeur C local : on écoute sur 5001, on émet vers 5000.
            self.ipc = IPCClient(port_ecoute=5001, port_c=5000)
            print("[RESEAU] IPC Local OK : J'écoute sur 5001 et j'envoie au C sur 5000")
        except Exception as e:
            print(f"[RESEAU] Erreur de connexion IPC : {e}")
            self.ipc = None

    def start(self):
        if self.tournaments:
            self.load_scenario()
            self.initialize_ai()
            self.initialize_units()
            self.is_running = True
            self.star_execution_time = time.time()
            randomize_order(self.units)
            self.game_loop()
            return self.end_battle()

        print("=== Starting Battle ===")
        old_settings = None
        if os.name != 'nt' and sys.stdin.isatty():
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        try:
            self.load_scenario()
            self.initialize_ai()
            if self.view_type > 0:
                self.initialize_view()
            self.is_running = True
            self.star_execution_time = time.time()
            self.game_loop()
        finally:
            if old_settings:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        return self.end_battle()

    def pause(self):  self.is_running = False
    def resume(self): self.is_running = True
    def stop(self):   self.is_running = False

    def load_scenario(self):
        if not self.tournaments:
            print(f"Loading scenario: {self.scenario_name}")
        self.game_map = Map()
        Map.load(self.game_map, self.scenario_name)
        # Purge des unités adverses chargées par le scénario : chaque PC ne garde
        # que sa propre armée, l'autre arrive par SPAWN réseau.
        for pos in [p for p, u in self.game_map.map.items()
                    if u and u.team != self.local_team]:
            self.game_map.map.pop(pos, None)
        if not self.tournaments:
            self.build_spawn_queue()

    def build_spawn_queue(self):
        from battle.scenario import Scenario
        _, scenario = Scenario().get_list_by_name(self.scenario_name)
        red, blue = [], []
        if "lanchester" in self.scenario_name:
            for x, y, t in scenario:
                if x < self.game_map.p // 2:
                    red.append((x, y, t, 'R'))
                else:
                    blue.append((x, y, t, 'B'))
        else:
            for x, y, t in scenario:
                red.append((x, y, t, 'R'))
                blue.append((self.game_map.p - x, y, t, 'B'))
        self.spawn_queue = []
        for i in range(max(len(red), len(blue))):
            if i < len(red):  self.spawn_queue.append(red[i])
            if i < len(blue): self.spawn_queue.append(blue[i])

    def initialize_units(self):
        for (x, y) in self.game_map.map:
            self.game_map.get_unit(x, y).direction = (0, 0)
            self.units.append(self.game_map.get_unit(x, y))

    def initialize_ai(self):
        if self.ia1 not in AI_REGISTRY: raise ValueError(f"IA '{self.ia1}' non reconnue.")
        if self.ia2 not in AI_REGISTRY: raise ValueError(f"IA '{self.ia2}' non reconnue.")
        self.ia1 = AI_REGISTRY[self.ia1]("R", self.game_map)
        self.ia2 = AI_REGISTRY[self.ia2]("B", self.game_map)
        self.ia1.initialize()
        self.ia2.initialize()
        if not self.tournaments:
            print(f"Initializing AIs: {self.ia1.name} vs {self.ia2.name}")

    def initialize_view(self):
        import visuals.terminal_view as term
        import visuals.gui_view as gui
        if self.view_type == 1:
            self.view = term.Terminal_view(self.game_map.p, self.game_map.q)
        elif self.view_type == 2:
            self.view = gui.GUI_view(self.game_map.p, self.game_map.q)

    def end_battle(self):
        if self.view == 1 and not self.tournaments:
            self.update_view()
        if not self.tournaments and "lanchester" in self.scenario_name.lower():
            self.rapport_lanchester()
        if not self.tournaments:
            print("\n=== Battle Ended ===")
            print(f"Total turns: {self.current_turn}")
            return None
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
            'winner_team': None,
        }

    # =================================================================
    #  Boucle principale
    # =================================================================
    def game_loop(self):
        view_frame_time = max(1 / 100, 2 / (self.max_fps + self.min_fps))
        self.turn_time_target = 1.0 / self.tps
        next_view_time = time.time()
        last_hello = 0.0
        while self.is_running:
            t0 = time.time()
            last_hello = self._pump_network(t0, last_hello)
            view_frame_time, next_view_time = self._run_one_tick(t0, view_frame_time, next_view_time)

    def _run_one_tick(self, t0, view_frame_time, next_view_time):
        if self.tournaments:
            self.process_turn()
            self.process_spawns()
            self.check_victory()
            self.current_turn += 1
            self.update_units(1 / 60)
            self.update_projectiles()
            dt = time.time() - t0
            if dt > 0:
                self.tab_game_tps.append(1.0 / dt)
            self.real_tps = mean(self.tab_game_tps) if self.tab_game_tps else 0
            return view_frame_time, next_view_time

        if self.game_pause:
            return self._tick_paused(t0, view_frame_time, next_view_time)

        # Tour normal
        if self.view_type > 1 and self.current_turn % 5 == 0:
            view_frame_time = self._adapt_timing(view_frame_time)
        self.process_turn()
        self.process_spawns()
        if self.view_type == 1:
            self.handle_input()
        if t0 >= next_view_time and self.view_type > 0:
            next_view_time = t0 + view_frame_time
            self.update_view()
        self.check_victory()
        self.current_turn += 1
        self.update_units(1 / 60)
        self.update_projectiles()
        self.turn_time = time.time() - t0
        if self.view and self.turn_time < self.turn_time_target:
            time.sleep(self.turn_time_target - self.turn_time)
        dt2 = time.time() - t0
        if dt2 != 0:
            self.tab_game_tps.append(1.0 / dt2)
            self.tab_tps_affichage.append(1.0 / dt2)
        self.real_tps = mean(self.tab_game_tps) if self.tab_game_tps else 0
        self.time_turn = time.time()
        return view_frame_time, next_view_time

    def _tick_paused(self, t0, view_frame_time, next_view_time):
        if self.view_type == 1:
            self.handle_input()
        if t0 >= next_view_time:
            next_view_time = t0 + view_frame_time
            if self.view_type > 0:
                self.update_view()
        dt = time.time() - t0
        if self.view and dt < self.turn_time_target:
            time.sleep(self.turn_time_target - dt)
        dt2 = time.time() - t0
        if dt2 != 0:
            self.tab_game_tps.append(1.0 / dt2)
        return view_frame_time, next_view_time

    def _adapt_timing(self, view_frame_time):
        tps = self.real_tps if self.real_tps else 60
        if self.tps <= 0:
            self.tps = 0
            perf = 1
        else:
            perf = tps / self.tps
        view_frame_time = max(min(view_frame_time / perf, self.max_frame_delay), self.min_frame_delay)
        self.turn_time_target = max(min(self.turn_time_target * perf, 1 / (self.tps + 3)), 1 / (self.tps + 30))
        view_frame_time = max(1 / tps, view_frame_time)
        self.turn_fps = 1 / view_frame_time
        return view_frame_time

    def _pump_network(self, t0, last_hello):
        if not self.ipc:
            return last_hello
        # HELLO périodique : sans ça un pair qui n'a pas découvert l'autre a un
        # lobby vide côté C => famine de cession de propriété.
        if t0 - last_hello > HELLO_PERIOD_S:
            self.ipc.send_action(Message(
                id_joueur=self.player_id, pos_x=0.0, pos_y=0.0, hp=0.0,
                action=ActionType.HELLO, timestamp=t0, target_id="HELLO",
            ))
            last_hello = t0
        for msg in self.ipc.get_pending_messages():
            self.apply_network_message(msg)
        # Disparition des pairs déconnectés (4 s de tolérance Wi-Fi)
        now = time.time()
        for u in [u for u in self.units
                  if u.team != self.local_team and hasattr(u, 'last_seen')
                  and now - u.last_seen > PEER_TIMEOUT_S]:
            print(f"[RESEAU] Timeout distant. Disparition complète de {u.unit_id}")
            u.is_alive = False
            if u in self.units:
                self.units.remove(u)
            self.game_map.remove_unit(u.position[0], u.position[1])
        return last_hello

    # =================================================================
    #  Tour de jeu
    # =================================================================
    def process_turn(self):
        red_alive = blue_alive = 0
        for unit in self.units:
            if not unit.is_alive:
                self._broadcast_death(unit)
                continue
            if unit.team == 'R': red_alive += 1
            elif unit.team == 'B': blue_alive += 1
            if unit.team == self.local_team:
                self._play_unit_turn(unit)
        self._cleanup_dead_units()
        if "lanchester" in self.scenario_name.lower() and self.current_turn % 10 == 0:
            self.history['turns'].append(self.current_turn)
            self.history['red_units'].append(red_alive)
            self.history['blue_units'].append(blue_alive)

    def _play_unit_turn(self, unit):
        old_pos = unit.position
        ia = self.ia1 if unit.team == 'R' else self.ia2
        ia.play_turn(unit, self.current_turn)

        # ACTION centralisée : si l'IA a déclenché une attaque sur une case
        # dont on n'a pas la propriété, Map.attack2 met l'unité en
        # "waiting_ownership". On envoie alors la demande de cession.
        if unit.state == "waiting_ownership" and unit.target:
            self._request_ownership(unit, unit.target)
        elif unit.state == "attacking" and unit.target:
            # Double sécurité : revérifier la propriété de la case cible.
            if self.try_action(unit, unit.target):
                self._send(ActionType.ATTACK, unit, pos=unit.target.position)
            else:
                self._request_ownership(unit, unit.target)

        # Heartbeat : on continue à émettre même en waiting_ownership pour
        # ne pas se faire timeout par le pair (4 s sans nouvelles).
        if self.ipc and (unit.position != old_pos
                         or self.current_turn % HEARTBEAT_PERIOD_TURNS == 0):
            self._send(ActionType.MOVE, unit)

    def _broadcast_death(self, unit):
        # Diffuser une seule fois la mort d'une unité que NOUS possédons (la
        # nôtre, ou une dont on a acquis la propriété réseau via ACK).
        we_own = (unit.team == self.local_team
                  or getattr(unit, 'network_owner', None) == self.player_id)
        if not (we_own and hasattr(unit, 'unit_id')):
            return
        if unit.unit_id in self.dead_units_sync:
            return
        self._send(ActionType.MOVE, unit, pos=(DEATH_SENTINEL, DEATH_SENTINEL), hp=0.0)
        self.dead_units_sync.add(unit.unit_id)
        unit.died_at = time.time()

    def _cleanup_dead_units(self):
        # Retrait visuel après DEATH_CLEANUP_S : laisse au pair le temps de
        # recevoir le MOVE de mort et au visuel de jouer la dernière frame.
        now = time.time()
        for u in [u for u in self.units
                  if not u.is_alive and getattr(u, 'died_at', None)
                  and now - u.died_at > DEATH_CLEANUP_S]:
            self.units.remove(u)
            for pos in [p for p, m in self.game_map.map.items() if m is u]:
                self.game_map.map.pop(pos, None)

    # =================================================================
    #  Spawns
    # =================================================================
    def process_spawns(self):
        if not self.spawn_queue:
            return
        self.time_since_last_spawn += 1.0 / 60.0
        while self.time_since_last_spawn >= self.spawn_interval and self.spawn_queue:
            self.time_since_last_spawn -= self.spawn_interval
            x, y, unit_type, team = self.spawn_queue.pop(0)
            # Plus de concurrence sauvage : on ne spawne QUE nos propres unités.
            if team != self.local_team:
                continue
            self.game_map.add_unit(x, y, unit_type, team)
            new_unit = self.game_map.get_unit(x, y)
            if not new_unit or new_unit in self.units:
                continue
            new_unit.direction = (0, 0)
            new_unit.unit_id = f"{team}_{unit_type}_{self.unit_id_counter}"
            new_unit.network_owner = self.player_id
            self.unit_id_counter += 1
            self.units.append(new_unit)
            self.ia1.initialize()
            self.ia2.initialize()
            self._send(ActionType.SPAWN, new_unit)

    # =================================================================
    #  ACTION centralisée — vérification de propriété réseau
    #  (réponse au boss : "tout état de mise à jour passe par la
    #   demande de propriété ; la méthode action retourne positif ou
    #   négatif selon que la propriété est transmise")
    # =================================================================
    def try_action(self, unit, target):
        """Vérifie la propriété réseau de la case cible.

        Retourne True (positif)  : propriété OK -> caller exécute l'action.
        Retourne False (négatif) : propriété absente -> caller renonce ce tour
                                   (le caller doit appeler _request_ownership
                                   pour déclencher la cession).
        """
        owner = self.game_map.cell_owner(*target.position)
        me = getattr(unit, 'network_owner', self.player_id)
        return owner is None or owner == me

    def _request_ownership(self, unit, target):
        """Sémaphore avec retry rapide (perte UDP) et abandon (pair planté)."""
        now = time.time()
        last = getattr(unit, 'req_sent_at', None)
        unit.target = target
        unit.state = "waiting_ownership"
        if last is None:
            print(f"[V2] {unit.unit_id} demande l'autorisation d'attaquer {target.unit_id}...")
            self._send_req(unit, target, now)
            return
        if now - last > REQ_ABANDON_S:
            print(f"[V2] Timeout REQ pour {unit.unit_id} (cible {target.unit_id}), abandon.")
            unit.state = "idle"
            unit.target = None
            unit.req_sent = False
            unit.req_sent_at = None
            return
        if now - last > REQ_RETRY_S:
            self._send_req(unit, target, now)

    def _send_req(self, unit, target, now):
        if self.ipc:
            self.ipc.send_action(Message(
                id_joueur=self.player_id, pos_x=0.0, pos_y=0.0, hp=0.0,
                action=ActionType.REQ_OWNERSHIP, timestamp=now,
                target_id=str(target.unit_id),
            ))
        unit.req_sent = True
        unit.req_sent_at = now

    # =================================================================
    #  Réseau — entrée (dispatch par ActionType)
    # =================================================================
    def apply_network_message(self, msg):
        if msg.action == ActionType.HELLO:
            return  # découverte de pair côté C, aucun effet sur la scène
        unit = self.find_unit_by_id(msg.target_id)
        # Cas spécial : SPAWN d'une unité inconnue -> on la crée légitimement.
        # C'est le SEUL chemin de création réseau (pas de "concurrence sauvage"
        # via MOVE/ATTACK pour des unit_id inconnus).
        if not unit and msg.action == ActionType.SPAWN:
            unit = self._spawn_remote_unit(msg)
            if not unit:
                return
        if not unit:
            return  # message orphelin pour un ID inconnu -> ignoré silencieusement
        # Sync continue des HP des unités distantes
        if getattr(unit, 'network_owner', self.player_id) != self.player_id and msg.hp > 0:
            unit.current_hp = msg.hp
        handler = self._NET_HANDLERS.get(msg.action)
        if handler:
            handler(self, unit, msg)

    def _spawn_remote_unit(self, msg):
        parts = msg.target_id.split('_')
        if len(parts) < 2:
            return None
        team, u_type = parts[0], parts[1]
        px, py = int(msg.pos_x), int(msg.pos_y)
        old_marge = self.game_map.marge
        self.game_map.marge = 0
        self.game_map.add_unit(px, py, u_type, team)
        self.game_map.marge = old_marge
        unit = self.game_map.get_unit(px, py)
        if not unit or unit in self.units:
            return unit
        print(f"[RESEAU] Spawn distant légitime : {msg.target_id}")
        unit.direction = (0, 0)
        unit.unit_id = msg.target_id
        unit.last_seen = time.time()
        unit.current_hp = msg.hp
        unit.network_owner = msg.id_joueur
        self.units.append(unit)
        self.ia1.initialize()
        self.ia2.initialize()
        # Handshake : on ré-annonce nos unités locales en SPAWN (et plus en
        # MOVE comme avant) car les MOVE pour ID inconnus sont désormais ignorés.
        if self.ipc:
            for local_u in self.units:
                if (local_u.team == self.local_team and local_u.is_alive
                        and hasattr(local_u, 'unit_id')):
                    self._send(ActionType.SPAWN, local_u)
        return unit

    def _on_move(self, unit, msg):
        # Mort signalée par sentinelle de position
        if msg.pos_x <= DEATH_SENTINEL and msg.pos_y <= DEATH_SENTINEL:
            print(f"[RESEAU] Mort confirmée de l'unité adverse : {msg.target_id}")
            unit.is_alive = False
            unit.current_hp = 0
            unit.state = "dead"
            self.game_map.remove_unit(unit.position[0], unit.position[1])
            if unit in self.units:
                self.units.remove(unit)
            return
        new_pos = (msg.pos_x, msg.pos_y)  # float pour rendu sub-pixel fluide
        if unit.position != new_pos:
            self.game_map.maj_unit_posi(unit, new_pos)
        unit.last_seen = time.time()

    def _on_spawn(self, unit, msg):
        # Re-spawn d'une unité morte connue : le pair a redémarré et réutilise
        # le même unit_id alors qu'on en avait gardé une trace.
        if not unit.is_alive:
            print(f"[RESEAU] Re-spawn de {msg.target_id} (restart du pair)")
            new_pos = (int(msg.pos_x), int(msg.pos_y))
            unit.is_alive = True
            unit.current_hp = msg.hp if msg.hp > 0 else getattr(unit, 'max_hp', 100)
            unit.state = "idle"
            unit.network_owner = msg.id_joueur
            unit.last_seen = time.time()
            unit.died_at = None
            self.dead_units_sync.discard(unit.unit_id)
            if unit.position != new_pos:
                self.game_map.maj_unit_posi(unit, new_pos)
            self.game_map.map[new_pos] = unit
            if unit not in self.units:
                self.units.append(unit)
            return
        # Sinon (unité déjà vivante connue) : MOVE classique
        self._on_move(unit, msg)

    def _on_attack(self, unit, msg):
        unit.last_seen = time.time()
        unit.state = "attacking"
        if unit.type not in ('C', 'S') or unit.time_until_next_attack > 0:
            return
        tx, ty = msg.pos_x, msg.pos_y
        ux, uy = unit.position
        # Anti-divbyzero dans Projectile.arrow / lance
        if abs(tx - ux) < 1e-6 and abs(ty - uy) < 1e-6:
            tx += 1.0
        self.game_map.fire_projectile(unit, _MockTarget((tx, ty)))
        unit.time_until_next_attack = unit.reload_time

    def _on_req_ownership(self, unit, msg):
        # Le pair demande la cession d'une de NOS unités.
        if getattr(unit, 'network_owner', self.player_id) != self.player_id:
            return
        print(f"[V2] Cession de la propriété réseau de {unit.unit_id} au joueur {msg.id_joueur}")
        unit.network_owner = msg.id_joueur
        self._send(ActionType.ACK_OWNERSHIP, unit)

    def _on_ack_ownership(self, unit, msg):
        # 'unit' = la VICTIME dont on vient d'acquérir la propriété.
        print(f"[V2] Propriété réseau acquise pour {unit.unit_id} ! (HP actuels: {msg.hp})")
        unit.network_owner = self.player_id
        unit.current_hp = msg.hp
        new_pos = (int(msg.pos_x), int(msg.pos_y))
        if unit.position != new_pos:
            self.game_map.maj_unit_posi(unit, new_pos)
        if msg.hp <= 0:
            unit.is_alive = False
            unit.current_hp = 0
            unit.state = "dead"
        # Débloque les attaquants locaux qui patientaient sur cette cible
        for atk in self.units:
            if (getattr(atk, 'state', None) == "waiting_ownership"
                    and getattr(atk, 'target', None) is unit):
                atk.req_sent = False
                atk.req_sent_at = None
                if msg.hp <= 0:
                    atk.target = None  # PDF §2.d : pas de riposte sur un mort
                atk.state = "idle"

    # Table de dispatch (peuplée en bas du fichier après définition des handlers)
    _NET_HANDLERS = {}

    # =================================================================
    #  Réseau — sortie (helper unique)
    # =================================================================
    def _send(self, action, unit, *, pos=None, hp=None):
        if not self.ipc:
            return
        px, py = pos if pos is not None else unit.position
        hp_val = hp if hp is not None else unit.current_hp
        self.ipc.send_action(Message(
            id_joueur=self.player_id,
            pos_x=px, pos_y=py, hp=hp_val,
            action=action,
            timestamp=time.time(),
            target_id=str(unit.unit_id),
        ))

    def find_unit_by_id(self, unit_id):
        for u in self.units:
            if getattr(u, 'unit_id', None) == unit_id:
                return u
        return None

    # =================================================================
    #  Vue & input
    # =================================================================
    def update_units(self, dt):
        for u in self.units:
            u.update(dt)

    def update_projectiles(self):
        self.game_map.update_projectiles()

    def change_view(self, view_type):
        self.view_type = view_type
        self.initialize_view()
        self.update_view()

    def update_view(self):
        # On passe self.units (source de vérité) en plus de la map : sinon les
        # unités partageant une tuile sont écrasées dans map.map et disparaissent.
        a = self.view.display(self.game_map, self.get_game_info(), self.units)
        if self.view_type != 2:
            return
        if a["change_view"]: self.change_view(a["change_view"])
        if a['pause']: self.game_pause = not self.game_pause
        if a["quit"]:
            self.is_running = False  # sortie propre avant pygame.quit()
            self.end_battle()
            return
        if a["quicksave"]: self.game_map.save_file(self.scenario_name, self.ia1.name, self.ia2.name)
        if a["quickload"]: self._quickload()
        if a["increase_speed"]: self.tps += 10
        if a["decrease_speed"]: self.tps -= 10
        if a["generate_rapport"]: self.rapport_in_game()

    def _quickload(self):
        self.stop()
        name = "autosave"
        if os.path.exists(f"data/savedata/{name}_engine_data.txt"):
            with open(f"data/savedata/{name}_engine_data.txt", "r") as f:
                line = f.read().split("\n")[0].split(',')
                scenario, ia1, ia2 = line[0], line[1], line[2]
        else:
            scenario, ia1, ia2 = "stest1", "major_daft", "major_daft"
            name = "stest1"
        print(f"[LOAD] Loading saved battle from: {name}_save")
        Engine(name, ia1, ia2, view_type=2, local_team=self.local_team).start()

    def handle_input(self):
        key_input = get_key()
        if key_input is None:
            self.pressed_keys.clear()
            return
        if key_input.startswith('\x1b'):
            mapping = {'\x1b[A': 'z', '\x1b[B': 's', '\x1b[D': 'q', '\x1b[C': 'd'}
            if key_input in mapping:
                key_input = mapping[key_input]
            else:
                return
        for char in key_input:
            key = 'tab' if char == '\t' else char.lower()
            if key in self.pressed_keys:
                continue
            self.pressed_keys.add(key)
            self._dispatch_key(key)

    def _dispatch_key(self, key):
        if key == 'z':   self.view.move(0, -1)
        elif key == 's': self.view.move(0, 1)
        elif key == 'q': self.view.move(-10, 0)
        elif key == 'd': self.view.move(10, 0)
        elif key == 'p': self.game_pause = not self.game_pause
        elif key == 'c': self.change_view(2)
        elif key == 'tab': self.rapport_in_game()
        elif key == 't': self.game_map.save_file(self.scenario_name, self.ia1.name, self.ia2.name)
        elif key == 'y': self._quickload()

    # =================================================================
    #  Stats / rapports
    # =================================================================
    def get_game_info(self):
        return {
            'turn': self.current_turn,
            'ia1': self.ia1.name,
            'ia2': self.ia2.name,
            'game_pause': self.game_pause,
            'units_ia1': len([u for u in self.units if u.team == 'R' and u.is_alive]),
            'units_ia2': len([u for u in self.units if u.team == 'B' and u.is_alive]),
            'target_tps': self.tps,
            'real_tps': mean(self.tab_tps_affichage) if len(self.tab_tps_affichage) > 0 else 0,
            'turn_fps': round(self.turn_fps),
            'time_from_start': f'{(time.time() - self.star_execution_time):.2f}s',
            'in_game_time': f'{(self.current_turn / 60):.2f}s',
            'performance': f'{round(self.real_tps * 100 / 60)}%',
            'time_delta': f'{((self.current_turn / 60) - (time.time() - self.star_execution_time)):.2f}s',
            'winner_status': getattr(self, 'winner_state', 'EN ATTENTE...'),
        }

    def check_victory(self):
        team1 = len([u for u in self.units if u.team == self.local_team and u.is_alive])
        team2 = len([u for u in self.units if u.team != self.local_team and u.is_alive])
        if self.current_turn <= VICTORY_GRACE_TURNS:
            return  # 5 s de grâce pour la synchro réseau initiale
        if team1 == 0 and team2 > 0:    new_state = "DEFAITE"
        elif team2 == 0 and team1 > 0:  new_state = "VICTOIRE"
        elif team1 > 0 and team2 > 0:   new_state = "COMBAT EN COURS"
        else:                           new_state = "EGALITE (ARENE VIDE)"
        if self.winner_state != new_state:
            print(f"\n[JEU] ---> ETAT DU MATCH : {new_state} <---")
        self.winner_state = new_state

    def rapport_lanchester(self):
        info = self.get_game_info()
        filename = f"lanchester_report_{int(time.time())}.html"
        if not self.history['turns'] or self.history['turns'][-1] != self.current_turn:
            r = len([u for u in self.units if u.team == 'R' and u.is_alive])
            b = len([u for u in self.units if u.team == 'B' and u.is_alive])
            self.history['turns'].append(self.current_turn)
            self.history['red_units'].append(r)
            self.history['blue_units'].append(b)
        report_data = {
            'scenario': self.scenario_name,
            'turn': self.current_turn,
            'ia1': info['ia1'], 'ia2': info['ia2'],
            'winner': self.winner_state,
            'history': self.history,
            'initial_red':  self.history['red_units'][0]  if self.history['red_units']  else 0,
            'initial_blue': self.history['blue_units'][0] if self.history['blue_units'] else 0,
            'final_red':    self.history['red_units'][-1] if self.history['red_units']  else 0,
            'final_blue':   self.history['blue_units'][-1] if self.history['blue_units'] else 0,
        }
        generate_report('lanchester', report_data, filename)

    def rapport_in_game(self):
        info = self.get_game_info()
        filename = f"game_report_{info['turn']}.html"
        teams_data = {}
        for code, name in {'R': 'Rouge', 'B': 'Bleue'}.items():
            team_units = [u for u in self.units if u.team == code]
            alive = [u for u in team_units if u.is_alive]
            total_hp = sum(u.current_hp for u in alive)
            max_hp = sum(u.max_hp for u in alive)
            types = {}
            for u in alive:
                t = types.setdefault(u.type, {'count': 0, 'hp': 0, 'max_hp': 0})
                t['count'] += 1
                t['hp'] += u.current_hp
                t['max_hp'] += u.max_hp
            types_stats = {t: {'count': s['count'],
                               'avg_hp': s['hp'] / s['count'],
                               'percent': s['hp'] / s['max_hp'] * 100}
                           for t, s in types.items()}
            teams_data[code] = {
                'name': name, 'alive_count': len(alive), 'total_count': len(team_units),
                'total_hp': total_hp, 'max_hp': max_hp,
                'hp_percent': (total_hp / max_hp * 100) if max_hp > 0 else 0,
                'types': types_stats,
            }
        units_list = [{
            'team_code': u.team, 'type': u.type, 'hp': u.current_hp, 'max_hp': u.max_hp,
            'hp_percent': (u.current_hp / u.max_hp * 100) if u.max_hp > 0 else 0,
            'pos_x': u.position[0], 'pos_y': u.position[1], 'is_alive': u.is_alive,
        } for u in self.units]
        report_data = {
            'turn': info['turn'], 'in_game_time': info['in_game_time'],
            'ia1': info['ia1'], 'ia2': info['ia2'],
            'performance': info['performance'], 'real_tps': info['real_tps'],
            'teams': teams_data, 'units': units_list,
        }
        generate_report('battle', report_data, filename)
        if self.view_type == 1:
            print("Appuyez sur Entrée pour reprendre...")
            input()


# Initialisation différée de la table de dispatch (méthodes définies plus haut).
# Stocker les fonctions brutes comme valeurs : on les appelle via handler(self, unit, msg).
if ActionType:
    Engine._NET_HANDLERS = {
        ActionType.MOVE:          Engine._on_move,
        ActionType.SPAWN:         Engine._on_spawn,
        ActionType.ATTACK:        Engine._on_attack,
        ActionType.REQ_OWNERSHIP: Engine._on_req_ownership,
        ActionType.ACK_OWNERSHIP: Engine._on_ack_ownership,
    }
