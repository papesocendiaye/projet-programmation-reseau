from battle.engine import Engine

# Remplacez "nom_du_scenario", "nom_ia_1" et "nom_ia_2" par les VRAIS noms 
# qui sont dans votre AI_REGISTRY et vos fichiers de scénarios.
if __name__ == "__main__":
    print("--- Démarrage Joueur ROUGE ---")
    moteur = Engine(
        scenario="lanchester", # <-- METTEZ VOTRE SCENARIO ICI
        ia1="random_ia",       # <-- METTEZ VOTRE IA ROUGE ICI
        ia2="random_ia",       # <-- METTEZ VOTRE IA BLEUE ICI
        view_type=2, 
        local_team='R'         # <-- Ce PC calcule l'équipe Rouge
    )
    moteur.start()