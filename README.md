# Introduction
This is a research project under MORSE Studio Georgia State University under Dr. Ashwin Ashok<br/>
The project aims to understand feasibility of using mmWave Radar setup to detect tiny drone imitating a fly/mosquito with the help of range, doppler and sound signatures of the object of interest<br/>
Special Thanks to Argha Sen, IIT Kharagpur, for allowing us to refer https://github.com/arghasen10/mmHER for the raw data streaming and parsing code using DCA1000EVM<br/>

----------------------------------------------------------------------------
## Hardware Setup
Step 1: Make sure the IWR6843ISK (mmWave board) is connected with the mmWAVEICBOOST and DCM1000EVM along with the swicthes as follows<br/>
![image](https://github.com/pvdsan/mmWaveRadar_Experiments/assets/22724124/acc04876-b1de-4abf-a143-d167ecd64a09)


Step 2: Make sure you have flashed the DCA1000EVM with the apt FPGA image using the Lattice Diamond Programmer.<br/>
See document: https://www.ti.com/lit/pdf/spruij4 under FPGA - SPI Flash Programming Mode

--------------------------------------------------------------------------------------------------------

## mmWave Studio Configuration Setup
Step 1: Run the dataCaptureScript.lua from the repository in the mmWave Studio
![image](https://github.com/pvdsan/mmWaveRadar_Experiments/assets/22724124/674d52f2-fef8-4baa-93cd-53734ee2757c)

Step 2: Once the script is done running, we are ready to capture data using the datacapture.py script.

-----------------------------------------------------------------------------

## Recording Data

Run the script with the desired duration of data capture in minutes as a command-line argument.
This will create a .bin file in the same directory which can be later used for plotting and analysis.
For example:

```bash
python data_capture.py 5
```


----------------------------------------------------------------------------

## Plotting the Data

Using the above created .bin file, to view the data frame by frame with going to the next frame using a keystroke, use the following usage<br\>
We set the 3rd argument as 0 indicating we do not need to capture a video of the results.

```bash
python plotData.py <filename.bin> 0 
``` 
The results should be as follows:<br\>
![Figure_1](https://github.com/pvdsan/mmWaveRadar_Experiments/assets/22724124/7ed59df4-a755-4ef3-a20a-03615cd20594)


----------------------------------------------------------------------------

# Running the Plot Results as a video






