import sys
import os

# 1. On trouve le dossier parent (la racine du projet)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# 2. NOUVEAU : On force Python à se placer à la racine pour que les chemins "data/..." fonctionnent
os.chdir(parent_dir)

# 3. On ajoute au path
sys.path.append(parent_dir)

# Maintenant on peut importer le moteur
from battle.engine import Engine

# Remplacez "nom_du_scenario", "nom_ia_1" et "nom_ia_2" par les VRAIS noms 
# qui sont dans votre AI_REGISTRY et vos fichiers de scénarios.
if __name__ == "__main__":
    print("--- Démarrage Joueur ROUGE ---")
    moteur = Engine(
        scenario="156u_KCPL_210", # <-- METTEZ VOTRE SCENARIO ICI
        ia1="Strategus20",       # <-- METTEZ VOTRE IA ROUGE ICI
        ia2="Strategus20",       # <-- METTEZ VOTRE IA BLEUE ICI
        view_type=2, 
        local_team='R'         # <-- Ce PC calcule l'équipe Rouge
    )
    moteur.start()