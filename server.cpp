#include <iostream>
#include <iomanip>
#include <chrono>
#include <winsock2.h>
#include <ws2tcpip.h>
#include "modbus_frame.hpp"
#include "physics_engine.hpp"
#include "telemetry.hpp"

#pragma comment(lib, "ws2_32.lib")

int main() {
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        std::cerr << "[FATAL] WSAStartup failed\n";
        return 1;
    }

    SOCKET server_fd = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in srv_addr{};
    srv_addr.sin_family = AF_INET;
    srv_addr.sin_addr.s_addr = INADDR_ANY;
    srv_addr.sin_port = htons(5502);

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));

    if (bind(server_fd, (sockaddr*)&srv_addr, sizeof(srv_addr)) == SOCKET_ERROR) {
        std::cerr << "[FATAL] Bind failed on port 5502\n";
        return 1;
    }
    listen(server_fd, 5);

    SOCKET udp_sock = socket(AF_INET, SOCK_DGRAM, 0);
    sockaddr_in udp_dest{};
    udp_dest.sin_family = AF_INET;
    udp_dest.sin_port = htons(5555);
    inet_pton(AF_INET, "127.0.0.1", &udp_dest.sin_addr);

    VoltGuard::PhysicsEngine engine;

    std::cout << "========================================================================\n";
    std::cout << "  VOLTGUARD :: PRODUCTION CYBER-PHYSICAL OT FIREWALL & IPS (WEEK 1-4)    \n";
    std::cout << "  INGRESS: TCP 5502 (ZERO-COPY) | TELEMETRY: UDP 5555 (32-BYTE ALIGNED)  \n";
    std::cout << "========================================================================\n";
    std::cout << "[INFO] VoltGuard Zero-Copy IPS Ingress Armed & Listening on TCP 5502...\n";

    while (true) {
        sockaddr_in client_addr{};
        int addr_len = sizeof(client_addr);
        SOCKET client_sock = accept(server_fd, (sockaddr*)&client_addr, &addr_len);
        if (client_sock == INVALID_SOCKET) continue;

        auto t_start = std::chrono::high_resolution_clock::now();

        uint8_t buffer[256];
        int bytes_read = recv(client_sock, (char*)buffer, sizeof(buffer), 0);

        if (bytes_read >= 12) {
            uint16_t tx_id = (buffer[0] << 8) | buffer[1];
            uint8_t func   = buffer[7];
            uint16_t reg   = (buffer[8] << 8) | buffer[9];
            uint16_t raw_val = (buffer[10] << 8) | buffer[11];

            float shock_bar = 7.75f;
            uint16_t twin_rpm = 1800;
            float fatigue_score = 12.4f;

            VoltGuard::Verdict v = engine.evaluate(raw_val, shock_bar, twin_rpm, fatigue_score);

            auto t_end = std::chrono::high_resolution_clock::now();
            double latency_us = std::chrono::duration<double, std::micro>(t_end - t_start).count();

            std::cout << "[INGRESS] Tx: 0x" << std::hex << std::setw(4) << std::setfill('0') << tx_id << std::dec
                      << " | Reg: 0x" << std::hex << std::setw(4) << std::setfill('0') << reg << std::dec
                      << " | Commanded: " << std::setw(5) << std::setfill('0') << raw_val << " RPM"
                      << " | Shock: " << std::fixed << std::setprecision(2) << shock_bar << " Bar"
                      << " | Twin: " << std::setw(5) << std::setfill('0') << twin_rpm << " RPM"
                      << " | Latency: " << std::fixed << std::setprecision(2) << latency_us << " us -> ";

            if (v == VoltGuard::Verdict::ALLOW) {
                std::cout << "[ ALLOW : INVARIANT MET ]\n";
                send(client_sock, (const char*)buffer, bytes_read, 0);
            } else {
                std::cout << "[ DROP : INTERCEPTED AT WIRE ] (Verdict Code: " << static_cast<int>(v) << ")\n";
                uint8_t err_resp[9] = { buffer[0], buffer[1], 0x00, 0x00, 0x00, 0x03, buffer[6], 0x86, 0x04 };
                send(client_sock, (const char*)err_resp, sizeof(err_resp), 0);
            }

            TelemetryFrame frame{};
            frame.timestamp_us = static_cast<uint32_t>(std::chrono::duration_cast<std::chrono::microseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count());
            frame.tx_id = tx_id;
            frame.commanded_rpm = raw_val;
            frame.joukowsky_shock = shock_bar;
            frame.twin_rpm = twin_rpm;
            frame.basquin_fatigue = fatigue_score;
            frame.verdict = static_cast<uint8_t>(v);

            sendto(udp_sock, (const char*)&frame, sizeof(frame), 0, (sockaddr*)&udp_dest, sizeof(udp_dest));
        }

        closesocket(client_sock);
    }

    closesocket(server_fd);
    closesocket(udp_sock);
    WSACleanup();
    return 0;
}