/*Un processus réseau en C : gère les
 sockets TCP et la communication entre joueurs 
Responsabilités 
- Créer le socket serveur TCP 
- Accepter les connexions clients
- Lire les messages des clients

*/
#include <stdio.h>       // Bibliothèque standard pour l'affichage (printf)
#include <stdlib.h>      // Pour la gestion de la mémoire et exit()
#include <string.h>      // Pour manipuler les chaînes de caractères (memset)
#include <unistd.h>      // Pour les fonctions système Linux (close, read)
#include <arpa/inet.h>   // Bibliothèque spécifique aux sockets (IP, ports)

#define PORT 5000        // Le port sur lequel les deux PC vont communiquer

int main(int argc, char *argv[]) {
    // Déclarations des variables
    int sock = 0, conn_sock;
    struct sockaddr_in serv_addr; // Structure contenant l'adresse IP et le Port
    char buffer[1024] = {0};      // Espace mémoire pour stocker les messages reçus

    // --- MISSION MEMBRE 1 : CRÉATION DE LA SOCKET ---
    // On crée un "point de communication". AF_INET = IPv4, SOCK_STREAM = TCP
    if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
        printf("\n Erreur de création de socket \n");
        return -1;
    }

    // Configuration de l'adresse (Famille et Port)
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(PORT); // htons convertit le port pour le réseau

    // --- LOGIQUE SANS SERVEUR (P2P) ---
    // Si on passe une adresse IP en argument (ex: ./reseau_test 192.168.1.10)
    if (argc > 1) {
        
        // --- CAS CLIENT (On rejoint un ami) ---
        printf("Tentative de connexion vers %s...\n", argv[1]);
        
        // Convertit l'adresse IP du texte (ex: "192...") vers le format binaire réseau
        if (inet_pton(AF_INET, argv[1], &serv_addr.sin_addr) <= 0) {
            printf("\nAdresse invalide ou non supportée\n");
            return -1;
        }

        // Tente d'établir la connexion avec l'autre PC
        if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
            // MISSION MEMBRE 2 : GESTION D'ERREUR
            printf("\nConnexion échouée. Vérifiez l'IP ou si l'autre PC écoute.\n");
            return -1;
        }

        // Envoi d'un message de test pour valider que le tuyau fonctionne
        send(sock, "Bonjour depuis le PC distant !", 30, 0);
        printf("Message de test envoyé.\n");
    } 
    else {
        // --- CAS "SERVEUR" LOCAL (On attend un ami) ---
        
        // MISSION MEMBRE 2 : Option pour réutiliser le port sans attendre (REUSEADDR)
        int opt = 1;
        setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        // On dit à la socket d'écouter sur n'importe quelle interface réseau du PC
        serv_addr.sin_addr.s_addr = INADDR_ANY;

        // Attachement de la socket au port 5000
        if (bind(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
            printf("\nErreur de Bind : le port est peut-être déjà utilisé.\n");
            return -1;
        }

        // On met la socket en mode "écoute"
        listen(sock, 3);
        printf("En attente d'une connexion sur le port %d...\n", PORT);
        
        // Le programme se bloque ici jusqu'à ce qu'un ami se connecte
        conn_sock = accept(sock, (struct sockaddr *)NULL, NULL);
        
        // MISSION MEMBRE 2 : Vérification si la connexion a bien été acceptée
        if (conn_sock < 0) {
            printf("Erreur lors de l'acceptation de la connexion.\n");
            return -1;
        }
        
        printf("Connexion acceptée !\n");
        
        // Lecture des données reçues depuis l'autre PC
        // MISSION MEMBRE 1 : Afficher ce qu'on reçoit
        read(conn_sock, buffer, 1024);
        printf("Message reçu : %s\n", buffer);
        
        // Fermeture de la connexion après réception
        close(conn_sock);
    }

    // Fermeture de la socket principale
    close(sock);
    return 0;
}