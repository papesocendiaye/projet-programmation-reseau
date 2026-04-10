#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "protocol.h"

#ifdef _WIN32
    #include <winsock2.h>
    #pragma comment(lib, "ws2_32.lib")
#else
    #include <unistd.h>
    #include <arpa/inet.h>
    #include <sys/select.h>
#endif

#define PORT_IA 5000      // Port pour l'IA Python locale
#define PORT_RESEAU 6000  // Port pour les autres nœuds P2P
#define MAX_PEERS 10

typedef struct {
    struct sockaddr_in addr;
    int active;
} Peer;

Peer lobby[MAX_PEERS]; 

// --- Gestion du carnet d'adresses ---
void add_peer(struct sockaddr_in new_addr) {
    for (int i = 0; i < MAX_PEERS; i++) {
        if (lobby[i].active && lobby[i].addr.sin_addr.s_addr == new_addr.sin_addr.s_addr) return;
        if (!lobby[i].active) {
            lobby[i].addr = new_addr;
            lobby[i].active = 1;
            printf("[P2P] Nouveau voisin ajouté : %s\n", inet_ntoa(new_addr.sin_addr));
            return;
        }
    }
}

int main(int argc, char *argv[]) {
#ifdef _WIN32
    WSADATA wsaData; WSAStartup(MAKEWORD(2, 2), &wsaData);
#endif

    int sock_ia = socket(AF_INET, SOCK_DGRAM, 0);
    int sock_reseau = socket(AF_INET, SOCK_DGRAM, 0);

    struct sockaddr_in addr_ia, addr_res, sender_addr;
    socklen_t addr_len = sizeof(sender_addr);
    char buffer[sizeof(Message)]; // Le buffer a maintenant la taille exacte du message binaire

    // Liaison socket IA (127.0.0.1:5000)
    memset(&addr_ia, 0, sizeof(addr_ia));
    addr_ia.sin_family = AF_INET;
    addr_ia.sin_addr.s_addr = inet_addr("127.0.0.1");
    addr_ia.sin_port = htons(PORT_IA);
    bind(sock_ia, (struct sockaddr*)&addr_ia, sizeof(addr_ia));

    // Liaison socket Réseau (0.0.0.0:6000)
    memset(&addr_res, 0, sizeof(addr_res));
    addr_res.sin_family = AF_INET;
    addr_res.sin_addr.s_addr = INADDR_ANY;
    addr_res.sin_port = htons(PORT_RESEAU);
    bind(sock_reseau, (struct sockaddr*)&addr_res, sizeof(addr_res));

    printf("Nœud P2P Version 2 (Binaire) actif.\n");
    printf("IA sur port %d, Réseau sur port %d\n", PORT_IA, PORT_RESEAU);

    // Connexion initiale si IP fournie
    if (argc > 1) {
        struct sockaddr_in first_peer;
        first_peer.sin_family = AF_INET;
        first_peer.sin_addr.s_addr = inet_addr(argv[1]);
        first_peer.sin_port = htons(PORT_RESEAU);
        
        Message h = {0, 0, 0, ACTION_HELLO, 0.0, "HELLO"};
        serialize_binary(&h, buffer);
        sendto(sock_reseau, buffer, sizeof(Message), 0, (struct sockaddr*)&first_peer, sizeof(first_peer));
        add_peer(first_peer);
    }

    fd_set readfds;
    while (1) {
        FD_ZERO(&readfds);
        FD_SET(sock_ia, &readfds);
        FD_SET(sock_reseau, &readfds);
        int max_fd = (sock_ia > sock_reseau) ? sock_ia : sock_reseau;

        select(max_fd + 1, &readfds, NULL, NULL, NULL);

        // --- CAS 1 : L'IA locale envoie un ordre ---
        if (FD_ISSET(sock_ia, &readfds)) {
            int len = recvfrom(sock_ia, buffer, sizeof(Message), 0, NULL, NULL);
            if (len == sizeof(Message)) {
                Message m_ia;
                deserialize_binary(buffer, &m_ia);
                printf("[IA] Action: %d | Time: %f\n", m_ia.action, m_ia.timestamp);

                // Broadcast aux voisins
                for (int i = 0; i < MAX_PEERS; i++) {
                    if (lobby[i].active) {
                        sendto(sock_reseau, buffer, sizeof(Message), 0, (struct sockaddr*)&lobby[i].addr, sizeof(lobby[i].addr));
                    }
                }
            }
        }

        // --- CAS 2 : Message venant du réseau ---
        if (FD_ISSET(sock_reseau, &readfds)) {
            int len = recvfrom(sock_reseau, buffer, sizeof(Message), 0, (struct sockaddr*)&sender_addr, &addr_len);
            if (len == sizeof(Message)) {
                Message m_res;
                deserialize_binary(buffer, &m_res);

                if (m_res.action == ACTION_HELLO) {
                    add_peer(sender_addr);
                } else {
                    // Transmettre l'action binaire à l'IA locale pour mise à jour
                    sendto(sock_ia, buffer, sizeof(Message), 0, (struct sockaddr*)&addr_ia, sizeof(addr_ia));
                }
            }
        }
    }

    return 0;
}