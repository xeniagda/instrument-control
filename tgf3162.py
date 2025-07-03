import serial
import time
import numpy as np
import struct
import matplotlib.pyplot as plt

class TGF3162:
    def __init__(
        self,
        path="/dev/tty.usbmodemDA20526F1",
        print_debug=False,
    ):
        self.port = serial.Serial(path)
        self.print_debug = print_debug

    def print_(self, *args):
        if self.print_debug:
            print("   [*]", *args, end="", flush=True)

    def print(self, *args):
        if self.print_debug:
            print(*args)

    # Send a command, wait until it's executed
    def do(self, cmd):
        if self.print_debug:
            if len(cmd) < 20:
                print(f"   [TGF] Sending {cmd}")
            else:
                print(f"   [TGF] Sending {cmd[:20]}...")
        self.port.write(cmd + b"\n*OPC?\n")
        self.port.readline()

    def query(self, cmd):
        self.port.write(cmd + b"\n")
        return self.port.readline()[:-2] # strip CRLF

    def get_idn(self):
        return self.query(b"*IDN?")

    # Set load impedance in Ω. Between 1 to 10kΩ
    def set_z_load(self, z_load):
        self.print_(f"Setting Z_LOAD={z_load} Ω... ")
        self.do(b"ZLOAD %g" % z_load)
        self.print("done")

    # Sets open load
    def set_z_load_open(self):
        self.print_(f"Setting Z_LOAD=open...")
        self.do(b"ZLOAD OPEN")
        self.print("done")

    # Loads ARBn, n between 1 to 4, defaults to ARB1
    def load_arb(self, n=1):
        self.print_(f"Loading ARB{n}... ")
        self.do(b"ARBLOAD ARB%d" % n)
        self.print("done")

    # Name must be alphanumeric (I think). Will be uppercased
    def set_arb_name_interp(self, name, n=1, interpolation=True):
        interp = b"ON" if interpolation else b"OFF"
        self.print_(f"Renaming ARB{n} to {name} (interp={interp})...")
        self.do(b"ARBDEF ARB%d, %s, %s" % (n, name.encode(), interp))
        self.print("done")

    def load_dc(self, volts):
        self.do(b"ARBLOAD DC;DCOFFS %g" % volts)

    def set_channel(self, ch):
        self.print_(f"Setting channel to CH{ch}")
        self.do(b"CHN %d" % ch)
        self.print("done")

    def enable_output(self):
        self.print_(f"Enabling output...")
        self.do(b"OUTPUT ON")
        self.print("done")

    def disable_output(self):
        self.print_(f"Disabling output...")
        self.do(b"OUTPUT OFF")
        self.print("done")

    # amplitude in volts, 0-10Vpp
    def set_amplitude(self, hilvl, lolvl=0):
        # amplitude = float(amplitude)
        self.print_(f"Setting amplitude to HI = {hilvl:.3g}V, LO = {lolvl:.3g} V... ")
        self.do(b"HILVL %g;LOLVL %g" % (hilvl, lolvl))
        self.print("done")

    # Re-enables buttons
    def local_control(self):
        self.print("Enabling local control")
        self.do(b"LOCAL")

    # Waveform must be array of floats between 0 and 1
    # Maximum 8192 samples.
    # Must either specify sample_rate, Δt or length
    # sample_rate in Hz, Δt and length in in seconds
    # Enables the channel and sets the frequency
    def write_waveform(
        self,
        waveform,
        sample_rate=None,
        Δt=None,
        length=None,
        n=1,
    ):
        if len(waveform) > 8192:
            raise ValueError("Cannot upload more than 8192 samples to channel")
        waveform = np.array(waveform)

        if sample_rate is not None:
            f = sample_rate / len(waveform)
        elif Δt is not None:
            f = 1 / (Δt * len(waveform))
        elif length is not None:
            f = 1 / length
        else:
            raise ValueError("Specify one of sample_rate (Hz), Δt (s) or length (s)")

        self.print_(f"Set frequency to {f:.5g} Hz...")
        self.do(b"ARBLOAD ARB%d;FREQ %g;ARBRESIZE ARB%d %d" % (n, f, n, len(waveform)))

        self.print_(f"uploading {len(waveform)} points to ARB{n}...")

        data = np.array(waveform * (2**16 - 1) - 2**15, dtype="int16")
        data_bin = struct.pack(">%dh" % len(data), *data)

        self.port.write(b"ARB%d #5%05d%s\n" % (n, len(data_bin), data_bin))
        time.sleep(1)
        self.port.write(b"*OPC?\n")
        self.port.readline()
        self.print("done")

if __name__ == "__main__":
    wfg = TGF3162(print_debug=True)
    print(f"Connected, IDN = {wfg.get_idn()}")

    # Δt = 10e-9
    # N = 100
    # t = np.arange(0, Δt * N, Δt)
    # n = np.array(t / Δt, dtype="int")
    # y = (n * (n&6==0)) / N

    # wfg.write_waveform(
    #     y, Δt=Δt, n=1
    # )

    # wfg.local_control()

    wfg.load_dc(1.337)
    wfg.local_control()
