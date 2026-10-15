import asyncio
import logging
import random

from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusDeviceContext,
    ModbusServerContext,
)

# Industrial Logging Configuration
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] [PLC-SIM] %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("VoltguardPLC")

class VirtualIndustrialPLC:
    """
    VoltGuard Virtual Industrial Water Pumping PLC:
    - Register 0: Pressure (bar * 10, e.g. 45 = 4.5 bar)
    - Register 1: Flow Rate (L/s * 10, e.g. 120 = 12.0 L/s)
    - Register 2: Valve Position (0 = Closed, 100 = Fully Open)
    - Register 3: Pump Motor RPM (0 to 3000 RPM)
    """
    def __init__(self):
        # Baseline industrial parameters
        self.pressure = 45        # 4.5 bar
        self.flow_rate = 120      # 12.0 L/s
        self.valve_pos = 100      # 100% open
        self.pump_rpm = 2850      # 2850 RPM

        # Register data block (10 registers)
        initial_registers = [self.pressure, self.flow_rate, self.valve_pos, self.pump_rpm, 0, 0, 0, 0, 0, 0]
        self.block = ModbusSequentialDataBlock(1, initial_registers)
        
        # Pymodbus 3.8+ standard: DeviceContext wraps data block
        self.device = ModbusDeviceContext(hr=self.block)
        self.context = ModbusServerContext(devices=self.device, single=True)

    def read_telemetry(self):
        """Read live register values safely."""
        try:
            return self.block.getValues(1, 4)
        except Exception:
            return [self.pressure, self.flow_rate, self.valve_pos, self.pump_rpm]

    def write_telemetry(self, values):
        """Write updated sensor values to holding registers."""
        try:
            self.block.setValues(1, values)
        except Exception as e:
            logger.error(f"Failed to update registers: {e}")

    async def run_telemetry_loop(self):
        """Simulates physical sensor telemetry and reads incoming control commands."""
        logger.info("Real-time Industrial Telemetry Loop active.")
        while True:
            try:
                # Read current register values (Operator / SCADA commands)
                values = self.read_telemetry()
                current_valve = values[2] if len(values) > 2 else self.valve_pos
                current_rpm = values[3] if len(values) > 3 else self.pump_rpm

                # Physical simulation logic:
                effective_flow = int((current_valve / 100.0) * (current_rpm / 3000.0) * 120)
                simulated_flow = max(0, effective_flow + random.randint(-2, 2))
                simulated_pressure = int(35 + (100 - current_valve) * 0.4 + random.randint(-1, 1))

                # Update live holding registers
                self.write_telemetry([simulated_pressure, simulated_flow, current_valve, current_rpm])
                self.pressure = simulated_pressure
                self.flow_rate = simulated_flow

                logger.info(
                    f"Telemetries -> Pressure: {simulated_pressure / 10.0:.1f} bar | "
                    f"Flow: {simulated_flow / 10.0:.1f} L/s | "
                    f"Valve: {current_valve}% | RPM: {current_rpm}"
                )

            except Exception as e:
                logger.error(f"Telemetry loop error: {e}")

            await asyncio.sleep(1.0)  # 1 Hz Industrial Polling rate


async def main():
    plc = VirtualIndustrialPLC()
    server_host = "127.0.0.1"
    server_port = 5020  # Virtual PLC Modbus Port

    logger.info(f"Starting VoltGuard Virtual PLC on {server_host}:{server_port}...")

    # Run Telemetry loop and Modbus Server concurrently
    await asyncio.gather(
        plc.run_telemetry_loop(),
        StartAsyncTcpServer(
            context=plc.context,
            address=(server_host, server_port)
        )
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("PLC Simulator stopped safely.")