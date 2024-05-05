import numpy as np

NUM_TX = 1 # tx order tx0,tx2,tx1, face to the board (left,right,upper) 
NUM_RX = 4

START_FREQ = 60 
ADC_START_TIME = 6 
FREQ_SLOPE = 90.018
ADC_SAMPLES = 256 # data samples per chirp
SAMPLE_RATE = 10000
RX_GAIN = 30 


IDLE_TIME = 100
RAMP_END_TIME = 40
#  2 for 1843
NUM_FRAMES = 0 
#  Set this to 0 to continuously stream data
LOOPS_PER_FRAME = 128 # num of chirp loop, one loop has three chirps
#PERIODICITY = 100 
# time for one chirp in ms  100ms == 10FPS
NUM_DOPPLER_BINS = LOOPS_PER_FRAME
NUM_RANGE_BINS = ADC_SAMPLES
NUM_ANGLE_BINS = 64
RANGE_RESOLUTION = (3e8 * SAMPLE_RATE * 1e3) / (2 * FREQ_SLOPE * 1e12 * ADC_SAMPLES)
MAX_RANGE = (300 * SAMPLE_RATE) / (2 * FREQ_SLOPE * 1e3)
DOPPLER_RESOLUTION = 3e8 / (2 * START_FREQ * 1e9 * (IDLE_TIME + RAMP_END_TIME) * 1e-6 * NUM_DOPPLER_BINS * NUM_TX)
MAX_DOPPLER = 3e8 / (4 * START_FREQ * 1e9 * (IDLE_TIME + RAMP_END_TIME) * 1e-6 * NUM_TX)
