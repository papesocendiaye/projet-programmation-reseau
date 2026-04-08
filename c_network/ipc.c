/*	ipc.c
	communication avec Python
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/select.h>

#define SOCKET_PATH "/tmp/medievai_ipc.sock"

int main() {
    int server_fd, client_fd = 0;
    int max_sd, activity;
    struct sockaddr_un addr;
    char buffer[1025];

    // Ensemble des sockets à surveiller
    fd_set readfds; 

    // 1. Initialisation du socket Unix (IPC)
    server_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    unlink(SOCKET_PATH);
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, SOCKET_PATH, sizeof(addr.sun_path) - 1);
    bind(server_fd, (struct sockaddr*)&addr, sizeof(addr));
    listen(server_fd, 5);

    printf("Multiplexeur C démarré. En attente sur %s...\n", SOCKET_PATH);

    // Boucle infinie du processus C
    while(1) {
        FD_ZERO(&readfds); // On vide l'ensemble

        // On ajoute le socket d'écoute IPC
        FD_SET(server_fd, &readfds);
        max_sd = server_fd;

        // Si le Python est connecté, on écoute aussi ce qu'il dit
        if (client_fd > 0) {
            FD_SET(client_fd, &readfds);
            if (client_fd > max_sd) max_sd = client_fd;
        }

        // ==========================================
        // ICI : L'équipe Réseau ajoutera son socket TCP
        // ex: FD_SET(tcp_socket, &readfds);
        // if (tcp_socket > max_sd) max_sd = tcp_socket;
        // ==========================================

        // Le programme s'endort ici jusqu'à ce qu'un message arrive !
        activity = select(max_sd + 1, &readfds, NULL, NULL, NULL);

        // Cas 1 : Nouvelle connexion IPC (Python vient de démarrer)
        if (FD_ISSET(server_fd, &readfds)) {
            client_fd = accept(server_fd, NULL, NULL);
            printf("Processus Python connecté !\n");
        }

        // Cas 2 : Message reçu du Python (Action locale à diffuser)
        if (client_fd > 0 && FD_ISSET(client_fd, &readfds)) {
            int valread = read(client_fd, buffer, 1024);
            if (valread == 0) {
                printf("Python s'est déconnecté.\n");
                close(client_fd);
                client_fd = 0;
            } else {
                buffer[valread] = '\0';
                printf("[IPC -> RÉSEAU] A diffuser : %s", buffer);
                // ICI : On fera l'envoi TCP aux autres joueurs
                // send(tcp_socket, buffer, strlen(buffer), 0);
            }
        }

        // ==========================================
        // Cas 3 : Message reçu du Réseau (Action distante)
        // if (FD_ISSET(tcp_socket, &readfds)) { ... on lit et on envoie à client_fd }
        // ==========================================
    }
    return 0;
}