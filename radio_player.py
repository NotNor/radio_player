# !/usr/bin/env python
import time
import threading
import itertools
from enum import Enum
import mpv

from math import floor

from MY_TINY_FONT import TINY_FONT
from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, CP437_FONT, SINCLAIR_FONT, LCD_FONT

from radio_stations_config import radio_stations

global timeout
timeout = 25200


class Action(Enum):
    STOP = 1
    PLAY = 2
    TOGGLE_PAUSE = 3
    NEXT = 4
    SEEK_B = 5
    SEEK_F = 6
    SHOW = 7
    LIVE = 8


class RadioStation:
    def __init__(self, name, link, logo=None):
        self.name = name
        self.link = link
        self.logo = logo


class DeviceController:
    def __init__(self):
        self.streams_iterator = itertools.cycle(
            [StreamPlayer(RadioStation(radio_station[0], radio_station[1], radio_station[2])) for radio_station in radio_stations])
        self.current_stream = next(self.streams_iterator)
        self.event = threading.Event()
        self.led_matrix = threading.Thread(target=lcd_controller, args=(self.event, self))
        self.led_matrix.start()

    def execute(self, cmd):
        if cmd == Action.STOP:
            self.current_stream.mute()
            self.current_stream.reset_pos()
        else:
            if cmd == Action.PLAY:
                self.current_stream.unmute()
                self.event.set()

            if cmd == Action.TOGGLE_PAUSE:
                if self.current_stream.is_paused():
                    self.current_stream.unpause()
                else:
                    self.current_stream.pause()

            if cmd == Action.NEXT:
                self.current_stream.mute()
                self.current_stream.reset_pos()
                self.current_stream.unpause()
                self.current_stream = next(self.streams_iterator)
                self.current_stream.unmute()
                self.event.set()

            if cmd == Action.SEEK_B:
                self.current_stream.seek(-30)

            if cmd == Action.SEEK_F:
                self.current_stream.seek(30)

            if cmd == Action.SHOW:
                self.current_stream.unmute()
                self.event.set()

            if cmd == Action.LIVE:
                self.current_stream.reset_pos()
                self.current_stream.unpause()


class StreamPlayer:
    def __init__(self, station):
        self.station = station
        self.stream_player = mpv.MPV()
        self.stream_player._set_property("ao", "pulse")
        self.stream_player.play(station.link)
        self.mute()
        self.stream_player._set_property("force-seekable", True)
        time.sleep(3)
        self.reset_pos()

    def unmute(self):
        self.stream_player._set_property("volume", 100)

    def mute(self):
        self.stream_player._set_property("volume", 0)

    def is_muted(self):
        return self.stream_player._get_property("volume") == 0

    def is_paused(self):
        return self.stream_player.core_idle

    def is_playing(self):
        return len(self.stream_player.playlist_filenames) == 1

    def pause(self):
        self.stream_player._set_property("pause", True)

    def unpause(self):
        self.stream_player._set_property("pause", False)

    def seek(self, seconds):
        seek_timestamp = self.stream_playback_pos() + seconds
        if 0 < seek_timestamp < self.stream_end_timestamp():
            self.stream_player.seek(seconds)
            return seconds
        elif seek_timestamp < 0:
            self.stream_player.seek(0, reference="absolute")
        else:
            self.reset_pos()
        return 0

    def reset_pos(self):
        self.stream_player.seek(self.stream_end_timestamp(), reference="absolute")

    def stream_end_timestamp(self):
        return floor(self.stream_player.demuxer_cache_state.get('cache-end') - 5)

    def stream_playback_pos(self):
        return floor(self.stream_player._get_property("playback-time"))

    def stream_lag_seconds(self):
        return int(floor(self.stream_end_timestamp() - self.stream_playback_pos()))

    def stream_lag_string(self):
        lag = self.stream_lag_seconds()
        hours = lag // 3600
        minutes = lag % 3600 // 60
        seconds = lag % 3600 % 60

        if hours > 0:
            return f'-{hours:02}:{minutes:02}:{seconds:02}'
        elif minutes > 0:
            return f'-{minutes:02}:{seconds:02}'
        else:
            return f'-{seconds:02}'


def lcd_controller(event, device_controller):
    led = LED()

    while True:
        if event.is_set():
            event.clear()
            led.brightness_high()
            led.print_bitmap(device_controller.current_stream.station.logo)
            led.dim(event)
        elif device_controller.current_stream.is_paused() or device_controller.current_stream.stream_lag_seconds() > 3:
            led.print(device_controller.current_stream.stream_lag_string())
        elif device_controller.current_stream.is_muted():
            led.blank()
        else:
            led.brightness_low()
            led.active()

        time.sleep(0.3)


class LED():

    def __init__(self):
        self.serial = spi(port=0, device=0, gpio=noop())
        self.device = max7219(self.serial, 16, 8, None, 2, -90, False)
        self.device.contrast(128)

    X = 1
    _ = 0

    PLAYING =  [[X,_,_,_,_,_,_,_,_,_,_,_,_,_,_,X],
                [_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
                [_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
                [_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
                [_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
                [_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
                [_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
                [X,_,_,_,_,_,_,_,_,_,_,_,_,_,_,X]]

    def active(self):
        self.print_bitmap(self.PLAYING)

    def blank(self):
        self.device.clear()

    def dim(self, event):
        time.sleep(1.5)
        for br_lvl in range(128, -1, -16):
            self.device.contrast(br_lvl)
            if not event.is_set():
                time.sleep(0.05)
            else:
                break

    def print_bitmap(self, logo):
        with canvas(self.device) as draw:
            for x in range(16):
                for y in range(8):
                    if logo[y][x] == 1:
                        draw.point((x, y), fill="white")

    def brightness_high(self):
        self.device.contrast(128)

    def brightness_low(self):
        self.device.contrast(0)

    def print(self, stream_lag_string):
        self.brightness_high()
        show_message(self.device, str(stream_lag_string), fill="white", font=proportional(TINY_FONT))
