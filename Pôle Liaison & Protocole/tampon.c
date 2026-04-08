#include "protocol.h"

// Initialise le buffer
void init_buffer(TCPBuffer* buf) {
    buf->current_length = 0;
    memset(buf->data, 0, MAX_BUFFER_SIZE);
}

// Ajoute les données reçues au buffer
void add_data(TCPBuffer* buf, const char* new_data, int data_len) {
    if (buf->current_length + data_len < MAX_BUFFER_SIZE) {
        memcpy(buf->data + buf->current_length, new_data, data_len);
        buf->current_length += data_len;
        buf->data[buf->current_length] = '\0'; 
    } else {
        printf("Erreur : Buffer overflow !\n");
    }
}

// Extrait un message s'il y a un '\n'
int get_next_message(TCPBuffer* buf, char* output_msg) {
    char* newline_ptr = strchr(buf->data, '\n');
    
    if (newline_ptr != NULL) {
        int msg_len = newline_ptr - buf->data;
        
        strncpy(output_msg, buf->data, msg_len);
        output_msg[msg_len] = '\0';
        
        int remaining_len = buf->current_length - (msg_len + 1);
        memmove(buf->data, newline_ptr + 1, remaining_len);
        buf->current_length = remaining_len;
        buf->data[remaining_len] = '\0';
        
        return 1; 
    }
    return 0; 
}

// Transforme la Struct en texte
void serialize_message(const Message* msg, char* buffer, size_t buffer_size) {
    snprintf(buffer, buffer_size, "%d|%d|%d|%d|%s\n", 
             msg->id_joueur, msg->pos_x, msg->pos_y, msg->action, msg->target_id);
}

// Transforme le texte en Struct
int deserialize_message(const char* str, Message* msg) {
    int parsed = sscanf(str, "%d|%d|%d|%d|%15[^\n]", 
                        &msg->id_joueur, &msg->pos_x, &msg->pos_y, (int*)&msg->action, msg->target_id);
    return (parsed == 5); 
}