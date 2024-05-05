import numpy as np
import sounddevice as sd

# Generate a 140 Hz sinusoidal waveform
fs = 44100  # Sampling frequency
duration = 100  # seconds
t = np.linspace(0, duration, int(fs * duration), endpoint=False)
frequency = 600
waveform =   np.sin(2 * np.pi * frequency * t)  # 0.5 to reduce the amplitude

# Play the waveform
sd.play(waveform, fs)
sd.wait()
