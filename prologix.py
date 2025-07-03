from __future__ import annotations
from typing import Optional
import socket
import datetime
import time

from commlog import CommLog

# Prologix GPIB-Ethernet bridge communication layer

TIMEOUT = 0.1
EOT_BREAK_CHAR = 123

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

        # terminate all messages with a null byte
        # note that a message can contain a null byte already though.
        # so when we get a null byte we see if receiving another timeouts
        self.sock.send(b"++eot_enable 1\n")
        self.sock.send(f"++eot_char {EOT_BREAK_CHAR}\n".encode())

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

        # if no data has been received yet, ++read will do nothing.
        # thus we want to continually issue ++read until all data has been read
        received_data = b''
        data_hdr = f"Recv from {self.current_addr}"
        self.sock.send(b'++read eoi\n')
        while True:
            try:
                ch = self.sock.recv(1)
            except TimeoutError as e:
                # try to issue another ++read call
                self.log.event("Timeouted. Issuing another ++read")
                self.sock.send(b'++read eoi\n')
                continue
            self.log.write(data_hdr, ch)

            received_data += ch
            if ch[0] == EOT_BREAK_CHAR:
                self.log.event("Potential EOT break")
                try:
                    self.sock.settimeout(0.01) # fast timeout
                    ch = self.sock.recv(1)
                    self.log.event("Fake EOT, continuing")
                    received_data += ch
                    self.log.write(data_hdr, ch)
                except TimeoutError as e:
                    # we're properly done
                    self.log.event("EOT break was real")
                    return received_data[:-1] # remove EOT_BREAK_CHAR
                finally:
                    # reset the timeout
                    self.sock.settimeout(TIMEOUT)




        # while True:
        #     self.sock.send(b'++read eoi\n')

        #     while True:
        #         try:
        #             ch = self.sock.recv(1)
        #         except TimeoutError as e:
        #             self.log.event("Read failure. Retrying")
        #             time.sleep(TIMEOUT)
        #             continue

        #         self.log.write(f"Recv from {self.current_addr}", ch)
        #         if ch[0] == EOT_BREAK_CHAR:
        #             self.log.event("Got a null byte. Seeing if there's more data")

        #             try:
        #                 self.sock.settimeout(0.01) # short timeout
        #                 next_ch = self.sock.recv(1)
        #                 self.log.write(f"Recv from {self.current_addr}", next_ch)
        #                 res += ch
        #                 ch = next_ch
        #             except TimeoutError as e:
        #                 # we're done
        #                 self.log.event("Nope. We timeouted.")
        #                 return res
        #             finally:
        #                 self.sock.settimeout(TIMEOUT) # reset the timeout

        #             self.log.write(f"Recv from {self.current_addr}", ch)
        #         res += ch

    def device(self, addr: int) -> PrologixDevice:
        return PrologixDevice(self, addr)

class PrologixDevice:
    def __init__(self, comm: Prologix, addr: int):
        self.comm = comm
        self.addr = addr

    def send_command(self, cmd: bytes):
        self.comm.send_command(cmd, self.addr)

    def read_until_eoi(self):
        return self.comm.read_until_eoi(self.addr)

    def query(self, cmd: bytes):
        self.send_command(cmd)
        return self.read_until_eoi()


if __name__ == "__main__":
    p = Prologix("/tmp/prologix.log", '10.30.42.1', 1234)
    p.send_command(b'*IDN?', 2)
    print(p.read_until_eoi(2))
