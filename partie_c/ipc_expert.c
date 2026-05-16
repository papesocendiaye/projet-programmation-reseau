#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include "protocol_expert.h"

#define PORT_BASE 5000

int main(int argc, char *argv[]) {
    int sockfd;
    struct sockaddr_in servaddr, cliaddr;
    MessageExpert msg;

    // 1. Création de la socket UDP (Sans serveur central) [cite: 7, 147]
    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Échec création socket");
        exit(EXIT_FAILURE);
    }

    memset(&servaddr, 0, sizeof(servaddr));
    servaddr.sin_family = AF_INET;
    servaddr.sin_addr.s_addr = INADDR_ANY;
    servaddr.sin_port = htons(argc > 1 ? atoi(argv[1]) : PORT_BASE);

    // 2. Liaison (Bind) [cite: 145]
    if (bind(sockfd, (const struct sockaddr *)&servaddr, sizeof(servaddr)) < 0) {
        perror("Échec bind");
        exit(EXIT_FAILURE);
    }

    printf("[SYSTEME ABIDA] Nœud réseau actif sur le port %d\n", ntohs(servaddr.sin_port));

    // 3. Boucle de réception (Gestion de la cohérence V2)
    while (1) {
        socklen_t len = sizeof(cliaddr);
        int n = recvfrom(sockfd, &msg, sizeof(MessageExpert), 0, (struct sockaddr *)&cliaddr, &len);
        
        if (n > 0) {
            // Vérification de l'intégrité (Sécurité)
            uint16_t expected_checksum = (msg.id_joueur + msg.x + msg.y + msg.action_type) % 65535;
            if (msg.checksum != expected_checksum) {
                printf("[ALERTE SECURITE] Reçu CHK: %u, Attendu: %u .\n");
                continue;
            }

            // Logique de découverte sauvage (HELLO) [cite: 157, 160]
            if (msg.action_type == ACTION_HELLO) {
                printf("[RESEAU] Nouveau pair détecté (Joueur %d)\n", msg.player_id);
            }
            
            // Logique de propriété réseau (REQ_OWNERSHIP) [cite: 165]
            if (msg.action_type == ACTION_REQ_OWNERSHIP) {
                printf("[COHERENCE] Requête de propriété pour l'unité %s reçue (TS: %f)\n", msg.unit_id, msg.timestamp);
                // Ici, le code C transmettrait l'info au Python via IPC (Mémoire partagée ou Pipe) [cite: 146, 147]
            }
        }
    }

    return 0;
}