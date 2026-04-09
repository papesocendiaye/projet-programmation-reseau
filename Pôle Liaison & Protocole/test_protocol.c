#include <stdio.h>
#include <string.h>
#include "protocol.h"
// On part du principe que tu as mis le code du TCPBuffer et 
// les structures Message / ActionType juste au-dessus ici.

int main() {
    printf("--- DEBUT DU CRASH-TEST C ---\n");

    // 1. Initialisation de notre buffer
    TCPBuffer tcp_buf;
    init_buffer(&tcp_buf);
    char msg_extrait[100]; // Pour stocker le résultat

    // 2. SIMULATION DE COUPURE
    printf("\n[Réseau] On reçoit un bout de message...\n");
    add_data(&tcp_buf, "1|120|250|", 10); // Il manque la fin !

    if (get_next_message(&tcp_buf, msg_extrait)) {
        printf("-> Erreur: Il a trouvé un message alors qu'il n'y a pas de '\\n' !\n");
    } else {
        printf("-> Correct: Aucun message complet trouve.\n");
    }

    // 3. SIMULATION DE SPAM (La fin arrive, avec deux autres messages)
    printf("\n[Réseau] On reçoit la suite, avec des messages collés...\n");
    add_data(&tcp_buf, "0|None\n2|50|50|1|Pb1\n3|300|300|2|Pc", 35);
    add_data(&tcp_buf, "3\n", 2); // On rajoute le petit bout qui manquait au 3eme

    printf("\n--- EXTRACTION DES MESSAGES ---\n");
    // On boucle tant qu'on trouve des '\n'
    while (get_next_message(&tcp_buf, msg_extrait)) {
        printf("\nMessage brut extrait : %s\n", msg_extrait);

        // 4. On teste la désérialisation (sscanf)
        Message msg_dest;
        if (deserialize_message(msg_extrait, &msg_dest)) {
            printf("Succès ! Objet C recréé : Joueur %d en (%d, %d)\n", 
                   msg_dest.id_joueur, msg_dest.pos_x, msg_dest.pos_y);
        } else {
            printf("Erreur de désérialisation (sscanf a échoué).\n");
        }
    }

    return 0;
}