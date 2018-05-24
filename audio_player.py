#!/usr/bin/env python
# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import sys
import json
import numpy as np
from pydub import AudioSegment
from pydub.utils import make_chunks
import pyaudio
from threading import Lock, Thread

CHUNK_SIZE = 50
REDUCTION_FACTOR = 2000

class CursorPlayer(object):

    def __init__(self, audio, x, ax, rate):
        self.audio = audio
        self.seg = make_chunks(audio, CHUNK_SIZE)
        self.x = x
        self.ly = ax.axvline(color='k', alpha=0.25)
        self.isPlaying = False
        self.sem1 = Lock()
        self.sem2 = Lock()
        self.rate = rate

    def onclick(self, event):
        self.sem1.acquire()
        self.isPlaying = False
        self.sem1.release()
        self.sem2.acquire()
        x = event.xdata
        if event.button == 1 and x is not None:
            if x < 0:
                x = 0
            t = Thread(target=self.play, args=(self.seg, self.audio, x,))
            t.daemon = True
            self.sem1.acquire()
            if not self.isPlaying:
                self.isPlaying = True
                t.start()
            self.sem1.release()
        self.sem2.release()

    def play(self, seg, audio, pos):
        self.sem2.acquire()
        pos = pos/self.rate
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(audio.sample_width),
                        channels=audio.channels,
                        rate=audio.frame_rate,
                        output=True)
        for chunk in seg[int(pos * (1000/CHUNK_SIZE)):]:
            self.sem1.acquire()
            if not self.isPlaying:
                self.sem1.release()
                break
            else:
                self.sem1.release()
                t = Thread(target=self.move_cursor, args=(seg.index(chunk) * (20*(CHUNK_SIZE/100.)),))
                t.start()
                stream.write(chunk._data)
        stream.stop_stream()
        stream.close()
        p.terminate()
        self.sem2.release()

    def move_cursor(self, x):
        if x % (100 * (100./CHUNK_SIZE)) == 0:
            self.ly.set_xdata(x * self.rate / (100 * (100./CHUNK_SIZE)))
            t = Thread(target= plt.draw)
            t.start()

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
        self.ly.set_xdata(x)
        self.txt.set_text('sec = %1.0f' % (x/self.rate))
        plt.draw()

def play_audio(audio_file_path):
	audio_name = audio_file_path if not '/' in audio_file_path else audio_file_path.rsplit("/",1)[1]
	fig, ax = plt.subplots()
	plt.gcf().canvas.set_window_title(audio_name)
	audio = AudioSegment.from_file(audio_file_path)
	rate = audio.frame_rate
	signal = audio.get_array_of_samples()
	final_signal = []
	for i in range(len(signal)):
		if i % (audio.channels*REDUCTION_FACTOR) == 0:
			final_signal.append(signal[i])
	signal = np.array(final_signal)
	plt.plot(signal)
	cursor = SnaptoCursor(ax, range(len(signal)), rate/REDUCTION_FACTOR)
	plt.connect('motion_notify_event', cursor.mouse_move)
	print("Loading audio...")
	cursor_player = CursorPlayer(audio, range(len(signal)), ax, rate/REDUCTION_FACTOR)
	plt.connect('button_press_event', cursor_player.onclick)
	plt.show()

if __name__ == '__main__':
	if len(sys.argv) == 2:
		play_audio(sys.argv[1])
	else:
		print("Audio file path as param")

