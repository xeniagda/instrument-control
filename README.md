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


