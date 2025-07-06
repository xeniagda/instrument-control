from prologix import PrologixDevice
import skrf
import numpy as np

# network analyzer
class HP8720d:
    """
        HP8720d vector network analyzer
    """
    def __init__(self, dev: PrologixDevice):
        """
            Create a HP8720d device

            Parameters
            ----------
            dev: PrologixDevice
                Device to connect to. Use Prologix.device(GBIB_ADDR) to acquire.
        """
        # assert isinstance(device, PrologixDevice)
        self.dev = dev

        idn = self.dev.query(b"*IDN?")
        assert idn.startswith(b"HEWLETT PACKARD,8720D,"), f"Device seems to not be a HP8720d: {idn}"

        self.dev.send_command(b'CONT;') # continuous measurements
        self.dev.send_command(b'DEBUON;') # write commands to screen

    @property
    def freq_start(self):
        """
            Starting frequency in GHz
        """
        return float(self.dev.query(b'STAR;OUTPACTI;'))

    @freq_start.setter
    def freq_start(self, freq_hz):
        self.dev.send_command(f'STAR {freq_hz};'.encode())

    @property
    def freq_stop(self):
        """
            Stopping frequency in GHz
        """
        return float(self.dev.query(b'STOP;OUTPACTI;'))

    @freq_stop.setter
    def freq_stop(self, freq_hz):
        self.dev.send_command(f'STOP {freq_hz};'.encode())

    @property
    def npoints(self):
        """
            Number of frequency points
        """
        instrument_ret_val = self.dev.query(b'POIN;OUTPACTI;')
        return int(float(instrument_ret_val.decode().strip()))

    @property
    def frequency(self):
        return skrf.Frequency(self.freq_start/1e9, self.freq_stop/1e9, self.npoints, "GHz")

    @frequency.setter
    def frequency(self, freq: skrf.Frequency):
        # TODO: set number of points
        self.freq_start = freq.f[0]
        self.freq_stop = freq.f[-1]

    def measure_one_s(self, n, m) -> np.ndarray:
        """
            Measure the S_n,m port of the device
            Returns a complex numpy array of S-parameters over frequency
        """
        s_cmd = f"S{n}{m};"
        self.dev.send_command(s_cmd.encode())
        raw_data = self.dev.query(b"SING;FORM3;OUTPDATA;") # form3 = 64 bit floats
        data_points = np.frombuffer(raw_data[4:], dtype='>f8').reshape((-1, 2))
        data = data_points[:,0] + 1j * data_points[:,1]
        return data

    def full_twoport(self) -> skrf.Network:
        """
            Measure the full 2x2 S matrix of the device
            Returns the shape (n_points, 2, 2). S11 is [:,0,0], etc.
        """
        s11 = self.measure_one_s(1, 1)
        s12 = self.measure_one_s(1, 2)
        s21 = self.measure_one_s(2, 1)
        s22 = self.measure_one_s(2, 2)
        s = np.stack([[s11, s12], [s21, s22]]).transpose(2, 0, 1)
        return skrf.Network(frequency=self.frequency, s=s)
