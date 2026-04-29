#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "protocol.h"

#ifdef _WIN32
    #include <winsock2.h>
    typedef int socklen_t;
    #pragma comment(lib, "ws2_32.lib")
#else
    #include <unistd.h>
    #include <arpa/inet.h>
    #include <sys/select.h>
#endif

#define PORT_IA 5000      
#define PORT_RESEAU 6000  
#define MAX_PEERS 10

typedef struct {
    struct sockaddr_in addr;
    int active;
} Peer;

Peer lobby[MAX_PEERS];

void add_peer(struct sockaddr_in addr) {
    for (int i = 0; i < MAX_PEERS; i++) {
        if (lobby[i].active && lobby[i].addr.sin_addr.s_addr == addr.sin_addr.s_addr) return;
        if (!lobby[i].active) {
            lobby[i].addr = addr;
            lobby[i].active = 1;
            printf("[P2P] Nouveau voisin ajouté : %s\n", inet_ntoa(addr.sin_addr));
            return;
        }
    }
}

int main(int argc, char *argv[]) {
#ifdef _WIN32
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        printf("Erreur fatale : Impossible d'initialiser Winsock.\n");
        return 1;
    }
#endif

    int sock_ia = socket(AF_INET, SOCK_DGRAM, 0);
    int sock_res = socket(AF_INET, SOCK_DGRAM, 0);

    struct sockaddr_in addr_ia = {0}, addr_res = {0}, sender_addr;
    socklen_t addr_len = sizeof(sender_addr);
    char buffer[sizeof(Message) + 10]; 

    addr_ia.sin_family = AF_INET;
    addr_ia.sin_port = htons(PORT_IA);
    addr_ia.sin_addr.s_addr = inet_addr("127.0.0.1");
    if (bind(sock_ia, (struct sockaddr*)&addr_ia, sizeof(addr_ia)) < 0) {
        printf("❌ ERREUR FATALE : Impossible d'ouvrir le port %d (Peut-etre deja utilise ?)\n", PORT_IA);
        return 1;
    }

    addr_res.sin_family = AF_INET;
    addr_res.sin_port = htons(PORT_RESEAU);
    addr_res.sin_addr.s_addr = htonl(INADDR_ANY);
    if (bind(sock_res, (struct sockaddr*)&addr_res, sizeof(addr_res)) < 0) {
        printf("❌ ERREUR FATALE : Impossible d'ouvrir le port %d\n", PORT_RESEAU);
        return 1;
    }

    printf("--- Nœud V2 (Binaire + Timestamp + HP) actif ---\n");

    if (argc > 1) {
        struct sockaddr_in p = {0};
        p.sin_family = AF_INET;
        p.sin_port = htons(PORT_RESEAU);
        p.sin_addr.s_addr = inet_addr(argv[1]);
        Message h = {0, 0, 0, 0, ACTION_HELLO, 0.0, "HELLO"};
        serialize_binary(&h, buffer);
        sendto(sock_res, buffer, sizeof(Message), 0, (struct sockaddr*)&p, sizeof(p));
        add_peer(p);
    }

    fd_set reads;
    while(1) {
        FD_ZERO(&reads);
        FD_SET(sock_ia, &reads);
        FD_SET(sock_res, &reads);
        int max_fd = (sock_ia > sock_res) ? sock_ia : sock_res;

        select(max_fd + 1, &reads, NULL, NULL, NULL);

        if (FD_ISSET(sock_ia, &reads)) {
            int len = recvfrom(sock_ia, buffer, sizeof(buffer), 0, NULL, NULL);
            if (len == sizeof(Message)) {
                Message m;
                deserialize_binary(buffer, &m);
                for(int i=0; i<MAX_PEERS; i++) {
                    if(lobby[i].active) 
                        sendto(sock_res, buffer, sizeof(Message), 0, (struct sockaddr*)&lobby[i].addr, sizeof(lobby[i].addr));
                }
            }
        }

        if (FD_ISSET(sock_res, &reads)) {
            int len = recvfrom(sock_res, buffer, sizeof(buffer), 0, (struct sockaddr*)&sender_addr, &addr_len);
            if (len == sizeof(Message)) {
                Message m;
                deserialize_binary(buffer, &m);
                if (m.action == ACTION_HELLO) {
                    add_peer(sender_addr);
                } else {
                    // ---> LE CORRECTIF EST ICI : on renvoie au Python sur son port 5001 <---
                    struct sockaddr_in addr_python = addr_ia; 
                    addr_python.sin_port = htons(5001); 
                    sendto(sock_ia, buffer, sizeof(Message), 0, (struct sockaddr*)&addr_python, sizeof(addr_python));
                }
            }
        }
    }
    
#ifdef _WIN32
    WSACleanup();
#endif
    return 0;
}