#include "protocol.h"
#include <string.h>

void serialize_binary(const Message* msg, char* buffer) {
    // On copie directement la structure dans le buffer réseau
    memcpy(buffer, msg, sizeof(Message));
}

void deserialize_binary(const char* buffer, Message* msg) {
    // On reconstruit la structure à partir des octets reçus
    memcpy(msg, buffer, sizeof(Message));
}