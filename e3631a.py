# HP E3631A triple output DC power supply

from prologix import Prologix

PORT_6V = "P6V"
PORT_P25 = "P25V"
PORT_N25 = "N25V"

class E3631A:
    def __init__(
        self,
        comm: Prologix,
        addr: int,
    ):
        self.comm = comm
        self.addr = addr

    # This function does no quoting of text
    def show_on_display(self, text: str):
        self.comm.send_command(f':DISP:TEXT "{text}"'.encode(), self.addr)

    def reset_display(self):
        self.comm.send_command(f':DISP:TEXT:CLE'.encode(), self.addr)

    def set_channel(
        self,
        channel: str,
        voltage: float,
        current: float,
    ):
        assert channel in (PORT_6V, PORT_P25, PORT_N25)
        self.comm.send_command(f"APPL {channel}, {voltage}, {current}".encode(), self.addr)

    def enable_channel(
        self,
        channel: str,
    ):
        assert channel in (PORT_6V, PORT_P25, PORT_N25)
        self.comm.send_command(f"INST:SEL {channel}".encode(), self.addr)
        self.comm.send_command(f"OUTP:STAT ON".encode(), self.addr)

    def disable_channel(
        self,
        channel: str,
    ):
        assert channel in (PORT_6V, PORT_P25, PORT_N25)
        self.comm.send_command(f"INST:SEL {channel}".encode(), self.addr)
        self.comm.send_command(f"OUTP:STAT OFF".encode(), self.addr)

    def wait_for_complete(self):
        self.comm.send_command(b"*OPC?", self.addr)
        self.comm.read_until_eoi(self.addr)

# Single port variant
class E3633A:
    def __init__(
        self,
        comm: Prologix,
        addr: int,
    ):
        self.comm = comm
        self.addr = addr

    # This function does no quoting of text
    def show_on_display(self, text: str):
        self.comm.send_command(f':DISP:TEXT "{text}"'.encode(), self.addr)

    def reset_display(self):
        self.comm.send_command(f':DISP:TEXT:CLE'.encode(), self.addr)

    def set_channel(
        self,
        _channel: str,
        voltage: float,
        current: float,
    ):
        self.comm.send_command(f"APPL {voltage}, {current}".encode(), self.addr)

    def enable_channel(
        self,
        _channel: str,
    ):
        self.comm.send_command(f"OUTP:STAT ON".encode(), self.addr)

    def disable_channel(
        self,
        _channel: str,
    ):
        self.comm.send_command(f"OUTP:STAT OFF".encode(), self.addr)

    def wait_for_complete(self):
        self.comm.send_command(b"*OPC?", self.addr)
        self.comm.read_until_eoi(self.addr)

if __name__ == "__main__":
    import time, tqdm
    p = Prologix("/tmp/prologix.log", "10.30.42.1", 1234)
    e = E3631A(p, 5)
    # e.show_on_display(":3 :3 :3 :3 :3")
    e.enable_channel(PORT_6V)
    for i in tqdm.tqdm(range(60)):
        e.set_channel(PORT_6V, voltage=i/10, current=0.1)
        e.wait_for_complete()
