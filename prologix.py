from typing import Optional
import socket
import datetime
import time

from commlog import CommLog

# Prologix GPIB-Ethernet bridge communication layer

TIMEOUT = 2

class Prologix:
    def __init__(
        self,
        log_path: str,
        ip: str,
        port: int = 1234,
    ):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((ip, port))
        self.current_addr = -1
        self.log = CommLog(log_path)
        self.sock.send(b"++auto 0\n") # don't auto-receive
        self.sock.send(b"++eos 2\n") # append LF to commands

        self.sock.settimeout(TIMEOUT)

    def _escape_cmd(
        self,
        text: bytes,
    ):
        res = b''
        for ch in text:
            if ch in b'\n\r\x1b+':
                res += b'\x1b'
            res += bytes([ch])
        return res

    def _address_device(
        self,
        addr: int,
    ):
        if self.current_addr != addr:
            self.sock.send(f"++addr {addr}\n".encode())
            self.current_addr = addr

    def send_command(
        self,
        cmd: bytes,
        addr: int,
    ):
        assert addr is not None
        if self.current_addr != addr:
            self._address_device(addr)
        send = self._escape_cmd(cmd) + b"\n"
        self.log.write(f"Send to {self.current_addr}", send)
        self.sock.send(send)

    def read_until_eoi(
        self,
        addr: int,
    ):
        if self.current_addr != addr:
            self._address_device(addr)
        while True:
            try:
                self.sock.send(b'++read eoi\n')
                res = b''
                while True:
                    ch = self.sock.recv(1)
                    self.log.write(f"Recv from {self.current_addr}", ch)
                    if ch == b'\x1b':
                        ch = self.sock.recv(1)
                        self.log.write(f"Recv from {self.current_addr}", ch)
                    if ch == b'\r':
                        self.sock.recv(1) # eat the \n
                        return res
                    if ch == b'\n':
                        return res
                    res += ch
            except TimeoutError as e:
                self.log.event("Read failure. Retrying")
                time.sleep(TIMEOUT)

if __name__ == "__main__":
    p = Prologix("/tmp/prologix.log", '10.30.42.1', 1234)
    p.send_command(b'*IDN?', 2)
    print(p.read_until_eoi(2))
