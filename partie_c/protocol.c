#include "protocol.h"

void serialize_message(const Message* msg, char* buffer, size_t buffer_size) {
    snprintf(buffer, buffer_size, "%d|%d|%d|%d|%s", 
             msg->id_joueur, msg->pos_x, msg->pos_y, (int)msg->action, msg->target_id);
}

int deserialize_message(const char* str, Message* msg) {
    int parsed = sscanf(str, "%d|%d|%d|%d|%31[^|]", 
                        &msg->id_joueur, &msg->pos_x, &msg->pos_y, (int*)&msg->action, msg->target_id);
    return (parsed == 5); 
}