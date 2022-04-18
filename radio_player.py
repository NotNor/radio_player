 #!/usr/bin/env python

import re
import time
import evdev
import vlc
import threading
import queue
import os
from MY_TINY_FONT import TINY_FONT

from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, CP437_FONT, SINCLAIR_FONT, LCD_FONT

global timeout
timeout = 25200


class Station:
    def __init__(self, name, logo, link):
        self.name = name
        self.logo = logo
        self.link = link


class DeviceController:
    global B

    B = 1

    def __init__(self):

        self.R357 = Station(
            "Radio 357",
            [[0, B, B, B, B, 0, B, B, B, B, 0, B, B, B, B, 0],
             [0, 0, 0, 0, B, 0, B, 0, 0, 0, 0, 0, 0, 0, B, 0],
             [0, 0, 0, 0, B, 0, B, 0, 0, 0, 0, 0, 0, 0, B, 0],
             [0, B, B, B, B, 0, B, B, B, B, 0, 0, 0, 0, B, 0],
             [0, 0, 0, 0, B, 0, 0, 0, 0, B, 0, 0, 0, 0, B, 0],
             [0, 0, 0, 0, B, 0, 0, 0, 0, B, 0, 0, 0, 0, B, 0],
             [0, B, B, B, B, 0, B, B, B, B, 0, 0, 0, 0, B, 0],
             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]],
            "https://stream.rcs.revma.com/an1ugyygzk8uv")

        self.RNS = Station(
            "Radio Nowy Swiat",
            [[0, B, B, B, 0, 0, B, 0, 0, B, 0, 0, B, B, 0, 0],
             [0, B, 0, 0, B, 0, B, 0, 0, B, 0, 0, 0, 0, 0, 0],
             [0, B, 0, 0, B, 0, B, 0, 0, B, 0, B, B, B, B, 0],
             [0, B, B, B, 0, 0, B, B, 0, B, 0, B, 0, 0, 0, 0],
             [0, B, 0, 0, B, 0, B, 0, B, B, 0, B, B, B, B, 0],
             [0, B, 0, 0, B, 0, B, 0, 0, B, 0, 0, 0, 0, B, 0],
             [0, B, 0, 0, B, 0, B, 0, 0, B, 0, B, B, B, B, 0],
             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]],
            "https://stream.rcs.revma.com/ypqt40u0x1zuv")

        self.ROCKSERWIS = Station(
            "RockSerwis.fm",
            [[0, 0, 0, B, B, B, 0, 0, 0, B, B, 0, 0, 0, 0, 0],
             [0, 0, 0, B, 0, 0, B, 0, B, 0, 0, B, 0, 0, 0, 0],
             [0, 0, 0, B, 0, 0, B, 0, B, 0, 0, 0, 0, 0, 0, 0],
             [0, 0, 0, B, B, B, 0, 0, 0, B, B, 0, 0, 0, 0, 0],
             [0, 0, 0, B, 0, 0, B, 0, 0, 0, 0, B, 0, 0, 0, 0],
             [0, 0, 0, B, 0, 0, B, 0, B, 0, 0, B, 0, 0, 0, 0],
             [0, 0, 0, B, 0, 0, B, 0, 0, B, B, 0, 0, 0, 0, 0],
             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]],
            "https://stream9.nadaje.com:8003/live")
        self.stations = [self.R357, self.RNS, self.ROCKSERWIS]

        self.stations_iterator = iter(self.stations)

        self.media_player = Player(self.R357)

        self.led_cmds = queue.Queue()
        self.led_matrix = threading.Thread(target=LCD, args=(self.led_cmds, self.media_player))
        self.led_matrix.start()

    def execute(self, cmd):

        if cmd == "STOP":
            self.media_player.stop()
        else:
            if cmd == "PLAY":
                self.media_player.play()

            if cmd == "RNS":
                self.media_player.play(self.RNS)

            if cmd == "357":
                self.media_player.play(self.R357)

            if cmd == "NEXT":
                try:
                    self.media_player.play(next(self.stations_iterator))
                except:
                    self.stations_iterator = iter(self.stations)
                    self.media_player.play(next(self.stations_iterator))

            self.led_cmds.put(self.media_player.station)


def player_countdown(vlc_p):
    vlc_p.stop()


class Player:
    player = vlc.Instance("-I dummy --no-video --aout=alsa")
    media_player = player.media_player_new()

    t = threading.Timer(timeout, player_countdown, media_player)

    def __init__(self, station):
        self.station = station

    def play(self, station=None):
        if station is not None and self.station != station:
            self.set_station(station)
            self.media_player.play()
        elif not self.media_player.is_playing():
            self.media_player.play()

        self.t.cancel()
        self.t = threading.Timer(timeout, player_countdown, args=(self.media_player,))
        self.t.start()

    def set_station(self, station):
        self.media_player.set_media(self.player.media_new(station.link))
        self.station = station

    def stop(self):
        self.media_player.stop()

    def is_playing(self):
        return self.media_player.is_playing()


def LCD(station, media_player):
    serial = spi(port=0, device=0, gpio=noop())

    device = max7219(serial, 16, 8, None, 2, -90, False)
    device.contrast(192)

    CL = [[B, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, B],
          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
          [B, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, B]]

    timer = 0
    countdown = 600
    step = 0.3
    while True:

        if not station.empty():
            device.contrast(128)
            logo = station.get()
            if logo.logo != None:
                printBitmap(logo.logo, device)
            else:
                show_message(device, logo.name, fill="white", font=proportional(SINCLAIR_FONT))
            timer = time.time()

        if time.time() - timer < 4 and time.time() - timer > 3:
            dim(device)
            time.sleep(1)

        playtime = time.time() - timer

        if playtime > 4:
            if media_player.is_playing():
                if playtime < timeout - countdown:
                    device.contrast(0)
                    printBitmap(CL, device)
                    step = 0.5
                else:
                    device.contrast(255)
                    with canvas(device) as draw:
                        text(draw, (0, 0), str(-round(playtime) + timeout), fill="white", font=proportional(TINY_FONT))
                    step = 0.05
            else:
                device.clear()
                step = 1

        time.sleep(step)


def dim(device):
    for br_lvl in range(128, -1, -16):
        device.contrast(br_lvl)
        time.sleep(0.05)


def printBitmap(T, device):
    with canvas(device) as draw:
        for x in range(16):
            for y in range(8):
                if T[y][x] == 1:
                    draw.point((x, y), fill="white")
