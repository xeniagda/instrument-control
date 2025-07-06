# ETA Instrument Control

This repository contains Python code to interface with various instruments at ETA.

Some of the instruments are over serial over USB, some are over GPIB, which is
interfaced to over the [Prologis GPIB-to-Ethernet](https://prologix.biz/product/gpib-ethernet-controller)
adapter.

## Installation instructions

The code has not been packaged to a library in any way, so to use it, download the repository and
add the following to the start of your script

```py
import sys
sys.path.append("/path/to/repository")

from prologix import Prologix
... etc ...
```


## Prologix GPIB Ethernet Controller

To interface with the Prologix controller, import the Prologix object from `prologix.py`

```py
from prologix import Prologix
```

and instantiate the Prologix object and get a device

```py
prlx = Prologix(ip="10.30.42.1", port=1234) # GPIB-corner Prologix' IP
device = prlx.device(2) # A device handle to GPIB device with address 2
```

Typically, you'd instantiate a driver for an instrument here, see below for
details. You can also issue raw SCPI commands to the device. Note that all
strings are `b'...'` byte-strings

```py
device.query(b"*IDN?") # --> b'HEWLETT-PACKARD,E3633A,0,1.7-5.0-1.0\n'
device.send_command(b":DISP:TEXT HELLO WORLD")
```

All communication is logged to `/tmp/prologix.log` (can be changed using the
`log_path`-argument to the `Prologix` instance), where you can observe what data
is sent to and received from the device.

# Quick reference for instruments

## Agilent E363xA single/triple output DC power supply

```py
from prologix import Prologix
from e363xa import E363xA, Port

prlx = Prologix(...)
dev = prlx.device(5)

dc_psu = E363xA(dev)

# Either control all ports directly
dc_psu.set_voltage(3, Port.P25V) # Set P25V output to 3V
dc_psu.set_current(0.5, Port.P25V) # Set P25V output to 0.5A
dc_psu.output_on(Port.P25V)

# Or make an object for a port. Same as above, less verbose
p25 = dc_psu.port(Port.P25V)
p25.set_voltage(3)
p25.set_voltage(0.5)
p25.output_on()

# Before making any measurements, synchronize by waiting until the PSU has
# finished
dc_psu.wait_for_complete()
# or
p25.wait_for_complete()

# Turns off all channels
dc_psu.turn_off()

# Note:
# It can be wise to wrap your whole program in a try-finally-statement to
# turn off all channels at the end, even if the program errors
try:
    cool_measurement()
finally:
    dc_psu.turn_off()
```

## HP3478A Multimeter

```py
from prologix import Prologix
from hp3478a import HP3478A

prlx = Prologix(...)
dev = prlx.device(23)

mm = HP3478A(dev)

# Get voltage
mm.read_V() # --> 2.6123 (volts)
mm.read_I() # --> 2.21e-3 (amps)
```

Note the HP3478A doesn't use SCPI but some weird ass interface when communicating with it directly.

## HP7820A Vector network analyzer

This module interfaces with `scikit-rf`, make sure to have it install.

```py
from prologix import Prologix
from hp8720d import HP8720d
import skrf

prlx = Prologix(...)
dev = prlx.device(16)

vna = HP8720d(dev)

# Read the frequency from the vna
print(vna.freq) # 0.05-7.0 GHz, 201 pts

# Set frequency
# Note: this kills calibration!
vna.freq = skrf.Frequency(1, 3, 201, "GHz") # note: number of points must always be set to 201

# Measure S11
s11 = vna.measure_one_s(1, 1)
print(s11.shape, s11.dtype) # --> (201, ) "complex"

net = vna.full_twoport() # Returns a skrf.Network object with the measured data

# net.s is a numpy matrix of s-parameters
# net.s[:,0,0] is S11 for all frequency points, etc.
print(net.s.shape) # (201, 2, 2)
```
