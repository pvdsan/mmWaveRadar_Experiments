import numpy as np
import matplotlib.pyplot as plt
import configuration as config
import sys
import os
import cv2


def plot_range_and_power(reshapedFrame, config, frame_number, createPlotResultVideo):
    """
    Plot the range-Doppler map, range FFT, and relative power vs. range for a given frame.
    
    Args:
        reshapedFrame (ndarray): Reshaped frame data with dimensions (numTxAntennas, numRxAntennas, numLoopsPerFrame, numADCSamples).
        config (FrameConfig): Configuration object containing frame parameters.
        frame_number (int): Current frame number.
        createPlotResultVideo (int): Flag indicating whether to save plot images for video creation (1) or display the plot (0).
    """
    # Define the range resolution and Doppler resolution in meters
    range_resolution = config.RANGE_RESOLUTION
    doppler_resolution = config.DOPPLER_RESOLUTION
    
    # Define the maximum and minimum range in meters to display
    max_range_meters = 3
    min_range_meters = 0

    # Calculate the corresponding bin indices for the maximum and minimum range
    max_range_bins = int(max_range_meters / range_resolution)
    min_range_bins = int(min_range_meters / range_resolution)

    # Perform range FFT on the reshaped frame
    rangeFFTResult = rangeFFT(reshapedFrame, config)
    
    # Apply clutter removal along the third axis (numLoopsPerFrame)
    rangeFFTResult = clutter_removal(rangeFFTResult, axis=2)
    
    # Calculate the magnitude of the range FFT result
    rangeFFTResultMag = np.abs(rangeFFTResult)
    
    # Calculate the average range FFT magnitude across Tx and Rx antennas
    avgRangeFFTResultMagTX_RX = np.mean(rangeFFTResultMag, axis=(0, 1))
    
    # Calculate the average range FFT magnitude across Tx, Rx antennas, and chirps, used for relative power caluclation.
    avgRangeFFTResultMagTX_RX_Chirp = np.mean(rangeFFTResultMag, axis=(0, 1, 2))

    # Extract the power values within the specified range bins
    power = avgRangeFFTResultMagTX_RX_Chirp[min_range_bins:max_range_bins]
    
    # Calculate the relative power in dB
    relative_power = 10 * np.log10((power / np.max(power)))

    # Perform Doppler FFT on the range FFT result
    dopplerResult = dopplerFFT(rangeFFTResult, config)
    
    # Calculate the magnitude of the Doppler FFT result
    dopplerFFTResultMag = np.abs(dopplerResult)
    
    # Calculate the average Doppler FFT magnitude across Tx and Rx antennas
    avgDopplerFFTResultMag = np.sum(dopplerFFTResultMag, axis=(0, 1))
    
    # Calculate the range bins corresponding to the specified range
    range_bins = np.arange(min_range_bins, max_range_bins) * range_resolution

    # Get the number of chirps in the frame
    num_chirps = avgDopplerFFTResultMag.shape[0]
    
    # Calculate the velocity values corresponding to the Doppler bins
    velocity_values = np.arange(-num_chirps // 2, num_chirps // 2) * doppler_resolution

    # Create a figure with specified size
    plt.figure(figsize=(20, 4))

    # Plot the Range-Doppler Map
    plt.subplot(1, 3, 1)
    plt.imshow(avgDopplerFFTResultMag, cmap='viridis', aspect='auto') # use vmin and vmax parameters to adjust the visualization as per the data
    plt.colorbar(label='Magnitude (dB)')
    plt.title('Doppler-Range Map')
    plt.ylabel('Chirp Index')
    plt.xlim(min_range_bins, max_range_bins)

    # Plot the Range FFT
    plt.subplot(1, 3, 2)
    plt.imshow(avgRangeFFTResultMagTX_RX, cmap='viridis', aspect='auto') # use vmin and vmax parameters to adjust the visualization as per the data
    plt.colorbar(label='Magnitude (dB)')
    plt.title('Range FFT')
    plt.xlabel('Range Bins')
    plt.ylabel('Chirp Index')
    plt.xlim(min_range_bins, max_range_bins)

    # Plot the Relative Power vs. Range
    plt.subplot(1, 3, 3)
    plt.plot(range_bins, relative_power)
    plt.title('Relative Power vs. Range')
    plt.xlabel('Range (m)')
    plt.ylabel('Relative Power (dB)')
    plt.grid(True)
    plt.tight_layout()

    if createPlotResultVideo > 0:
        # Save the plot as an image file for video creation
        plt.savefig(f'output_images/frame_{frame_number:04d}.png')
        plt.close()
    else:
        plt.show()


class FrameConfig:
    """
    Configuration class for frame parameters.
    """
    def __init__(self):
        # Get configuration values from the configuration file (config)
        self.numTxAntennas = config.NUM_TX
        self.numRxAntennas = config.NUM_RX
        self.numLoopsPerFrame = config.LOOPS_PER_FRAME
        self.numADCSamples = config.ADC_SAMPLES
        self.numAngleBins = config.NUM_ANGLE_BINS

        # Calculate the number of chirps per frame
        self.numChirpsPerFrame = self.numTxAntennas * self.numLoopsPerFrame
        
        # Calculate the number of range bins (equal to the number of ADC samples)
        self.numRangeBins = self.numADCSamples
        
        # Calculate the number of Doppler bins (equal to the number of loops per frame)
        self.numDopplerBins = self.numLoopsPerFrame

        # Calculate the size of one chirp in samples
        self.chirpSize = self.numRxAntennas * self.numADCSamples
        
        # Calculate the size of one chirp loop in samples (3Tx has three chirps in one loop for TDM)
        self.chirpLoopSize = self.chirpSize * self.numTxAntennas
        
        # Calculate the size of one frame in samples
        self.frameSize = self.chirpLoopSize * self.numLoopsPerFrame


class RawDataReader:
    """
    Class for reading raw data from a binary file.
    """
    def __init__(self, path):
        self.path = path
        self.ADCBinFile = open(path, 'rb')

    def getNextFrame(self, frameconfig):
        """
        Read the next frame of data from the binary file.
        
        Args:
            frameconfig (FrameConfig): Configuration object containing frame parameters.
        
        Returns:
            ndarray: Frame data as a 1D numpy array of int16.
        """
        # Read one frame of data from the binary file
        frame = np.frombuffer(self.ADCBinFile.read(frameconfig.frameSize * 4), dtype=np.int16)
        return frame

    def close(self):
        """
        Close the binary file.
        """
        self.ADCBinFile.close()


def bin2np_frame(bin_frame):
    """
    Convert a binary frame to a complex numpy array.
    
    Args:
        bin_frame (ndarray): Binary frame data as a 1D numpy array of int16.
    
    Returns:
        ndarray: Complex numpy array representing the frame data.
    """
    # Create a complex numpy array of half the size of the binary frame
    np_frame = np.zeros(shape=(len(bin_frame) // 2), dtype=np.complex_)
    
    # Assign real and imaginary parts alternately from the binary frame
    np_frame[0::2] = bin_frame[0::4] + 1j * bin_frame[2::4]
    np_frame[1::2] = bin_frame[1::4] + 1j * bin_frame[3::4]
    
    return np_frame


def frameReshape(frame, frameConfig):
    """
    Reshape the frame data into a 4D array.
    
    Args:
        frame (ndarray): 1D numpy array representing the frame data.
        frameConfig (FrameConfig): Configuration object containing frame parameters.
    
    Returns:
        ndarray: Reshaped frame data with dimensions (numTxAntennas, numRxAntennas, numLoopsPerFrame, numADCSamples).
    """
    # Reshape the frame into a 4D array
    frameWithChirp = np.reshape(frame, (frameConfig.numLoopsPerFrame, frameConfig.numTxAntennas, frameConfig.numRxAntennas, -1))
    
    # Transpose the dimensions to (numTxAntennas, numRxAntennas, numLoopsPerFrame, numADCSamples)
    return frameWithChirp.transpose(1, 2, 0, 3)


def rangeFFT(reshapedFrame, frameConfig):
    """
    Perform range FFT on the reshaped frame data.
    
    Args:
        reshapedFrame (ndarray): Reshaped frame data with dimensions (numTxAntennas, numRxAntennas, numLoopsPerFrame, numADCSamples).
        frameConfig (FrameConfig): Configuration object containing frame parameters.
    
    Returns:
        ndarray: Range FFT result with the same dimensions as the input.
    """
    # Apply a window function to the reshaped frame data
    windowedBins1D = reshapedFrame
    
    # Perform FFT along the last axis (numADCSamples)
    rangeFFTResult = np.fft.fft(windowedBins1D)
    
    return rangeFFTResult


def clutter_removal(input_val, axis=0):
    """
    Perform static clutter removal along the specified axis.
    
    Args:
        input_val (ndarray): Input data array.
        axis (int): Axis along which to perform clutter removal (default: 0).
    
    Returns:
        ndarray: Clutter-removed data array with the same dimensions as the input.
    """
    # Reorder the axes to bring the specified axis to the front
    reordering = np.arange(len(input_val.shape))
    reordering[0] = axis
    reordering[axis] = 0
    input_val = input_val.transpose(reordering)
    
    # Calculate the mean along the first axis (specified axis after reordering)
    mean = input_val.mean(0)
    
    # Subtract the mean from the input data
    output_val = input_val - mean
    
    # Reorder the axes back to the original order
    return output_val.transpose(reordering)


def dopplerFFT(rangeResult, frameConfig):
    """
    Perform Doppler FFT on the range FFT result.
    
    Args:
        rangeResult (ndarray): Range FFT result with dimensions (numTxAntennas, numRxAntennas, numLoopsPerFrame, numADCSamples).
        frameConfig (FrameConfig): Configuration object containing frame parameters.
    
    Returns:
        ndarray: Doppler FFT result with the same dimensions as the input.
    """
    # Apply a Hamming window to the range FFT result along the third axis (numLoopsPerFrame)
    windowedBins2D = rangeResult * np.reshape(np.hamming(frameConfig.numLoopsPerFrame), (1, 1, -1, 1))
    
    # Perform FFT along the third axis (numLoopsPerFrame)
    dopplerFFTResult = np.fft.fft(windowedBins2D, axis=2)
    
    # Shift the zero-frequency component to the center of the spectrum along the third axis
    dopplerFFTResult = np.fft.fftshift(dopplerFFTResult, axes=2)
    
    return dopplerFFTResult


def create_video(image_folder, output_path, fps=5):
    """
    Create a video from a folder of image files.
    
    Args:
        image_folder (str): Path to the folder containing the image files.
        output_path (str): Path to save the output video file.
        fps (int): Frames per second for the output video (default: 5).
    """
    # Get a sorted list of image files in the specified folder
    images = [img for img in os.listdir(image_folder) if img.endswith(".png")]
    images.sort()

    # Read the first image to get the frame dimensions
    frame = cv2.imread(os.path.join(image_folder, images[0]))
    height, width, layers = frame.shape

    # Create a VideoWriter object for saving the output video
    video = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

    # Iterate over the image files and write them to the video
    for image in images:
        video.write(cv2.imread(os.path.join(image_folder, image)))

    # Release the VideoWriter object
    video.release()


def main():

    # Print the range resolution, Doppler resolution, maximum range, and maximum Doppler from the configuration
    print(config.RANGE_RESOLUTION, config.DOPPLER_RESOLUTION, config.MAX_RANGE, config.MAX_DOPPLER)

    # Initialize the flag for creating a plot result video
    createPlotResultVideo = 0
    
    # Get the binary file name from the command-line arguments
    bin_filename = sys.argv[1]
    
    # Check if a second command-line argument is provided for creating a plot result video
    if len(sys.argv) > 2:
        createPlotResultVideo = int(sys.argv[2])
    
    # Create the output directory for saving plot images if creating a plot result video
    if createPlotResultVideo > 0:
        os.makedirs('output_images', exist_ok=True)

    # Create a RawDataReader object for reading the binary file
    bin_reader = RawDataReader(bin_filename)
    
    # Create a FrameConfig object for storing frame parameters
    config = FrameConfig()

    # Process a specified number of frames (adjust the range as needed)
    for frame in range(0, 100):
        # Read the next frame from the binary file
        bin_frame = bin_reader.getNextFrame(config)
        
        # Convert the binary frame to a complex numpy array
        np_frame = bin2np_frame(bin_frame)
        
        # Reshape the frame data into a 4D array
        reshapedFrame = frameReshape(np_frame, config)
        
        # Plot the range-Doppler map, range FFT, and relative power vs. range for the current frame
        plot_range_and_power(reshapedFrame, config, frame, createPlotResultVideo)

    # Create a video from the plot images if specified
    if createPlotResultVideo != 0:
        create_video('output_images', 'Plot_Results.mp4', fps=10)

    # Close the binary file reader
    bin_reader.close()


if __name__ == "__main__":
    main()