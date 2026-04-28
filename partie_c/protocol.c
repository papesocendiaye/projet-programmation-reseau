#include "protocol.h"

void serialize_message(const Message* msg, char* buffer, size_t buffer_size) {
    // Utilisation de %f au lieu de %d
    snprintf(buffer, buffer_size, "%d|%f|%f|%d|%s",
             msg->id_joueur, msg->pos_x, msg->pos_y, (int)msg->action, msg->target_id);
}

int deserialize_message(const char* str, Message* msg) {
    int action_tmp = 0;
    char target_tmp[TARGET_ID_MAX] = {0};

    // Utilisation de %f au lieu de %d
    int parsed = sscanf(str, "%d|%f|%f|%d|%31[^\n]",
                        &msg->id_joueur,
                        &msg->pos_x,
                        &msg->pos_y,
                        &action_tmp,
                        target_tmp);

    if (parsed != 5) return 0;

    msg->action = (ActionType)action_tmp;
    strncpy(msg->target_id, target_tmp, TARGET_ID_MAX - 1);
    msg->target_id[TARGET_ID_MAX - 1] = '\0';
    return 1;
}