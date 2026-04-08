#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdio.h>
#include <string.h>

#define MAX_BUFFER_SIZE 1024

// 1. Les types d'actions
typedef enum { 
    ACTION_MOVE, 
    ACTION_ATTACK, 
    ACTION_SPAWN, 
    ACTION_REQ_OWNERSHIP 
} ActionType;

// 2. Le format du message
typedef struct {
    int id_joueur;
    int pos_x;
    int pos_y;
    ActionType action;
    char target_id[16];
} Message;

// 3. Le tampon réseau
typedef struct {
    char data[MAX_BUFFER_SIZE];
    int current_length;
} TCPBuffer;

// 4. Les signatures des fonctions (les "titres")
void init_buffer(TCPBuffer* buf);
void add_data(TCPBuffer* buf, const char* new_data, int data_len);
int get_next_message(TCPBuffer* buf, char* output_msg);
void serialize_message(const Message* msg, char* buffer, size_t buffer_size);
int deserialize_message(const char* str, Message* msg);

#endif // PROTOCOL_H