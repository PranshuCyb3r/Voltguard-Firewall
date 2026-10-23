#pragma once
#include <winsock2.h>
#include <ws2tcpip.h>
#include "modbus_frame.hpp"

class TelemetryPublisher {
private:
    SOCKET udp_socket;
    sockaddr_in dest_addr;

public:
    TelemetryPublisher(const char* ip, int port) {
        udp_socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        dest_addr.sin_family = AF_INET;
        dest_addr.sin_port = htons(port);
        dest_addr.sin_addr.s_addr = inet_addr(ip);
    }

    ~TelemetryPublisher() {
        if (udp_socket != INVALID_SOCKET) {
            closesocket(udp_socket);
        }
    }

    void publish(const TelemetryFrame& frame) {
        sendto(udp_socket, reinterpret_cast<const char*>(&frame), sizeof(TelemetryFrame), 0,
               (sockaddr*)&dest_addr, sizeof(dest_addr));
    }
};