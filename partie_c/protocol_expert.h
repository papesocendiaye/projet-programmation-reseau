#ifndef PROTOCOL_EXPERT_H
#define PROTOCOL_EXPERT_H

#include <stdint.h>

typedef enum {
    ACTION_UPDATE = 1,         
    ACTION_REQ_OWNERSHIP = 3,   // Demande de propriété réseau 
    ACTION_ACK_OWNERSHIP = 4,   // Transfert d'état + propriété 
    ACTION_HELLO = 5           
} ActionType;

#pragma pack(push, 1) // on va force la taille à 56 octets sans padding
typedef struct {
    int32_t player_id;      
    int32_t x;              
    int32_t y;              
    int32_t action_type;    
    double  timestamp;     
    char    unit_id[32];    
    uint16_t checksum;    
} MessageExpert;
#pragma pack(pop)

#endif