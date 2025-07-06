# HP3489A Multimeter
# Does NOT use SCPI

from prologix import Prologix, PrologixDevice
import time

class HP3478A:
    def __init__(
        self,
        dev: PrologixDevice,
    ):
        self.dev = dev

        self.mode = None

        # go to autorange
        self.dev.send_command(b"RA")
        # show 5+1/2 digits
        self.dev.send_command(b"N5")
        # wait for trigger command
        self.dev.send_command(b"T4")

    def show_on_display(self, text: str):
        self.dev.send_command(b"D2" + text.encode())

    def reset_display(self):
        self.dev.send_command(b"D1")

    def _mode_DC_V(self):
        if self.mode != "DC_V":
            self.mode = "DC_V"
            self.dev.send_command(b"F1")

    def _mode_DC_I(self):
        if self.mode != "DC_I":
            self.mode = "DC_I"
            self.dev.send_command(b"F5")

    def _preread_V(self):
        self._mode_DC_V()
        self.dev.send_command(b"T3") # single trigger

    def _preread_I(self):
        self._mode_DC_I()
        self.dev.send_command(b"T3") # single trigger

    def _postread(self) -> float:
        return float(self.dev.read_until_eoi())

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
    m = HP3478A(p.device(23))
    m.show_on_display(":3 :3 :3 :3 :3")
    time.sleep(1)
    m.reset_display()

    bar = tqdm.tqdm(range(30))
    for i in bar:
        V = m.read_V()
        bar.set_description(f"V = {V:.2f} V")

    bar = tqdm.tqdm(range(30))
    for i in bar:
        I = m.read_I()
        bar.set_description(f"I = {I*1e6:.2f} μA")
