#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "protocol.h" 

//changement 
#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
    typedef int socklen_t;
#else
    #include <unistd.h>
    #include <arpa/inet.h>
    #include <sys/socket.h>
    #define INVALID_SOCKET -1
    #define SOCKET_ERROR -1
    typedef int SOCKET;
#endif

#define PORT 5000

int main(int argc, char *argv[]) {
    // 1. INITIALISATION RÉSEAU
#ifdef _WIN32
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) return 1;
#endif

    SOCKET sock = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(PORT);

    TCPBuffer net_buffer;
    init_buffer(&net_buffer);
    char raw_recv[MAX_BUFFER_SIZE];

    if (argc > 1) {
        // --- MODE CLIENT (Envoi continu possible) ---
        addr.sin_addr.s_addr = inet_addr(argv[1]);
        if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) == SOCKET_ERROR) {
            printf("Erreur de connexion.\n");
            return 1;
        }
        printf("Connecté au partenaire.\n");

        // NOTE POUR L'IA : Utiliser des IDs courts (ex: "U01") car target_id est limité à 16 chars
        Message my_action = {1, 150, 200, ACTION_MOVE, "U01"};
        char to_send[MAX_BUFFER_SIZE];
        
        // Simulation d'envoi de plusieurs messages rapides pour tester le buffer
        for(int i=0; i<3; i++) {
            serialize_message(&my_action, to_send, sizeof(to_send));
            send(sock, to_send, strlen(to_send), 0);
            printf("Message %d envoyé.\n", i+1);
        }

    } else {
        // --- MODE SERVEUR (Réception en boucle) ---
        addr.sin_addr.s_addr = INADDR_ANY;
        bind(sock, (struct sockaddr *)&addr, sizeof(addr));
        listen(sock, 3);
        printf("En attente sur le port %d (Mode Boucle Active)...\n", PORT);

        SOCKET client_sock = accept(sock, NULL, NULL);
        if (client_sock != INVALID_SOCKET) {
            
            int bytes_received;
            // BOUCLE DE RÉCEPTION : On ne s'arrête pas au premier message
            while ((bytes_received = recv(client_sock, raw_recv, MAX_BUFFER_SIZE - 1, 0)) > 0) {
                
                // 1. On ajoute les données brutes au tampon
                add_data(&net_buffer, raw_recv, bytes_received);
                
                // 2. On traite TOUS les messages complets actuellement dans le tampon
                // (C'est ici qu'on gère le cas où TCP colle plusieurs messages)
                char single_message[MAX_BUFFER_SIZE];
                while (get_next_message(&net_buffer, single_message)) {
                    Message received_msg;
                    if (deserialize_message(single_message, &received_msg)) {
                        printf("\n[LOG] Message décodé : Unité %s -> Action %d en (%d,%d)\n", 
                               received_msg.target_id, received_msg.action, 
                               received_msg.pos_x, received_msg.pos_y);
                    }
                }
            }
            printf("\nPartenaire déconnecté.\n");
#ifdef _WIN32
            closesocket(client_sock);
#else
            close(client_sock);
#endif
        }
    }

#ifdef _WIN32
    closesocket(sock);
    WSACleanup();
#else
    close(sock);
#endif
    return 0;
}