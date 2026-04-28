#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

typedef enum { 
    ACTION_MOVE = 0, 
    ACTION_ATTACK = 1, 
    ACTION_SPAWN = 2, 
    ACTION_REQ_OWNERSHIP = 3, 
    ACTION_ACK_OWNERSHIP = 4, 
    ACTION_HELLO = 5
} ActionType;

#pragma pack(push, 1) 
typedef struct {
    int32_t id_joueur;
    int32_t pos_x;
    int32_t pos_y;
    int32_t action;      
    double  timestamp;   // <-- LE FAMEUX CHAMP EST ICI
    char    target_id[32]; 
} Message;
#pragma pack(pop)

void serialize_binary(const Message* msg, char* buffer);
void deserialize_binary(const char* buffer, Message* msg);

#endif