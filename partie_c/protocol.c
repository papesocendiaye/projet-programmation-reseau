#include "protocol.h"
#include <string.h>

void serialize_binary(const Message* msg, char* buffer) {
    memcpy(buffer, msg, sizeof(Message));
}

void deserialize_binary(const char* buffer, Message* msg) {
    memcpy(msg, buffer, sizeof(Message));
}