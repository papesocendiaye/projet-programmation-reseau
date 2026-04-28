#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h> // Indispensable pour utiliser int32_t

// Énumération des actions pour la Version 2
typedef enum { 
    ACTION_MOVE = 0, 
    ACTION_ATTACK = 1, 
    ACTION_SPAWN = 2, 
    ACTION_REQ_OWNERSHIP = 3, // Demande de propriété
    ACTION_ACK_OWNERSHIP = 4, // Transfert de propriété + état (hp)
    ACTION_HELLO = 5
} ActionType;

#pragma pack(push, 1) // Force l'alignement binaire sans espaces vides (VITAL pour Python)
typedef struct {
    int32_t id_joueur;
    int32_t pos_x;
    int32_t pos_y;
    int32_t hp;          // <-- L'état de la ressource (V2)
    int32_t action;      // On force sur 32 bits pour la compatibilité Python
    double  timestamp;   // <-- Pour la cohérence temporelle (V2)
    char    target_id[32]; 
} Message;
#pragma pack(pop)

// On utilise bien les fonctions BINAIRES de la V2
void serialize_binary(const Message* msg, char* buffer);
void deserialize_binary(const char* buffer, Message* msg);

#endif