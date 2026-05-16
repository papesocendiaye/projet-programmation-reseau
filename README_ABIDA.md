OBJECTIF STRATEGIQUE
Réimplémenter les poles Liaison et Cohérence en améliorant la robustesse binaire, le determinisme et la sécurité des échanges conformément au cahier des charges

    A.Pôle Liaison & Protocole (Efficacité & Sécurité JSON)
        1.Sérialisation Binaire (C/Python)
            -Action : Remplacer le format texte par des struct C compactes
            -Idée: Réduction de la bande passante (messages de 56 octets fixes)
            -Code: Je vais utiliser uint32_t pour éviter les problèmes d'architecture entre 32 et 64 bits

        2.Couche de Sécurité & Intégrité (Format JSON/Checksum)
            -Ce qui va changer: Avant l'envoi, encapsuler les données critiques dans un objet JSON léger ou ajouter un num magique
            - Sécu: Vérifier que le message provient bien d'un client "MedievAI" pour éviter les injections de fausses coordonnées


    B.Pôle Cohérence (Algorithme de Propriété Réseau) (pour qu'une unité n'ait pas deux etats en meme temps)
        1.Protocole de Propriété (REQ/ACK)
            - L'IA demande la propriété via `ACTION_REQ_OWNERSHIP
            - Le possesseur actuel cède la propriété et envoie l'état (`ACK_OWNERSHIP`)
            -Le demandeur valide l'action **uniquement** à la réception

        2.NetworkManager (Python)
            -Création d'une classe `NetworkManager` qui maintient une table `local_ownership`
            -Blocage des entrées utilisateur (clics) si la propriété n'est pas acquise.



    C.Tests & Mesures (Pour la note finale)
        -Test sur la latence: je vais voir combien de temps entre REQ et ACK
        -Test sur la concurrence: Simuler deux clics simultanés sur deux instances WSL/VM pour ma version
        -enfin on va analyser le traffic: avec `tcpdump` pour la réduc des tailles des messages
