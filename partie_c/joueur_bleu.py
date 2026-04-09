from battle.engine import Engine

if __name__ == "__main__":
    print("--- Démarrage Joueur BLEU ---")
    moteur = Engine(
        scenario="lanchester", # <-- DOIT ETRE LE MÊME SCENARIO
        ia1="random_ia",       # <-- DOIT ETRE LA MÊME IA
        ia2="random_ia",       # <-- DOIT ETRE LA MÊME IA
        view_type=2, 
        local_team='B'         # <-- Ce PC calcule l'équipe Bleue
    )
    moteur.start()