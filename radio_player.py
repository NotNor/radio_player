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
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional

from radio_stations_config import radio_stations


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


class RadioController:
    def __init__(self):
        self.streams_iterator = itertools.cycle(
            [StreamPlayer(RadioStation(radio_station[0], radio_station[1], radio_station[2])) for radio_station in radio_stations])
        self.current_stream = next(self.streams_iterator)
        self.show_logo = threading.Event()
        self.show_lag = threading.Event()
        self.display = threading.Thread(target=display_control, args=(self.show_logo, self.show_lag, self))
        self.display.start()

    def execute(self, cmd):
        try:
            if cmd == Action.STOP:
                self.current_stream.mute()
                self.current_stream.reset_pos()
            elif cmd == Action.PLAY:
                self.current_stream.unmute()
                self.show_logo.set()
            elif cmd == Action.TOGGLE_PAUSE:
                if self.current_stream.is_paused():
                    self.current_stream.unpause()
                else:
                    self.current_stream.pause()
            elif cmd == Action.NEXT:
                self.current_stream.mute()
                self.current_stream.reset_pos()
                self.current_stream.unpause()
                self.current_stream = next(self.streams_iterator)
                self.current_stream.unmute()
                self.show_logo.set()
            elif cmd == Action.SEEK_B:
                self.show_lag.set()
                self.current_stream.seek(-30)
            elif cmd == Action.SEEK_F:
                self.show_lag.set()
                self.current_stream.seek(30)
            elif cmd == Action.SHOW:
                self.current_stream.unmute()
                self.show_logo.set()
            elif cmd == Action.LIVE:
                self.current_stream.reset_pos()
                self.current_stream.unpause()
        except Exception as e:
            print(e)
            self.streams_iterator = itertools.cycle(
            [StreamPlayer(RadioStation(radio_station[0], radio_station[1], radio_station[2])) for radio_station in radio_stations])
            self.current_stream = next(self.streams_iterator)


class StreamPlayer:
    def __init__(self, station):
        self.station = station
        self.stream_player = mpv.MPV()
        self.stream_player._set_property("ao", "pulse")
        self.stream_player.play(station.link)
        self.mute()
        self.stream_player._set_property("force-seekable", True)
        time.sleep(5)
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
        #return len(self.stream_player.playlist_filenames) == 1
        print(self.stream_player._get_property("idle-active"))
        return self.stream_player._get_property("idle-active") != "true"

    def pause(self):
        self.stream_player._set_property("pause", True)

    def unpause(self):
        self.stream_player._set_property("pause", False)

    def seek(self, seconds):
        seek_timestamp = self.stream_playback_pos() + seconds
        if 0 < seek_timestamp < self.stream_end_timestamp():
            self.stream_player.seek(seconds)
        elif seek_timestamp < 0:
            self.stream_player.seek(0, reference="absolute")
        else:
            self.reset_pos()

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
            return f'-{hours}:{minutes:02}:{seconds:02}'
        elif minutes > 0:
            return f'-{minutes}:{seconds:02}'
        else:
            return f'-{seconds:02}'


def display_control(show_logo, show_lag, device_controller):
    display = LED_display()

    while True:
        try:
            if show_logo.is_set():
                show_logo.clear()
                display.brightness_high()
                display.print_bitmap(device_controller.current_stream.station.logo)
                display.dim(show_logo)
            elif device_controller.current_stream.is_paused():
                display.print(device_controller.current_stream.stream_lag_string())
            elif show_lag.is_set():
                show_lag.clear()
                display.print(device_controller.current_stream.stream_lag_string())
                show_lag.wait(1.5)
            elif device_controller.current_stream.is_muted():
                display.blank()
            else:
                display.brightness_low()
                display.screensaver()

            time.sleep(0.1)
        except Exception:
            continue


class LED_display:
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

    def screensaver(self):
        self.print_bitmap(self.PLAYING)

    def blank(self):
        self.device.clear()

    def dim(self, event):
        event.wait(2.5)
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
        self.device.contrast(64)
        # there's space for 5 chars on the 16x8 display
        if len(stream_lag_string) > 5:
            show_message(self.device, str(stream_lag_string), fill="white", font=proportional(TINY_FONT))
        else:
            # scrolling text across display
            with canvas(self.device) as draw:
                text(draw, (-1, 1), stream_lag_string, fill="white", font=proportional(TINY_FONT))
