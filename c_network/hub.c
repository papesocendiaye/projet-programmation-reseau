#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/select.h>

#define IPC_PATH "/tmp/medievai_ipc.sock"
#define UDP_PORT 12345
#define BCAST_ADDR "255.255.255.255"
#define BUF_SIZE 2048

int main() {
    int ipc_server_fd, ipc_client_fd = 0;
    int udp_fd;
    struct sockaddr_un ipc_addr;
    struct sockaddr_in udp_addr, broadcast_addr;
    char buffer[BUF_SIZE];
    int broadcast_enable = 1;

    // --- 1. CONFIGURATION SOCKET IPC (LOCAL) ---
    ipc_server_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    unlink(IPC_PATH);
    memset(&ipc_addr, 0, sizeof(ipc_addr));
    ipc_addr.sun_family = AF_UNIX;
    strncpy(ipc_addr.sun_path, IPC_PATH, sizeof(ipc_addr.sun_path) - 1);
    bind(ipc_server_fd, (struct sockaddr*)&ipc_addr, sizeof(ipc_addr));
    listen(ipc_server_fd, 1);

    // --- 2. CONFIGURATION SOCKET UDP (RÉSEAU) ---
    udp_fd = socket(AF_INET, SOCK_DGRAM, 0);
    // Activation du Broadcast
    setsockopt(udp_fd, SOL_SOCKET, SO_BROADCAST, &broadcast_enable, sizeof(broadcast_enable));
    
    // Bind pour écouter tout le monde sur le réseau
    memset(&udp_addr, 0, sizeof(udp_addr));
    udp_addr.sin_family = AF_INET;
    udp_addr.sin_port = htons(UDP_PORT);
    udp_addr.sin_addr.s_addr = INADDR_ANY;
    bind(udp_fd, (struct sockaddr*)&udp_addr, sizeof(udp_addr));

    // Préparation de l'adresse de destination (tout le monde)
    memset(&broadcast_addr, 0, sizeof(broadcast_addr));
    broadcast_addr.sin_family = AF_INET;
    broadcast_addr.sin_port = htons(UDP_PORT);
    broadcast_addr.sin_addr.s_addr = inet_addr(BCAST_ADDR);

    printf("Hub V1 démarré. IPC: %s | UDP Port: %d\n", IPC_PATH, UDP_PORT);

    fd_set readfds;
    while(1) {
        FD_ZERO(&readfds);
        FD_SET(ipc_server_fd, &readfds);
        FD_SET(udp_fd, &readfds);
        int max_fd = (ipc_server_fd > udp_fd) ? ipc_server_fd : udp_fd;

        if (ipc_client_fd > 0) {
            FD_SET(ipc_client_fd, &readfds);
            if (ipc_client_fd > max_fd) max_fd = ipc_client_fd;
        }

        select(max_fd + 1, &readfds, NULL, NULL, NULL);

        // A. Nouvelle connexion du processus Python
        if (FD_ISSET(ipc_server_fd, &readfds)) {
            ipc_client_fd = accept(ipc_server_fd, NULL, NULL);
            printf("[SYSTEM] Python connecté au Hub.\n");
        }

        // B. Message reçu du Python -> Diffusion sur le réseau UDP
        if (ipc_client_fd > 0 && FD_ISSET(ipc_client_fd, &readfds)) {
            int n = read(ipc_client_fd, buffer, BUF_SIZE);
            if (n <= 0) { 
                close(ipc_client_fd); ipc_client_fd = 0; 
                printf("[SYSTEM] Python déconnecté.\n");
            } else {
                // On envoie le message tel quel à tout le monde sur le réseau
                sendto(udp_fd, buffer, n, 0, (struct sockaddr*)&broadcast_addr, sizeof(broadcast_addr));
            }
        }

        // C. Message reçu du réseau UDP -> Transmission au Python local
        if (FD_ISSET(udp_fd, &readfds)) {
            struct sockaddr_in sender_addr;
            socklen_t addr_len = sizeof(sender_addr);
            int n = recvfrom(udp_fd, buffer, BUF_SIZE, 0, (struct sockaddr*)&sender_addr, &addr_len);
            
            if (n > 0 && ipc_client_fd > 0) {
                // On renvoie le message réseau vers le processus Python local
                write(ipc_client_fd, buffer, n);
            }
        }
    }
    return 0;
}