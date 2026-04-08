"""
Point d'entrée principal du jeu
"""

import argparse
import sys
import os

from network_interface.client import IPCClient
from battle.engine import Engine
from tournaments.tournament_manager import TournamentManager
from battle.scenario import Scenario
from ia.registry import AI_REGISTRY
global tps

# 1. Initialisation standard du moteur AOE
engine = Engine("stest1", "major_daft", "major_daft", view_type=2)
engine.load_scenario() # 
engine.initialize_ai() # 
engine.initialize_units() #  - Remplit engine.units

# 2. Configuration de l'équipe locale
# Conseil : cela pourrait être un argument passé au script plus tard
MY_TEAM = 'R' 

# 3. Connexion au Hub C
ipc = IPCClient()
ipc.connect()

# 4. Annonce des unités au réseau (Objectif V1.1)
# On parcourt la liste des unités initialisées dans le moteur 
for i, unit in enumerate(engine.units):
    if unit.team == MY_TEAM: # 
        x, y = unit.position # 
        # Format du protocole : SPAWN:ID:TYPE:X:Y
        msg = f"SPAWN:{i}:{unit.type}:{x}:{y}"
        ipc.send_action(msg)

if not os.path.exists("data/scenario"):
    os.mkdir("data/scenario")
if not os.path.exists("data/lanchester"):
    os.mkdir("data/lanchester")
if not os.path.exists("data/save"):
    os.mkdir("data/save")
if not os.path.exists("data/savedata"):
    os.mkdir("data/savedata")

def help():
    print("Utilisation : battle <commande> [options]")
    print("battle run <scenario> <ia1> <ia2> / Lancer une bataille entre deux IA")
    print("battle load <save> / Charger une bataille ou un tournoi sauvegardé")
    print("battle tournament / Lancer un tournoi automatique")
    print("")
    
    print("Liste des scénarios disponibles :")
    scenarios, scenarios_lanchester, save, save_data = Scenario().list_scenarios()
    print(" Scénarios :")
    for s in scenarios:
        print(f"  - {s}")
    print("")
    print(" Scénarios Lanchester :")
    for s in scenarios_lanchester:
        print(f"  - {s}")
    print("")
    print(" Sauvegardes :")
    for s in save:
        print(f"  - {s}")
    print("")
    print(" Données sauvegardées :")
    for s in save_data:
        print(f"  - {s}")
    print("")
    
    print("Liste des IA disponibles :")
    for key in AI_REGISTRY.keys():
        print(f" - {key}")
    print("")
    
    print("Exemple de commandes :")
    print("python3 main.py battle run stest6 smartia  Major_DAFT")
    print("python3 main.py battle tournament")
    print("python3 main.py battle load stest1 (ou stest1_save)")

class BattleCLI:
    def __init__(self):
        parser = argparse.ArgumentParser(
            prog="battle",
            description="Battle simulation CLI — run matches, load saves, tournaments, and plot results."
        )
        subparsers = parser.add_subparsers(dest="command", required=True)

        # === battle run <scenario> <ia1> <ia2> [-t] [-d DATAFILE] ===
        run_parser = subparsers.add_parser("run", help="Launch a single battle between two ias.")
        run_parser.add_argument("scenario", help="Scenario name or file to use")
        run_parser.add_argument("ia1", help="Name of first ia")
        run_parser.add_argument("ia2", help="Name of second ia")
        run_parser.add_argument("-t", action="store_true", help="Launch terminal view instead of 2.5D")
        run_parser.add_argument("--no-terminal", action="store_true", help="Launch no view")

        run_parser.add_argument("-d", "--datafile", help="Write data output to this file (optional)")

        t = subparsers.add_parser("tournament", help="Lance un tournoi automatique")
        t.add_argument("--generals", nargs="+", default=["all"])
        t.add_argument("--scenarios", nargs="+", default=["all"])
        t.add_argument("--matches", type=int)
        t.add_argument("--out", default="tournament_report.html")
        t.add_argument("--scenario-dir", default="data/scenario")

        # === battle load <savefile> ===
        load_parser = subparsers.add_parser("load", help="Load a previously saved battle or tournament.")
        load_parser.add_argument("savefile", help="Path to saved battle file")
        load_parser.add_argument("-t", action="store_true", help="Launch terminal view instead of 2.5D")
        load_parser.add_argument("--no-terminal", action="store_true", help="Launch no view")

        load_parser.add_argument("-d", "--datafile", help="Write data output to this file (optional)")

        self.parser = parser

    ### === Command dispatch ===
    def run(self):
        """pour faire vos tests complets depuis la ligne de commande initiale,
        il vous suffit de modifier ce tableau dans le fichier mian,
        il agira comme si vous aviez tapper la ligne de commande qui est dedans"""

        if len(sys.argv) < 2:
            help()
            return

        else:
            sys.argv.pop(0)  # Retire le nom du script

        if sys.argv[1] == "run":
            scenario_path = f"data/scenario/{sys.argv[2]}.txt"
            lanchester_path = f"data/lanchester/{sys.argv[2]}.txt"
            if not os.path.exists(scenario_path) and not os.path.exists(lanchester_path):
                return print(f"Le scénario {sys.argv[2]} n'existe pas.")

        args = self.parser.parse_args()
        match args.command:
            case "run":
                self.cmd_run(args)
            case "load":
                self.cmd_load(args)
            case "tournament":
                self.cmd_tournament(args)

    # === Command implementations  ===
    def cmd_run(self, args):

        print(f"[RUN] Scenario: {args.scenario}")
        print(f"      ias: {args.ia1} vs {args.ia2}")
        if args.t:        print(f"Terminal view")
        if args.datafile:
            print(f"      Output data → {args.datafile}")
        if args.no_terminal:
            view_type = 0
        elif args.t:
            view_type = 1
        else:
            view_type = 2
        engine = Engine(args.scenario, args.ia1, args.ia2, view_type)
        engine.start()

    def cmd_load(self, args):
        name=args.savefile
        name=name[:-5] if name.endswith("_save") else name
        if os.path.exists(f"data/savedata/{name}_engine_data.txt"):
            with open(f"data/savedata/{name}_engine_data.txt", "r") as f:
                data = f.read().split("\n")
                line = data[0].split(',')
                scenario,ia1,ia2 = str(line[0]) ,str(line[1]),str(line[2])
        else:
            scenario,ia1,ia2 = "stest1","major_daft","major_daft"
            name="stest1"
            
        print(f"[LOAD] Loading saved battle from: {name}_save")
        print(f"      ias: {ia1} vs {ia2}")
        if args.t:        print(f"Terminal view")
        if args.datafile:
            print(f"      Output data → {args.datafile}")
        if args.no_terminal:
            view_type = 0
        elif args.t:
            view_type = 1
        else:
            view_type = 2
        engine = Engine(name, ia1, ia2, view_type)
        engine.start()

    def cmd_tournament(self, args):
        kwargs = {
            "out_file": args.out,
            "scenario_dir": args.scenario_dir,
        }

        if args.generals != ["all"]:
            kwargs["generals"] = args.generals

        if args.scenarios != ["all"]:
            kwargs["scenarios"] = args.scenarios

        if args.matches is not None:
            kwargs["matches_per_pair"] = args.matches

        TournamentManager(**kwargs)


if __name__ == "__main__":
    # sys.argv = [".","battle", "run", "stest2", "Major_DAFT", "Major_DAFT", "--no-terminal"]
    # sys.argv = [".","battle", "run", "stest2_lanchester", "Major_DAFT", "Major_DAFT"]
    # sys.argv = [".","battle", "run", "stest1_save", "Major_DAFT", "Major_DAFT"]
    # sys.argv = [".","battle", "tournament"]
    sys.argv = [".", "battle", "run", "100u_emix_150", "Major_DAFT", "strategus20"]
    #sys.argv = [".","battle", "load", "autosave"]

    BattleCLI().run()
