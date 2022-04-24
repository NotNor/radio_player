# !/usr/bin/env python
import time
import evdev
from radio_player import Action, RadioController


def main():
    remote = evdev.InputDevice('/dev/input/event0')
    remote.grab()
    
    player = RadioController()
    timee = time.time()

    while True:
        for event in remote.read_loop():
            if event.timestamp() - timee > 0.3:
                if event.value == 0x45c:
                    player.execute(Action.NEXT)

                if event.value == 0x409:
                    player.execute(Action.SHOW)

                if event.value == 0x40c or event.value == 0x3f or event.value == 0x153f or event.value == 0x113f:
                    player.execute(Action.STOP)

                if event.value == 0x43f:
                    player.execute(Action.PLAY)

                if event.value == 0x458:
                    player.execute(Action.TOGGLE_PAUSE)

                if event.value == 0x45a:
                    player.execute(Action.SEEK_B)

                if event.value == 0x45b:
                    player.execute(Action.SEEK_F)

                if event.value == 0x459:
                    player.execute(Action.LIVE)

            timee = time.time()
main()
