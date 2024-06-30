EnviroFun (in MicroPython)
==========================

This is a collection of MicroPython scripts for various
[Pimoroni](https://shop.pimoroni.com/) Enviro gadgets.

There's a bit of a mix of 'Pico On Board' and 'Pico Pack' options to choose
from; the code should normally be fairly freely transferable, but each script
specifies what it's been developed for and tested on.

As ever, this is all released under an MIT License (see LICENSE for details).

Share and Enjoy.

---

Enviro Pack
-----------

`enviropack-mqtt.py` is the offspring of a couple of the Pimoroni examples;
merging the nice display of `enviro_all.py` and the connectivity of 
`enviro_all_mqtt.py` (which, to be honest, doesn't look pretty). You can safely
rename this script as `main.py` to automatically run on startup; you will need
to ensure the following files are also copied over:

File|Purpose
----|-------
`enviropack-mqtt.rgb332`|Sprites used for the display


