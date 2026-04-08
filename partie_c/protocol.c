#include "protocol.h"

// Transforme la Struct en texte pour l'envoi UDP
void serialize_message(const Message* msg, char* buffer, size_t buffer_size) {
    // Note : on peut enlever le \n car UDP gère déjà la fin du paquet
    snprintf(buffer, buffer_size, "%d|%d|%d|%d|%s", 
             msg->id_joueur, msg->pos_x, msg->pos_y, msg->action, msg->target_id);
}

// Transforme le texte reçu par UDP en Struct
int deserialize_message(const char* str, Message* msg) {
    int parsed = sscanf(str, "%d|%d|%d|%d|%31[^|]", 
                        &msg->id_joueur, &msg->pos_x, &msg->pos_y, (int*)&msg->action, msg->target_id);
    return (parsed == 5); 
}