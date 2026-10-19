#include <iostream>
#include <vector>
#include <chrono>
#include <winsock2.h>
#include <ws2tcpip.h>
#include "modbus_frame.hpp"
#include "physics_engine.hpp"

#pragma comment(lib, "ws2_32.lib")

#define PORT 5502
#define BUFFER_SIZE 1024

int main() {
    std::cout << "========================================================================\n";
    std::cout << "     VoltGuard: Real-Time Cyber-Physical OT/ICS Firewall Server         \n";
    std::cout << "========================================================================\n";

    // 1. Initialize Winsock for Windows networking
    WSADATA wsaData;
    int wsaResult = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (wsaResult != 0) {
        std::cerr << "[ERROR] WSAStartup failed: " << wsaResult << "\n";
        return 1;
    }

    // 2. Create TCP Socket
    SOCKET server_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (server_socket == INVALID_SOCKET) {
        std::cerr << "[ERROR] Failed to create socket: " << WSAGetLastError() << "\n";
        WSACleanup();
        return 1;
    }

    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY; // Listen on all network interfaces
    server_addr.sin_port = htons(PORT);

    // 3. Bind socket to port 5502
    if (bind(server_socket, (sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        std::cerr << "[ERROR] Bind failed on port " << PORT << ": " << WSAGetLastError() << "\n";
        closesocket(server_socket);
        WSACleanup();
        return 1;
    }

    // 4. Start Listening
    if (listen(server_socket, SOMAXCONN) == SOCKET_ERROR) {
        std::cerr << "[ERROR] Listen failed: " << WSAGetLastError() << "\n";
        closesocket(server_socket);
        WSACleanup();
        return 1;
    }

    std::cout << "[VoltGuard] Engine State  : ACTIVE\n";
    std::cout << "[VoltGuard] Listening on  : 0.0.0.0:" << PORT << " (Modbus/TCP)\n";
    std::cout << "[VoltGuard] Physics Rules : Active (Max RPM 3600 | Max Accel 400 RPM/s | Min 500 RPM)\n";
    std::cout << "[VoltGuard] Waiting for SCADA / PLC connections...\n";
    std::cout << "------------------------------------------------------------------------\n\n";

    VoltGuard::PhysicsEngine engine;
    uint8_t buffer[BUFFER_SIZE];

    while (true) {
        sockaddr_in client_addr{};
        int client_size = sizeof(client_addr);

        SOCKET client_socket = accept(server_socket, (sockaddr*)&client_addr, &client_size);
        if (client_socket == INVALID_SOCKET) {
            std::cerr << "[WARN] Client connection accept failed: " << WSAGetLastError() << "\n";
            continue;
        }

        char client_ip[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &client_addr.sin_addr, client_ip, INET_ADDRSTRLEN);
        std::cout << "[INCOMING] Connection established from SCADA Client: " << client_ip << "\n";

        // Receive raw Modbus frame over the wire
        int bytes_received = recv(client_socket, (char*)buffer, BUFFER_SIZE, 0);
        if (bytes_received > 0) {
            auto now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count();

            VoltGuard::ParsedFrame frame;
            auto start = std::chrono::high_resolution_clock::now();

            bool parse_success = VoltGuard::ModbusParser::parse_frame(buffer, bytes_received, &frame);

            if (!parse_success) {
                std::cout << "  [MALFORMED] Invalid Modbus packet size/format. Dropping connection.\n";
            } else {
                VoltGuard::Verdict verdict = engine.verify_rpm_command(frame.register_value, now_ms);
                auto end = std::chrono::high_resolution_clock::now();
                auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();

                std::cout << "  [MODBUS] Transaction ID : " << frame.transaction_id << "\n";
                std::cout << "  [MODBUS] Unit ID (PLC)  : " << (int)frame.unit_id << "\n";
                std::cout << "  [MODBUS] Function Code  : 0x0" << std::hex << (int)frame.function_code << std::dec << "\n";
                std::cout << "  [MODBUS] Requested RPM  : " << frame.register_value << " RPM\n";
                std::cout << "  [VERDICT] Decision      : " << VoltGuard::PhysicsEngine::verdict_to_string(verdict) << "\n";
                std::cout << "  [LATENCY] Engine Time   : " << ns << " ns (" << (ns / 1000.0) << " us)\n";

                if (verdict == VoltGuard::Verdict::ALLOW) {
                    std::cout << "  >>> ACTION: [FORWARDED TO ACTUATOR / PLC] <<<\n";
                    const char* resp = "STATUS: ALLOWED\n";
                    send(client_socket, resp, strlen(resp), 0);
                } else {
                    std::cout << "  >>> ACTION: [CYBER ATTACK BLOCKED - PACKET DROPPED] <<<\n";
                    const char* resp = "STATUS: BLOCKED_BY_VOLTGUARD_PHYSICS_ENGINE\n";
                    send(client_socket, resp, strlen(resp), 0);
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
