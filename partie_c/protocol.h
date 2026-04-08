#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdio.h>
#include <string.h>

#define MAX_BUFFER_SIZE 1024

typedef enum { 
    ACTION_MOVE, 
    ACTION_ATTACK, 
    ACTION_SPAWN, 
    ACTION_REQ_OWNERSHIP 
} ActionType;

typedef struct {
    int id_joueur;
    int pos_x;
    int pos_y;
    ActionType action;
    char target_id[32]; // On a agrandi à 32 comme prévu
} Message;

// Les fonctions de traduction restent les mêmes ! 
// C'est l'avantage d'avoir bien bossé la Partie C.
void serialize_message(const Message* msg, char* buffer, size_t buffer_size);
int deserialize_message(const char* str, Message* msg);

#endif