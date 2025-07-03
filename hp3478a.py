# HP3489A Multimeter
# Does NOT use SCPI

from prologix import Prologix
import time

class HP3478A:
    def __init__(
        self,
        comm: Prologix,
        addr: int,
    ):
        self.comm = comm
        self.addr = addr

        self.mode = None

        # go to autorange
        self.comm.send_command(b"RA", self.addr)
        # show 5+1/2 digits
        self.comm.send_command(b"N5", self.addr)
        # wait for trigger command
        self.comm.send_command(b"T4", self.addr)

    def show_on_display(self, text: str):
        self.comm.send_command(b"D2" + text.encode(), self.addr)

    def reset_display(self):
        self.comm.send_command(b"D1", self.addr)

    def _mode_DC_V(self):
        if self.mode != "DC_V":
            self.mode = "DC_V"
            self.comm.send_command(b"F1", self.addr)

    def _mode_DC_I(self):
        if self.mode != "DC_I":
            self.mode = "DC_I"
            self.comm.send_command(b"F5", self.addr)

    def _preread_V(self):
        self._mode_DC_V()
        self.comm.send_command(b"T3", self.addr) # single trigger

    def _preread_I(self):
        self._mode_DC_I()
        self.comm.send_command(b"T3", self.addr) # single trigger

    def _postread(self) -> float:
        return float(self.comm.read_until_eoi(self.addr))

    def read_V(self) -> float:
        self._preread_V()
        # time.sleep(0.3)
        return self._postread()

    def read_I(self) -> float:
        self._preread_I()
        # time.sleep(0.3)
        return self._postread()


if __name__ == "__main__":
    import time
    import tqdm
    p = Prologix("/tmp/prologix.log", "10.30.42.1", 1234)
    m = HP3478A(p, 23)
    m.show_on_display(":3 :3 :3 :3 :3")
    time.sleep(1)
    m.reset_display()
    for i in tqdm.tqdm(range(30)):
        m.read_V()
        # print("Got voltage", m.read_V())
