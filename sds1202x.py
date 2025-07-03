from typing import Optional, List, Tuple
import socket
import time
import numpy as np

from commlog import CommLog

class SDS1202X:
    def __init__(
        self,
        addr: str,
        port: int = 5025,
        log_path: str = "/tmp/sds1202x.log",
    ):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((addr, port))
        self.log = CommLog(log_path)

        self.log.event("reset")
        self.cmd(b'*RST'); self.wait()
        self.log.event("set command header")
        self.cmd(b'CHDR SHORT')
        self.cmd(b'TRIG_MODE SINGLE')
        self.set_trig_lvl(0.5)
        self.cmd(b'MSIZ 140K')

        self.triggered = False

    def _send(self, cmd: bytes):
        self.sock.send(cmd)
        self.log.write("send", cmd)

    def _recv_line(self) -> bytes:
        line = b''
        while True:
            ch = self.sock.recv(1)
            self.log.write("recv", ch)
            if ch == b'\n':
                return line
            line += ch

    def cmd(self, cmd: bytes):
        self._send(cmd + b'\n')

    def wait(self):
        self.log.event("waiting")
        self.query(b"*OPC?")

    def query(self, query: bytes) -> bytes:
        self._send(query + b'\n')
        return self._recv_line()

    def rearm(self):
        self.log.event("arming")
        self.cmd(b"STOP")
        self.query(b"INR?") # clear register
        self.cmd(b"ARM")
        self.wait()

        self.log.event("waiting for arm")
        while True:
            inr = self.query(b"INR?")
            inr = int(inr.replace(b"INR ", b""))
            if inr & 0x1 != 0:
                self.log.event("pre-triggered")
                self.triggered = True
            if inr & 0x2000 != 0:
                self.log.event("armed")
                return

    def wait_for_trigger(self):
        if self.triggered:
            self.triggered = False
            return
        self.log.event("waiting for trigger")
        while True:
            inr = self.query(b"INR?")
            inr = int(inr.replace(b"INR ", b""))
            if inr & 1 == 1:
                self.log.event("triggered")
                return

    def conf_channel(
        self,
        ch_n: int,
        *,
        attn: Optional[int] = None,
        vdiv: Optional[float] = None,
    ):
        if attn != None:
            self.cmd(f"C{ch_n}:ATTN {attn}".encode())
        if vdiv != None:
            self.cmd(f"C{ch_n}:VDIV {vdiv}".encode())

    def set_timebase(self, t_secs: float):
        self.cmd(f"TDIV {t_secs*1e9}NS".encode())

    def set_trig_lvl(self, lvl: float):
        self.cmd(f'EX:TRIG_LEVEL {lvl}'.encode())

    def fetch_waveform(self, ch: int) -> Tuple[np.ndarray, np.ndarray]:
        vdiv_s = self.query(f"C{ch}:VDIV?".encode()).decode()
        vdiv = float(vdiv_s[2:].replace(":VDIV ", "")[:-1])
        voffset_s = self.query(f"C{ch}:OFFSET?".encode()).decode()
        voffset = float(voffset_s[2:].replace(":OFST ", "")[:-1])
        tdiv_s = self.query(f"TDIV?".encode()).decode()
        tdiv = float(tdiv_s.replace("TDIV ", "")[:-1])

        msize_s = self.query(b"MSIZ?").decode()
        msize_s = msize_s.replace("MSIZ ", "")
        if msize_s.endswith("M"):
            msize = int(msize_s[:-1]) * 1e6
        elif msize_s.endswith("K"):
            msize = int(msize_s[:-1]) * 1e3
        else:
            raise ValueError(b"unknown msize: {msize_s}")

        self.cmd(f"WFSU SP,1,NP,{msize},FP,0".encode())

        self.cmd(f"C{ch}:WF? DAT2".encode())
        hdr = self.sock.recv(len("C1:WF ALL,#"))
        self.log.write("wfhdr", hdr)
        nn = self.sock.recv(1)
        self.log.write("nn", nn)
        ns = self.sock.recv(int(nn.decode()))
        self.log.write("n", ns)
        n = int(ns.decode())

        # print(f"reading {n} data. vdiv = {vdiv}, voffset = {voffset}")
        data = b''
        while len(data) < n:
            data += self.sock.recv(n - len(data))
            # self.log.event(f"data len = {len(data)}")
            self.log.write(f"data with len = {len(data)}", data)

        nlnl = self.sock.recv(2)
        assert nlnl == b'\n\n', f"Expected data to end with \n\n, got {nlnl!r}"

        signed = [x if x < 128 else x - 255 for x in data]

        vs = np.array([x * vdiv / 25.0 - voffset for x in signed])
        ts = np.linspace(-tdiv * 7, tdiv * 7, len(vs))

        return ts, vs


if __name__ == "__main__":
    from prologix import Prologix
    from e3631a import E3633A
    import tqdm
    import matplotlib.pyplot as plt

    p = Prologix("/tmp/prologix.log", '10.30.42.1', 1234)
    e = E3633A(p, 2)
    e.disable_channel('')
    e.wait_for_complete()
    e.set_channel('', 8, 10)


    s = SDS1202X("10.30.200.237")

    print("SDS initialized. Setting up")
    s.conf_channel(1, attn=1, vdiv=5)
    s.set_timebase(20e-3)
    s.set_trig_lvl(0.5)
    s.wait()

    print("Arming")
    s.rearm()

    print("Pulsing PSU")

    e.enable_channel('')
    e.disable_channel('')
    # e.wait_for_complete()

    print("Waiting for trigger")
    s.wait_for_trigger()

    print("Fetching waveform...")
    l = s.fetch_waveform(1)
    plt.plot(l)
