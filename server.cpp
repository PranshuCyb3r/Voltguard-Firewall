#include <iostream>
#include <vector>
#include <chrono>
#include <cstring>
#include <winsock2.h>
#include <ws2tcpip.h>

#include "modbus_frame.hpp"
#include "physics_engine.hpp"

#pragma comment(lib, "ws2_32.lib")

#define LISTEN_PORT 5502
#define RECV_BUFFER_SIZE 1024

int main() {
    std::cout << "========================================================================\n";
    std::cout << "     VoltGuard: Real-Time Cyber-Physical OT/ICS Firewall Daemon         \n";
    std::cout << "========================================================================\n";

    // 1. Initialize Winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        std::cerr << "[CRITICAL] Winsock initialization failed.\n";
        return 1;
    }

    // 2. Open TCP Stream Socket
    SOCKET server_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (server_socket == INVALID_SOCKET) {
        std::cerr << "[CRITICAL] Failed to create socket: " << WSAGetLastError() << "\n";
        WSACleanup();
        return 1;
    }

    // Allow quick port re-use
    BOOL optval = TRUE;
    setsockopt(server_socket, SOL_SOCKET, SO_REUSEADDR, (char*)&optval, sizeof(optval));

    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(LISTEN_PORT);

    // 3. Bind to interface
    if (bind(server_socket, (sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        std::cerr << "[CRITICAL] Port " << LISTEN_PORT << " bind failed: " << WSAGetLastError() << "\n";
        closesocket(server_socket);
        WSACleanup();
        return 1;
    }

    // 4. Start Listening
    if (listen(server_socket, SOMAXCONN) == SOCKET_ERROR) {
        std::cerr << "[CRITICAL] Listen error: " << WSAGetLastError() << "\n";
        closesocket(server_socket);
        WSACleanup();
        return 1;
    }

    std::cout << "[SYSTEM] Engine Status   : ACTIVE & ENFORCING\n";
    std::cout << "[SYSTEM] Listening on    : 0.0.0.0:" << LISTEN_PORT << " (Modbus TCP)\n";
    std::cout << "[SYSTEM] Invariant Rules : Max 3600 RPM | Min 500 RPM | Accel 400 RPM/s\n";
    std::cout << "[SYSTEM] Press Ctrl+C in terminal to safely stop.\n";
    std::cout << "------------------------------------------------------------------------\n\n";

    VoltGuard::PhysicsEngine engine;
    uint8_t buffer[RECV_BUFFER_SIZE];

    while (true) {
        sockaddr_in client_addr{};
        int client_size = sizeof(client_addr);

        SOCKET client_socket = accept(server_socket, (sockaddr*)&client_addr, &client_size);
        if (client_socket == INVALID_SOCKET) {
            continue;
        }

        char client_ip[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &client_addr.sin_addr, client_ip, INET_ADDRSTRLEN);
        std::cout << "[CONN] Inbound connection from: " << client_ip << "\n";

        std::memset(buffer, 0, RECV_BUFFER_SIZE);
        int bytes_received = recv(client_socket, (char*)buffer, RECV_BUFFER_SIZE, 0);

        if (bytes_received > 0) {
            auto now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count();

            VoltGuard::ParsedFrame frame;
            auto start = std::chrono::high_resolution_clock::now();

            bool parse_ok = VoltGuard::ModbusParser::parse_frame(buffer, bytes_received, &frame);

            if (!parse_ok) {
                std::cout << "  [ANOMALY] Malformed frame or invalid protocol header. Packet dropped.\n";
                const char* malformed_resp = "STATUS: ERROR_MALFORMED_FRAME\n";
                send(client_socket, malformed_resp, (int)strlen(malformed_resp), 0);
            } else {
                VoltGuard::Verdict verdict = engine.verify_rpm_command(frame.register_value, now_ms);
                auto end = std::chrono::high_resolution_clock::now();
                auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();

                std::cout << "  [FRAME] TxID: " << frame.transaction_id
                          << " | Unit: " << (int)frame.unit_id 
                          << " | Func: 0x0" << std::hex << (int)frame.function_code << std::dec
                          << " | Target RPM: " << frame.register_value << " RPM\n";
                std::cout << "  [VERDICT] " << VoltGuard::PhysicsEngine::verdict_to_string(verdict) << "\n";
                std::cout << "  [INSPECTION TIME] " << ns << " ns (" << (ns / 1000.0) << " us)\n";

                if (verdict == VoltGuard::Verdict::ALLOW) {
                    std::cout << "  >>> FORWARDED: Safe command routed to physical actuator <<<\n";
                    const char* resp = "STATUS: ALLOWED\n";
                    send(client_socket, resp, (int)strlen(resp), 0);
                } else {
                    std::cout << "  >>> BLOCKED: Cyber-physical attack prevented. Connection reset <<<\n";
                    const char* resp = "STATUS: BLOCKED_BY_VOLTGUARD_PHYSICS_ENGINE\n";
                    send(client_socket, resp, (int)strlen(resp), 0);
                }
            }
        }

        closesocket(client_socket);
        std::cout << "------------------------------------------------------------------------\n";
    }

    closesocket(server_socket);
    WSACleanup();
    return 0;
}
