#!/usr/bin/env python
# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import sys
import numpy as np
from pydub import AudioSegment
from pydub.utils import make_chunks
import pyaudio
from threading import Lock, Thread

CHUNK_SIZE = 100
REDUCTION_FACTOR = 100


class CursorPlayer(object):

    def __init__(self, audio, x, ax, rate):
        self.audio = audio
        self.seg = make_chunks(audio, CHUNK_SIZE)
        self.x = x
        self.ly = ax.axvline(color='k', alpha=0.25)
        self.isPlaying = False
        self.sem1 = Lock()
        self.sem2 = Lock()
        self.sem3 = Lock()
        self.rate = rate

    def onclick(self, event):
        with self.sem1:
            self.isPlaying = False
        with self.sem2:
            x = event.xdata
            if event.button == 1 and x is not None:
                if x < 0:
                    x = 0
                with self.sem1:
                    if not self.isPlaying:
                        self.isPlaying = True
                        t = Thread(target=self.play, args=(self.seg, self.audio, x,))
                        t.daemon = True
                        t.start()

    def play(self, seg, audio, pos):
        with self.sem2:
            p = pyaudio.PyAudio()
            stream = p.open(format=p.get_format_from_width(audio.sample_width),
                            channels=audio.channels,
                            rate=audio.frame_rate,
                            output=True)
            for i, chunk in enumerate(seg[int(pos * (1000 / CHUNK_SIZE)):]):
                self.sem1.acquire()
                if not self.isPlaying:
                    self.sem1.release()
                    break
                else:
                    self.sem1.release()
                    stream.write(chunk._data)
                    self.move_cursor((i * CHUNK_SIZE / 1000) + pos)
            stream.stop_stream()
            stream.close()
            p.terminate()

    def move_cursor(self, x):
        position = x
        self.ly.set_xdata([position, position])
        self.sem3.acquire()
        t = Thread(target=self.draw)
        t.start()

    def draw(self):
        plt.draw()
        self.sem3.release()


class SnaptoCursor(object):

    def __init__(self, ax, x, rate):
        self.ax = ax
        self.ly = ax.axvline(color='k', ls='dashed', alpha=0.75)
        self.x = x
        self.txt = ax.text(0.7, 0.9, '', transform=ax.transAxes)
        self.rate = rate

    def mouse_move(self, event):
        if not event.inaxes:
            return
        x = event.xdata
        if x < 0:
            x = 0
        self.ly.set_xdata([x, x])
        self.txt.set_text('sec = %1.0f' % (x / self.rate))
        plt.draw()


def play_audio(audio_file_path):
    audio_name = audio_file_path if not '/' in audio_file_path else audio_file_path.rsplit("/", 1)[1]
    fig, ax = plt.subplots()
    fig.canvas.manager.set_window_title(audio_name)
    audio = AudioSegment.from_file(audio_file_path)
    rate = audio.frame_rate
    signal = audio.get_array_of_samples()
    final_signal = []
    for i in range(len(signal)):
        if i % (audio.channels * REDUCTION_FACTOR) == 0:
            final_signal.append(signal[i])
    signal = np.array(final_signal)
    plt.plot(np.arange(0, len(signal)/audio.frame_rate*REDUCTION_FACTOR, 1/audio.frame_rate*REDUCTION_FACTOR), signal)
    cursor = SnaptoCursor(ax, range(len(signal)), rate / REDUCTION_FACTOR)
    plt.connect('motion_notify_event', cursor.mouse_move)
    print("Loading audio...")
    cursor_player = CursorPlayer(audio, range(len(signal)), ax, rate / REDUCTION_FACTOR)
    plt.connect('button_press_event', cursor_player.onclick)
    plt.show()


if __name__ == '__main__':
    if len(sys.argv) == 2:
        play_audio(sys.argv[1])
    else:
        print("Audio file path as param")
