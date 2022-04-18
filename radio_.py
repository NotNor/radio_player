 
#!/usr/bin/env python
import re
import time
import evdev
import os

import radio_player

def demo():

    remote = evdev.InputDevice('/dev/input/event0')
    remote.grab()

    player = radio_player.DeviceController()
    timee = time.time()

    while True:
        for event in remote.read_loop():
            if event.timestamp() - timee > 0.3:
                if event.value ==  0x45c:
                    player.execute("NEXT")

                if event.value == 0x402:
                    player.execute("357")

                if event.value == 0x403:
                    player.execute("RNS")

                if event.value == 0x409:
                    player.execute("SHOW")

                if event.value == 0x40c or event.value == 0x3f or event.value == 0x153f or event.value == 0x113f:
                    player.execute("STOP")

                if event.value == 0x43f:
                    player.execute("PLAY")

            timee = time.time()
demo()
