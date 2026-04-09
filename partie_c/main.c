#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "protocol.h"
#ifdef _WIN32
    typedef int socklen_t;
#endif

#ifdef _WIN32
    #include <winsock2.h>
    #pragma comment(lib, "ws2_32.lib")
#else
    #include <unistd.h>
    #include <arpa/inet.h>
    #include <sys/select.h>
#endif

#define PORT_IA 5000      // Port pour parler au Python local
#define PORT_RESEAU 6000  // Port pour parler aux autres joueurs
#define MAX_PEERS 10

typedef struct {
    struct sockaddr_in addr;
    int active;
} Peer;

Peer lobby[MAX_PEERS]; // Carnet d'adresses

// Ajoute une IP au carnet si elle n'y est pas déjà
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

    struct sockaddr_in addr_ia, addr_res;
    char buffer[MAX_BUFFER_SIZE];

    // Liaison socket locale (IA)
    addr_ia.sin_family = AF_INET;
    addr_ia.sin_addr.s_addr = inet_addr("127.0.0.1");
    addr_ia.sin_port = htons(PORT_IA);
    bind(sock_ia, (struct sockaddr*)&addr_ia, sizeof(addr_ia));

    // Liaison socket publique (Réseau)
    addr_res.sin_family = AF_INET;
    addr_res.sin_addr.s_addr = INADDR_ANY;
    addr_res.sin_port = htons(PORT_RESEAU);
    bind(sock_reseau, (struct sockaddr*)&addr_res, sizeof(addr_res));

    printf("Nœud P2P actif. IA sur 5000, Réseau sur 6000.\n");

    if (argc > 1) {
        struct sockaddr_in first_peer;
        first_peer.sin_family = AF_INET;
        first_peer.sin_addr.s_addr = inet_addr(argv[1]);
        first_peer.sin_port = htons(PORT_RESEAU);
        
        Message h = {0, 0, 0, ACTION_HELLO, "HELLO"};
        serialize_message(&h, buffer, sizeof(buffer));
        sendto(sock_reseau, buffer, strlen(buffer), 0, (struct sockaddr*)&first_peer, sizeof(first_peer));
        add_peer(first_peer);
    }

    // --- NOUVEAU : Variables pour mémoriser l'adresse du script Python ---
    struct sockaddr_in python_client_addr;
    int python_connected = 0;

    fd_set readfds;
    while (1) {
        FD_ZERO(&readfds);
        FD_SET(sock_ia, &readfds);
        FD_SET(sock_reseau, &readfds);
        int max_fd = (sock_ia > sock_reseau) ? sock_ia : sock_reseau;

        select(max_fd + 1, &readfds, NULL, NULL, NULL);

        // CAS 1 : L'IA locale envoie un ordre -> On le broadcast au réseau
        if (FD_ISSET(sock_ia, &readfds)) {
            struct sockaddr_in sender_addr;
            socklen_t sender_len = sizeof(sender_addr);
            int len = recvfrom(sock_ia, buffer, MAX_BUFFER_SIZE-1, 0, (struct sockaddr*)&sender_addr, &sender_len);
            
            // On mémorise dynamiquement le port du Python (5001 ou 5002)
            python_client_addr = sender_addr;
            python_connected = 1;

            for (int i=0; i<MAX_PEERS; i++) {
                if (lobby[i].active) sendto(sock_reseau, buffer, len, 0, (struct sockaddr*)&lobby[i].addr, sizeof(lobby[i].addr));
            }
        }

        // CAS 2 : Message du réseau -> On l'ajoute au carnet ou on l'envoie à l'IA
        if (FD_ISSET(sock_reseau, &readfds)) {
            struct sockaddr_in sender_addr;
            socklen_t addr_len = sizeof(sender_addr);
            int len = recvfrom(sock_reseau, buffer, MAX_BUFFER_SIZE-1, 0, (struct sockaddr*)&sender_addr, &addr_len);
            buffer[len] = '\0';
            Message m;
            if (deserialize_message(buffer, &m)) {
                if (m.action == ACTION_HELLO) {
                    add_peer(sender_addr);
                } else if (python_connected) {
                    // CORRECTION : On envoie au Python, pas à nous-même !
                    sendto(sock_ia, buffer, len, 0, (struct sockaddr*)&python_client_addr, sizeof(python_client_addr));
                }
            }
        }
    }
    return 0;
}