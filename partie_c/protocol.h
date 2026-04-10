#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

// Mise à jour des actions pour la Version 2
typedef enum { 
    ACTION_MOVE = 0, 
    ACTION_ATTACK = 1, 
    ACTION_SPAWN = 2, 
    ACTION_REQ_OWNERSHIP = 3, // Demander la propriété réseau [cite: 165]
    ACTION_ACK_OWNERSHIP = 4, // Transférer la propriété + état [cite: 166]
    ACTION_HELLO = 5
} ActionType;

#pragma pack(push, 1) // Force l'alignement binaire strict
typedef struct {
    int32_t id_joueur;
    int32_t pos_x;
    int32_t pos_y;
    int32_t action;      
    double  timestamp;   // Pour l'ordre des événements et la cohérence [cite: 80]
    char    target_id[32]; 
} Message;
#pragma pack(pop)

void serialize_binary(const Message* msg, char* buffer);
void deserialize_binary(const char* buffer, Message* msg);

#endif