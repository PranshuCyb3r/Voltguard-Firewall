# Virtual PLC Network Connection
PLC_HOST = "127.0.0.1"
PLC_PORT = 5020          # Virtual Modbus TCP Port
FIREWALL_PORT = 5021     # Proxy Port (Traffic inspection)

# Modbus Register Map
REG_PUMP_SPEED    = 100  # Pump Speed (RPM)
REG_VALVE_POS     = 101  # Valve Position (0=Open, 100=Closed)
REG_LINE_PRESSURE = 102  # Pipeline Pressure (Bar)

# Physical Safety Limits (Physics-Aware Firewall)
MAX_PUMP_RPM       = 2400.0  # Isse zyada pump damage hoga
MAX_PRESSURE_BAR   = 16.0    # Pipe phatne ki limit
MAX_VALVE_SPEED    = 25.0    # % per second limit

# Decision Codes
VERDICT_ALLOW = "ALLOW"
VERDICT_DROP  = "DROP"