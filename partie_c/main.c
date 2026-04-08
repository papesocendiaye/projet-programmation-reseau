#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "protocol.h" // On inclut le travail du groupe Liaison

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
#else
    #include <unistd.h>
    #include <arpa/inet.h>
    #include <sys/socket.h>
#endif

#define PORT 5000

int main(int argc, char *argv[]) {
    // 1. INITIALISATION RÉSEAU (Windows/Linux)
#ifdef _WIN32
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);
#endif

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(PORT);

    TCPBuffer net_buffer;
    init_buffer(&net_buffer);
    char raw_recv[MAX_BUFFER_SIZE];

    if (argc > 1) {
        // --- MODE CLIENT ---
        addr.sin_addr.s_addr = inet_addr(argv[1]);
        connect(sock, (struct sockaddr *)&addr, sizeof(addr));
        printf("Connecté au partenaire.\n");

        // Exemple d'envoi utilisant le protocole du Membre 6
        Message my_action = {1, 150, 200, ACTION_MOVE, "Soldier1"};
        char to_send[MAX_BUFFER_SIZE];
        serialize_message(&my_action, to_send, sizeof(to_send));
        
        send(sock, to_send, strlen(to_send), 0);
        printf("Message envoyé : %s", to_send);

    } else {
        // --- MODE SERVEUR (P2P) ---
        addr.sin_addr.s_addr = INADDR_ANY;
        bind(sock, (struct sockaddr *)&addr, sizeof(addr));
        listen(sock, 3);
        printf("En attente sur le port %d...\n", PORT);

        int client_sock = accept(sock, NULL, NULL);
        
        // Réception avec le découpage du Membre 7
        int bytes_received = recv(client_sock, raw_recv, MAX_BUFFER_SIZE - 1, 0);
        if (bytes_received > 0) {
            add_data(&net_buffer, raw_recv, bytes_received);
            
            char single_message[MAX_BUFFER_SIZE];
            if (get_next_message(&net_buffer, single_message)) {
                Message received_msg;
                if (deserialize_message(single_message, &received_msg)) {
                    printf("\n--- Message reçu et décodé ---\n");
                    printf("Joueur: %d | Pos: %d,%d | Action: %d | Cible: %s\n", 
                            received_msg.id_joueur, received_msg.pos_x, 
                            received_msg.pos_y, received_msg.action, received_msg.target_id);
                }
            }
        }
#ifdef _WIN32
        closesocket(client_sock);
#else
        close(client_sock);
#endif
    }

#ifdef _WIN32
    closesocket(sock);
    WSACleanup();
#else
    close(sock);
#endif
    return 0;
}