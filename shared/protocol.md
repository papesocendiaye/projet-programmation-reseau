Protocole de Communication (C/Python & Réseau P2P)
1. Règles Générales
    - Format : Texte clair (ASCII/UTF-8).
    - Délimiteur de champs : Les paramètres sont séparés par le caractère : (deux-points).
    - Délimiteur de fin de message : Chaque message DOIT impérativement se terminer par un saut de ligne \n. C'est vital pour préserver les limites des messages transmis via TCP.
    - Sens de communication : Ce protocole est symétrique. Il est utilisé à la fois pour l'IPC (Python <-> C) et pour le réseau (C <-> C).

2. Phase 1 : Mode "Best-Effort" (Sans garantie de cohérence)
L'objectif ici est de partager une scène en "temps réel" , en acceptant les décalages temporels dans la vision du monde.
    - SPAWN
        - Description : Un participant place un nouvel objet/personnage dans la scène.
        - Format : SPAWN:<ID_ENTITE>:<TYPE>:<X>:<Y>
        - Exemple : SPAWN:P1:ARCHER:15.5:20.0\n

    - UPDATE
        - Description : Une IA envoie une mise à jour immédiate lorsqu'elle modifie la scène (déplacement, perte de vie). La mise à jour modifie la scène distante.
        - Format : UPDATE:<ID_ENTITE>:<X>:<Y>:<SANTE>
        - Exemple : UPDATE:P1:16.0:20.0:90\n

    - INTERACT
        - Description : Une IA locale interagit avec les ressources d'une IA distante  (ex: attaque).
        - Format : INTERACT:<ID_ATTAQUANT>:<ID_CIBLE>:<TYPE_ACTION>
        - Exemple : INTERACT:P1:Pc3:ATTACK\n

3. Phase 2 : Cohérence et Propriété Réseau
Pour garantir la cohérence, chaque élément de la scène dispose d'un attribut de propriété réseau cessible. Une IA doit demander cette propriété avant toute action.

    - REQ_PROP (Request Property)
        - Description : Demande la propriété réseau d'une entité à son propriétaire actuel.
        - Format : REQ_PROP:<ID_ENTITE_CIBLE>:<ID_DEMANDEUR>
        - Exemple : REQ_PROP:Pc3:B\n

    - GIVE_PROP (Give Property)
        - Description : Le propriétaire actuel transmet la propriété et l'état cohérent de la ressource.
        - Format : GIVE_PROP:<ID_ENTITE>:<NOUVEAU_PROPRIETAIRE>:<ETAT_COMPLET>
        - Exemple : GIVE_PROP:Pc3:B:ALIVE_X10_Y20_HP50\n

    - DENY_PROP (Deny Property)
        - Description : Refus de transférer la propriété (ex: l'entité vient d'être atteinte mortellement et ne peut plus riposter ).
        - Format : DENY_PROP:<ID_ENTITE>:<RAISON>
        - Exemple : DENY_PROP:Pc3:DEAD\n