#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "protocol.h"

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
  #define SOCKET_ERROR   -1
  typedef int SOCKET;
#endif

#define PORT 5000

static void socket_close(SOCKET s) {
#ifdef _WIN32
    closesocket(s);
#else
    close(s);
#endif
}

int main(int argc, char *argv[]) {
#ifdef _WIN32
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        printf("WSAStartup failed\n");
        return 1;
    }
#endif

    SOCKET sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == INVALID_SOCKET) {
        printf("socket() failed\n");
        return 1;
    }

    struct sockaddr_in my_addr;
    memset(&my_addr, 0, sizeof(my_addr));
    my_addr.sin_family = AF_INET;
    my_addr.sin_port = htons(PORT);

    char buffer[MAX_BUFFER_SIZE];

    if (argc > 1) {
        // --- MODE ENVOYEUR ---
        struct sockaddr_in other_addr;
        memset(&other_addr, 0, sizeof(other_addr));
        other_addr.sin_family = AF_INET;
        other_addr.sin_port = htons(PORT);
        other_addr.sin_addr.s_addr = inet_addr(argv[1]);

        Message msg = {1, 100, 200, ACTION_MOVE, "U37"};
        serialize_message(&msg, buffer, sizeof(buffer));

        // Test: envoyer 3 paquets
        for (int i = 0; i < 3; i++) {
            int sent = sendto(sock, buffer, (int)strlen(buffer), 0,
                              (struct sockaddr*)&other_addr, (socklen_t)sizeof(other_addr));
            if (sent == SOCKET_ERROR) {
                printf("sendto failed\n");
                break;
            }
            printf("UDP sent %d: %s\n", i + 1, buffer);
        }

    } else {
        // --- MODE RECEPTEUR ---
        my_addr.sin_addr.s_addr = INADDR_ANY;

        if (bind(sock, (struct sockaddr*)&my_addr, (socklen_t)sizeof(my_addr)) == SOCKET_ERROR) {
            printf("bind() failed\n");
            socket_close(sock);
            return 1;
        }

        printf("UDP listen on port %d...\n", PORT);

        while (1) {
            struct sockaddr_in src_addr;
            socklen_t src_len = sizeof(src_addr);
            int len = recvfrom(sock, buffer, MAX_BUFFER_SIZE - 1, 0,
                               (struct sockaddr*)&src_addr, &src_len);
            if (len <= 0) {
                // best-effort: on continue
                continue;
            }
            buffer[len] = '\0';

            Message received_msg;
            if (deserialize_message(buffer, &received_msg)) {
                printf("[UDP RECV] from %s | player=%d action=%d pos=(%d,%d) target=%s\n",
                       inet_ntoa(src_addr.sin_addr),
                       received_msg.id_joueur,
                       (int)received_msg.action,
                       received_msg.pos_x,
                       received_msg.pos_y,
                       received_msg.target_id);
            } else {
                printf("[UDP RECV] invalid packet: %s\n", buffer);
            }
        }
    }

    socket_close(sock);

#ifdef _WIN32
    WSACleanup();
#endif
    return 0;
}
