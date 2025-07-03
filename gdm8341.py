import serial

# You need drivers from https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
# And set the baudrate under MENU-IO-USB-BAUD to 115200
class GDM8341:
    def __init__(
        self,
        path="/dev/tty.GDM834X_VCP",
        print_debug=False,
    ):
        self.port = serial.Serial(
            path,
            baudrate=115200,
            timeout=10,
        )
        self.print_debug = print_debug

    def print_(self, *args):
        if self.print_debug:
            print("   [*]", *args, end="", flush=True)
    def print(self, *args):
        if self.print_debug:
            print(*args)

    # Send a command, wait until it's executed
    def do(self, cmd):
        self.port.write(cmd + b"\n*OPC?\n")
        self.port.readline()

    def query(self, cmd):
        self.port.write(cmd + b"\n")
        return self.port.readline()[:-2] # strip CRLF

    def get_idn(self):
        return self.query(b"*IDN?")

    # rng is measurement range and is ceil'd to the nearest range
    # (i.e. rng = 2 sets range to 5V)
    def measure_dc_voltage(self, rng: float):
        return float(self.query(b"MEASure:VOLTage:DC? %g" % rng).decode())

    def measure_dc_current(self, rng: float):
        return float(self.query(b"MEASure:CURRent:DC? %g" % rng).decode())

if __name__ == "__main__":
    print("Connecting...")
    mult = GDM8341(print_debug=True)
    print("Querying IDN...")
    print(mult.get_idn())
    for i in range(100):
        print("Voltage:", mult.measure_dc_voltage(5), "V")
    # for i in range(10):
    #     print("Current:", mult.measure_dc_current(0.5)*1e3, "mA")
