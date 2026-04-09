"""
battle/net_sync.py
V1 - Synchronisation reseau best-effort (MAJ).
Envoie les changements locaux aux peers, applique les changements distants.
"""
import sys
import os

# Ajouter partie_c au path pour importer protocol et client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'partie_c'))

from protocol import Message, ActionType
from client import IPCClient

# Facteur d'echelle : positions float (0-150) -> int (0-15000)
SCALE = 100

# Mapping equipe <-> int
TEAM_TO_INT = {'R': 0, 'B': 1}
INT_TO_TEAM = {0: 'R', 1: 'B'}


class NetSync:
    """Synchroniseur snapshot-diff pour le moteur de bataille."""

    def __init__(self, engine):
        """
        engine: instance de Engine (acces a .units, .game_map, .find_unit_by_id)
        """
        self.engine = engine
        self.ipc = IPCClient()          # ports par defaut: ecoute 5001, envoie vers 5000
        self.prev_snapshot = {}         # unit_id -> (pos_x, pos_y, hp, alive)

    # ---------------------------------------------------------------
    #  ENVOI : comparer snapshot courant vs precedent, envoyer diffs
    # ---------------------------------------------------------------
    def send_updates(self):
        """Compare l'etat courant avec le snapshot precedent, envoie les diffs."""
        current = self._snapshot()

        for uid, (x, y, hp, alive, utype, team) in current.items():
            prev = self.prev_snapshot.get(uid)
            team_int = TEAM_TO_INT.get(team, 0)

            # --- SPAWN : unite nouvelle ---
            if prev is None:
                target = f"{uid}:{utype}"   # ex: "R_K_0:K"
                self._send(team_int, int(x * SCALE), int(y * SCALE),
                           ActionType.SPAWN, target)
                continue

            old_x, old_y, old_hp, old_alive, _, _ = prev

            # --- DEATH : etait vivant, maintenant mort ---
            if old_alive and not alive:
                self._send(team_int, int(x * SCALE), int(y * SCALE),
                           ActionType.DEATH, uid)
                continue

            # Unite deja morte, rien a envoyer
            if not alive:
                continue

            # --- MOVE : position changee ---
            if abs(x - old_x) > 0.005 or abs(y - old_y) > 0.005:
                self._send(team_int, int(x * SCALE), int(y * SCALE),
                           ActionType.MOVE, uid)

            # --- ATTACK (changement HP) ---
            if abs(hp - old_hp) > 0.01:
                self._send(team_int, int(hp * SCALE), 0,
                           ActionType.ATTACK, uid)

        # Sauvegarder le snapshot pour le prochain tour
        self.prev_snapshot = current

    # ---------------------------------------------------------------
    #  RECEPTION : lire les messages en attente, les appliquer
    # ---------------------------------------------------------------
    def receive_updates(self):
        """Lit tous les messages reseau en attente et les applique."""
        try:
            messages = self.ipc.get_pending_messages()
        except (ConnectionResetError, OSError):
            # Windows renvoie une erreur si le C relay n'est pas lance
            return
        for msg in messages:
            self._apply(msg)

    # ---------------------------------------------------------------
    #  Application d'un message recu
    # ---------------------------------------------------------------
    def _apply(self, msg):
        """Applique un Message recu a l'etat local."""
        engine = self.engine
        game_map = engine.game_map

        if msg.action == ActionType.SPAWN:
            self._apply_spawn(msg, engine, game_map)
        elif msg.action == ActionType.MOVE:
            self._apply_move(msg, engine, game_map)
        elif msg.action == ActionType.ATTACK:
            self._apply_attack(msg, engine)
        elif msg.action == ActionType.DEATH:
            self._apply_death(msg, engine)

    def _apply_spawn(self, msg, engine, game_map):
        """Creer une unite distante sur la carte locale."""
        # target_id format: "R_K_0:K"
        parts = msg.target_id.split(':')
        if len(parts) != 2:
            return
        uid, unit_type = parts[0], parts[1]

        # Ne pas dupliquer si deja presente
        if engine.find_unit_by_id(uid) is not None:
            return

        team = INT_TO_TEAM.get(msg.id_joueur, 'R')
        x = msg.pos_x / SCALE
        y = msg.pos_y / SCALE

        game_map.add_unit(x, y, unit_type, team)
        new_unit = game_map.get_unit(x, y)
        if new_unit is not None and new_unit not in engine.units:
            new_unit.unit_id = uid
            new_unit.direction = (0, 0)
            engine.units.append(new_unit)

    def _apply_move(self, msg, engine, game_map):
        """Mettre a jour la position d'une unite distante."""
        unit = engine.find_unit_by_id(msg.target_id)
        if unit is None or not unit.is_alive:
            return
        new_x = msg.pos_x / SCALE
        new_y = msg.pos_y / SCALE
        game_map.maj_unit_posi(unit, (new_x, new_y))

    def _apply_attack(self, msg, engine):
        """Mettre a jour les HP d'une unite (resultat de degats)."""
        unit = engine.find_unit_by_id(msg.target_id)
        if unit is None:
            return
        new_hp = msg.pos_x / SCALE
        unit.current_hp = new_hp
        if unit.current_hp <= 0:
            unit.current_hp = 0
            unit.is_alive = False
            unit.state = "dead"

    def _apply_death(self, msg, engine):
        """Marquer une unite distante comme morte."""
        unit = engine.find_unit_by_id(msg.target_id)
        if unit is None:
            return
        unit.current_hp = 0
        unit.is_alive = False
        unit.state = "dead"

    # ---------------------------------------------------------------
    #  Helpers internes
    # ---------------------------------------------------------------
    def _snapshot(self):
        """Retourne dict: unit_id -> (x, y, hp, alive, type, team)"""
        snap = {}
        for unit in self.engine.units:
            uid = getattr(unit, 'unit_id', None)
            if not uid:
                continue
            snap[uid] = (
                unit.position[0],
                unit.position[1],
                unit.current_hp,
                unit.is_alive,
                unit.type,
                unit.team,
            )
        return snap

    def _send(self, id_joueur, pos_x, pos_y, action, target_id):
        """Construit et envoie un Message via IPC."""
        msg = Message(id_joueur, pos_x, pos_y, action, target_id)
        self.ipc.send_action(msg)
