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
#endif

#define PORT 5000

int main(int argc, char *argv[]) {
#ifdef _WIN32
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);
#endif

    // Changement : SOCK_DGRAM au lieu de SOCK_STREAM pour UDP
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    
    struct sockaddr_in my_addr, other_addr;
    socklen_t addr_len = sizeof(other_addr);
    char buffer[MAX_BUFFER_SIZE];

    if (argc > 1) {
        // --- MODE ENVOYEUR ---
        memset(&other_addr, 0, sizeof(other_addr));
        other_addr.sin_family = AF_INET;
        other_addr.sin_port = htons(PORT);
        other_addr.sin_addr.s_addr = inet_addr(argv[1]);

        Message msg = {1, 100, 200, ACTION_MOVE, "U37"};
        serialize_message(&msg, buffer, sizeof(buffer));

        sendto(sock, buffer, strlen(buffer), 0, (struct sockaddr*)&other_addr, addr_len);
        printf("Paquet UDP envoyé vers %s\n", argv[1]);

    } else {
        // --- MODE RECEPTEUR ---
        my_addr.sin_family = AF_INET;
        my_addr.sin_port = htons(PORT);
        my_addr.sin_addr.s_addr = INADDR_ANY;

        bind(sock, (struct sockaddr*)&my_addr, sizeof(my_addr));
        printf("Écoute UDP sur le port %d...\n", PORT);

        while (1) {
            int len = recvfrom(sock, buffer, MAX_BUFFER_SIZE - 1, 0, (struct sockaddr*)&other_addr, &addr_len);
            if (len > 0) {
                buffer[len] = '\0';
                Message received_msg;
                if (deserialize_message(buffer, &received_msg)) {
                    printf("[UDP RECU] Unité %s agit en %d,%d\n", 
                            received_msg.target_id, received_msg.pos_x, received_msg.pos_y);
                }
            }
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