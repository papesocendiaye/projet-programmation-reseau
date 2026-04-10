#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

// Énumération des actions pour la Version 2
typedef enum { 
    ACTION_MOVE = 0, 
    ACTION_ATTACK = 1, 
    ACTION_SPAWN = 2, 
    ACTION_REQ_OWNERSHIP = 3, // Demande de propriété
    ACTION_ACK_OWNERSHIP = 4, // Transfert de propriété + état
    ACTION_HELLO = 5
} ActionType;

#pragma pack(push, 1) // Force l'alignement binaire sans espaces vides
typedef struct {
    int32_t id_joueur;
    int32_t pos_x;
    int32_t pos_y;
    int32_t action;      // Utilise ActionType
    double  timestamp;   // Pour la cohérence temporelle (Axe A - Tâche 2)
    char    target_id[32]; 
} Message;
#pragma pack(pop)

void serialize_binary(const Message* msg, char* buffer);
void deserialize_binary(const char* buffer, Message* msg);

#endif