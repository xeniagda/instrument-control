# HP E3631A triple output DC power supply

from __future__ import annotations
from enum import Enum, auto
from prologix import Prologix, PrologixDevice
from typing import Optional

class Port(Enum):
    # E3631A
    P6V = "P6V"
    P25V = "P25V"
    N25V = "N25V"

    # E3633A. Note these are different modes for the same port
    P8V20A = "P8V20A"
    P20V10A = "P20V10A"

class Variant(Enum):
    E3631A = "E3631A"
    E3633A = "E3633A"

    def has_port(self, port: Port) -> bool:
        if self == Variant.E3631A:
            return port in [Port.P6V, Port.P25V, Port.N25V]
        elif self == Variant.E3633A:
            return port in [Port.P8V20A, Port.P20V10A]

class E363xA:
    """
        An E3631A or E3633A DC power supply.

        To operate on a static port
            comm = Prologix(...)
            dc_psu = E363xA(comm.device(GPIB_PORT), Port.P6V)
            dc_psu.apply(voltage=3, current=0.01)
            dc_psu.output_on()

        To operate many ports on the same device,
            comm = Prologix(...)
            dc_psu = E363xA(comm.device(GPIB_PORT))
            dc_psu.apply(voltage=3, current=0.01, port=Port.P6V)
            dc_psu.apply(voltage=15, current=0.01, port=Port.P25V)
            dc_psu.output_on(port=Port.P6V)
            dc_psu.output_on(port=Port.P25V)
            ...
        to operate on multiple ports.

        Note that the E3633A has one port that can operate in two modes: 8V/20A or 20V/10A, rather than two physical ports.
    """
    def __init__(
        self,
        dev: PrologixDevice,
    ):
        """
            Create a E363xA device

            Parameters
            ----------
            dev: PrologixDevice
                Device to connect to. Use Prologix.device(GBIB_ADDR) to acquire.
        """
        # assert isinstance(dev, PrologixDevice), "First argument must be a prologix device object. Call .device(GPIB_PORT)."
        self.dev = dev

        idn = dev.query(b"*IDN?")
        if idn.startswith(b"HEWLETT-PACKARD,E3631A"):
            self.variant = Variant.E3631A
        elif idn.startswith(b"HEWLETT-PACKARD,E3633A"):
            self.variant = Variant.E3633A
        else:
            raise ValueError(f"Device is not in E363xA family: {idn}")

        # default port the device is on
        # invariant is that the device should always be set to this port at the end of all function calls
        self.current_port: Optional[Port] = None

    def show_on_display(self, text: str):
        """
            Show a message on screen. Note text is NOT escaped, meaning special characters cannot be displayed.

            Parameters
            ----------
            text: str
                Text to display
        """
        self.dev.send_command(f':DISP:TEXT "{text}"'.encode())

    def reset_display(self):
        """
            Clear display
        """
        self.dev.send_command(f':DISP:TEXT:CLE'.encode())

    def _set_port(self, port: Port):
        """
            Internal method to set the port
        """

        if port == self.current_port:
            # nothing to be done
            return

        if not self.variant.has_port(port):
            raise ValueError(f"Model {self.variant.name} does not support {port.name}")

        if port in (Port.P6V, Port.P25V, Port.N25V):
            self.dev.send_command(f"INST:SEL {port.name}".encode())
        elif port == Port.P20V10A:
            self.dev.send_command(b"VOLT:RANG P20V")
        elif port == Port.P8V20A:
            self.dev.send_command(b"VOLT:RANG P8V")
        else:
            raise ValueError(f"Unsupported port {port}")

        self.current_port = port

    def output_on(self, port: Port):
        """
            Enable an output

            Parameters
            ----------
            port: Port
                Port to enable
        """
        self._set_port(port)
        self.dev.send_command(f"OUTP:STAT ON".encode())

    def output_off(self, port: Port):
        """
            Disable an output

            Parameters
            ----------
            port: Port
                Port to disable
        """
        self._set_port(port)
        self.dev.send_command(f"OUTP:STAT OFF".encode())

    def turn_off(self):
        """
            Turns off all output ports
        """
        for port in Port:
            if self.variant.has_port(port):
                # TODO: This is a little stupid cause P20V10A and P8V20A don't both need to be turned off
                self.output_off(port)


    def set_voltage(self, voltage: float, port: Port):
        """
            Set the voltage on a channel. Note that there are no checks that the voltage is in range.

            Paremeters
            ----------
            voltage: float
                Voltage to apply in volts
            port: Port
                Port to set voltage on
        """
        self._set_port(port)
        # TODO: Check if the voltage is in range?
        # Check if return value is error?
        self.dev.send_command(f"VOLT {voltage}".encode())

    def set_current(self, current: float, port: Port=None):
        """
            Set the current on a channel. Note that there are no checks that the current is in range.

            Paremeters
            ----------
            current: float
                Current  to apply in amperes
            port: Port
                Port to set current on
        """
        self._set_port(port)
        self.dev.send_command(f"CURR {current}".encode())

    def wait_for_complete(self):
        """
            Waits until the device reports that it has completed all operations.
            If any errors have been received, they are printed to the console
        """
        while True:
            res = self.dev.query(b"SYSTem:ERRor?")
            code, msg = res.split(b",", 1)
            code = int(code.decode())
            msg = msg.decode().strip()
            if code != 0:
                print(f"ERROR: Got error code {code}: {msg}")
            else:
                break



    def port(self, port: Port) -> E363xAChannel:
        """
            A handle to a port on the device. Can be a lot nicer to work with

            Example
            -------
                prlgx = Prologix(...)
                device = E363xA(prlgx.device(12))
                port_6v = device.port(Port.P6V)
                port_25v = device.port(Port.P25V)

                port_6v.set_voltage(3)
                port_6v.set_current(1)
                port_6v.output_on()

                port_25v.set_voltage(2)
                port_25v.set_current(1)
                port_25v.output_on()

            Parameters
            ----------
            port: Port
                Port to acquire
        """
        return E363xAChannel(self, port)

class E363xAChannel:
    """
        A specific port on an E363xA.

        Example
        -------
            prlgx = Prologix(...)
            device = E363xA(prlgx.device(12))
            port_6v = device.port(Port.P6V)
            port_25v = device.port(Port.P25V)

            port_6v.set_voltage(3)
            port_6v.set_current(1)
            port_6v.output_on()

            port_25v.set_voltage(2)
            port_25v.set_current(1)
            port_25v.output_on()
    """
    def __init__(
        self,
        device: E363xA,
        port: Port,
    ):
        """
            Prefer using device.port(...) instead of this method

            Paremeters
            ----------
            device: E363xA
            port: Port
        """
        self.device = device
        self.port = port

    def output_on(self):
        """
            Enable the output
        """
        self.device.output_on(self.port)

    def output_off(self):
        """
            Disable the output
        """
        self.device.output_off(self.port)

    def set_voltage(self, voltage: float):
        """
            Set the voltage. Note that there are no checks that the voltage is in range.

            Paremeters
            ----------
            voltage: float
                Voltage to apply in volts
        """
        self.device.set_voltage(voltage, self.port)

    def set_current(self, current: float):
        """
            Set the current. Note that there are no checks that the current is in range.

            Paremeters
            ----------
            current: float
                Current to apply in amperes
        """
        self.device.set_current(current, self.port)

    def wait_for_complete(self):
        """
            Waits until the device reports that it has completed all operations.
        """
        self.device.wait_for_complete()

if __name__ == "__main__":
    import time, tqdm
    p = Prologix("10.30.42.1", 1234)

    def test_e3633a():

        print("[E3633A]")
        e3633a = E363xA(p.device(2))
        print("  Saying HELLO")
        e3633a.show_on_display("HELLO"); e3633a.wait_for_complete()
        time.sleep(1)
        print("  I AM E3633A")
        e3633a.show_on_display("I AM E3633A"); e3633a.wait_for_complete()
        time.sleep(1)
        print("  Resetting display")
        e3633a.reset_display(); e3633a.wait_for_complete()


        print("  Sweeping voltage and current directly")
        for i in range(5):
            e3633a.set_voltage(i+0.13, port=Port.P8V20A)
            e3633a.set_current(i+0.13, port=Port.P8V20A)
            e3633a.wait_for_complete()

        print("  Sweeping voltage using channel")
        ch = e3633a.port(Port.P20V10A)
        for i in range(5):
            ch.set_voltage(i + 0.62)
            ch.set_current(i + 0.62)
            ch.wait_for_complete()

        print("  Set the other channel")
        ch1 = e3633a.port(Port.P8V20A)
        ch1.set_voltage(7)
        ch1.set_current(13)
        ch1.wait_for_complete()

        print("  Set again the first channel")
        ch.set_voltage(15)
        ch.set_current(5)
        ch.wait_for_complete()

        e3633a.turn_off()

    def test_e3631a():

        print("[E3631A]")
        e3631a = E363xA(p.device(5))

        # print("  Saying HELLO")
        # e3631a.show_on_display("HELLO"); e3631a.wait_for_complete()
        # time.sleep(1)
        # print("  I AM E3633A")
        # e3631a.show_on_display("I AM E3633A"); e3631a.wait_for_complete()
        # time.sleep(1)
        # print("  Resetting display")
        # e3631a.reset_display(); e3631a.wait_for_complete()

        ch1 = e3631a.port(Port.P6V)
        ch2 = e3631a.port(Port.P25V)

        for i in range(5):
            ch1.set_voltage(i+0.13)
            ch1.set_current(i/2+0.13)

            ch2.set_voltage(i*2+0.13)
            ch2.set_current(i/10+0.13)

            e3631a.wait_for_complete()

        e3631a.turn_off()

    test_e3633a()
    # test_e3631a()
