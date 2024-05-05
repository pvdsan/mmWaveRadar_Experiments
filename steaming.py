import socket
import struct
import threading
import time
import array as arr
import numpy as np

# Adjust as per the config file used in plotData.py
ADC_PARAMS = {'chirps': 128,
              'rx': 4,
              'tx': 3,
              'samples': 256,
              'IQ': 2,
              'bytes': 2}
"""
ADC_PARAMS is a dictionary that stores the configuration parameters for the ADC (Analog-to-Digital Converter).
- 'chirps': Number of chirps per frame.
- 'rx': Number of receiving antennas.
- 'tx': Number of transmitting antennas.
- 'samples': Number of samples per chirp.
- 'IQ': Number of components (In-phase and Quadrature) per sample.
- 'bytes': Number of bytes per sample component.
"""

# STATIC
MAX_PACKET_SIZE = 4096
BYTES_IN_PACKET = 1456
"""
- MAX_PACKET_SIZE: Maximum size of a packet in bytes.
- BYTES_IN_PACKET: Number of bytes in each packet.
"""

# DYNAMIC
BYTES_IN_FRAME = (ADC_PARAMS['chirps'] * ADC_PARAMS['rx'] * ADC_PARAMS['tx'] *
                  ADC_PARAMS['IQ'] * ADC_PARAMS['samples'] * ADC_PARAMS['bytes'])
BYTES_IN_FRAME_CLIPPED = (BYTES_IN_FRAME // BYTES_IN_PACKET) * BYTES_IN_PACKET
PACKETS_IN_FRAME = BYTES_IN_FRAME / BYTES_IN_PACKET
PACKETS_IN_FRAME_CLIPPED = BYTES_IN_FRAME // BYTES_IN_PACKET
UINT16_IN_PACKET = BYTES_IN_PACKET // 2
UINT16_IN_FRAME = BYTES_IN_FRAME // 2
"""
- BYTES_IN_FRAME: Total number of bytes in a frame.
- BYTES_IN_FRAME_CLIPPED: Number of bytes in a frame after clipping to a multiple of BYTES_IN_PACKET.
- PACKETS_IN_FRAME: Number of packets in a frame.
- PACKETS_IN_FRAME_CLIPPED: Number of packets in a frame after clipping.
- UINT16_IN_PACKET: Number of 16-bit unsigned integers in a packet.
- UINT16_IN_FRAME: Number of 16-bit unsigned integers in a frame.
"""

class adcCapThread(threading.Thread):
    """
    A thread class for capturing ADC data.
    """
    def __init__(self, threadID, name, static_ip='192.168.33.30', adc_ip='192.168.33.180',
                 data_port=4098, config_port=4096, bufferSize=1500):
        """
        Initialize the adcCapThread.

        Args:
            threadID: ID of the thread.
            name: Name of the thread.
            static_ip: IP address of the static device.
            adc_ip: IP address of the ADC device.
            data_port: Port number for receiving data.
            config_port: Port number for configuration.
            bufferSize: Size of the buffer for storing frames.
        """
        threading.Thread.__init__(self)
        self.whileSign = True
        self.threadID = threadID
        self.name = name
        self.recentCapNum = 0
        self.latestReadNum = 0
        self.nextReadBufferPosition = 0
        self.nextCapBufferPosition = 0
        self.bufferOverWritten = True
        self.bufferSize = bufferSize
    
        # Create configuration and data destinations
        self.cfg_dest = (adc_ip, config_port)
        self.cfg_recv = (static_ip, config_port)
        self.data_recv = (static_ip, data_port)

        # Create sockets
        self.config_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        # Bind data socket to fpga
        self.data_socket.bind(self.data_recv)
        self.data_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2**27)

        # Bind config socket to fpga
        self.config_socket.bind(self.cfg_recv)

        self.bufferArray = np.zeros((self.bufferSize, BYTES_IN_FRAME//2), dtype=np.int16)
        self.itemNumArray = np.zeros(self.bufferSize, dtype=np.int32)
        self.lostPackeFlagtArray = np.zeros(self.bufferSize, dtype=bool)

    def run(self):
        """
        Run the thread.
        """
        self._frame_receiver()
    
    def _frame_receiver(self):
        """
        Receive frames from the ADC device.
        """
        # First capture -- find the beginning of a Frame
        self.data_socket.settimeout(10)
        lost_packets = False
        recentframe = np.zeros(UINT16_IN_FRAME, dtype=np.int16)
        while self.whileSign:
            packet_num, byte_count, packet_data = self._read_data_packet()
            after_packet_count = (byte_count + BYTES_IN_PACKET) % BYTES_IN_FRAME
            
            # The recent Frame begins at the middle of this packet
            if after_packet_count < BYTES_IN_PACKET:
                recentframe[0:after_packet_count//2] = packet_data[(BYTES_IN_PACKET-after_packet_count)//2:]
                self.recentCapNum = (byte_count + BYTES_IN_PACKET) // BYTES_IN_FRAME
                recentframe_collect_count = after_packet_count
                last_packet_num = packet_num
                break
                
            last_packet_num = packet_num
            
        while self.whileSign:
            packet_num, byte_count, packet_data = self._read_data_packet()
            # Fix up the lost packets
            if last_packet_num < packet_num - 1:                
                lost_packets = True
                print('\a')
                print("Packet Lost! Please discard this data.")
                exit(0)

            # Begin to process the recent packet
            # If the frame finished when this packet is collected
            if recentframe_collect_count + BYTES_IN_PACKET >= BYTES_IN_FRAME:                
                recentframe[recentframe_collect_count//2:] = packet_data[:(BYTES_IN_FRAME-recentframe_collect_count)//2]
                self._store_frame(recentframe)                
                self.lostPackeFlagtArray[self.nextCapBufferPosition] = False
                self.recentCapNum = (byte_count + BYTES_IN_PACKET) // BYTES_IN_FRAME
                recentframe = np.zeros(UINT16_IN_FRAME, dtype=np.int16)
                after_packet_count = (recentframe_collect_count + BYTES_IN_PACKET) % BYTES_IN_FRAME
                recentframe[0:after_packet_count//2] = packet_data[(BYTES_IN_PACKET-after_packet_count)//2:]
                recentframe_collect_count = after_packet_count
                lost_packets = False
            else:
                after_packet_count = (recentframe_collect_count + BYTES_IN_PACKET) % BYTES_IN_FRAME
                recentframe[recentframe_collect_count//2:after_packet_count//2] = packet_data
                recentframe_collect_count = after_packet_count                
            last_packet_num = packet_num
    
    def getFrame(self):
        """
        Get the next frame from the buffer.

        Returns:
            tuple: A tuple containing the frame data, frame number, and lost packet flag.
                   - If the buffer is overwritten, returns ("bufferOverWritten", -1, False).
                   - If waiting for a new frame, returns ("wait new frame", -2, False).
        """
        if self.latestReadNum != 0:
            if self.bufferOverWritten:
                return "bufferOverWritten", -1, False
        else: 
            self.bufferOverWritten = False
        nextReadPosition = (self.nextReadBufferPosition + 1) % self.bufferSize 
        if self.nextReadBufferPosition == self.nextCapBufferPosition:
            return "wait new frame", -2, False
        else:
            readframe = self.bufferArray[self.nextReadBufferPosition]
            self.latestReadNum = self.itemNumArray[self.nextReadBufferPosition]            
            lostPacketFlag = self.lostPackeFlagtArray[self.nextReadBufferPosition]
            self.nextReadBufferPosition = nextReadPosition
        return readframe, self.latestReadNum, lostPacketFlag
    
    def _store_frame(self, recentframe):
        """
        Store the recent frame in the buffer.

        Args:
            recentframe: The recent frame data.
        """
        self.bufferArray[self.nextCapBufferPosition] = recentframe                    
        self.itemNumArray[self.nextCapBufferPosition] = self.recentCapNum
        if (self.nextReadBufferPosition - 1 + self.bufferSize) % self.bufferSize == self.nextCapBufferPosition:
            self.bufferOverWritten = True
        self.nextCapBufferPosition += 1
        self.nextCapBufferPosition %= self.bufferSize

    def _read_data_packet(self):
        """
        Read a data packet from the ADC device.

        Returns:
            tuple: A tuple containing the packet number, byte count, and packet data.
        """
        data, addr = self.data_socket.recvfrom(MAX_PACKET_SIZE)
        packet_num = struct.unpack('<1l', data[:4])[0]

        byte_count = struct.unpack('>Q', b'\x00\x00' + data[4:10][::-1])[0]
        packet_data = np.frombuffer(data[10:], dtype=np.uint16)
        return packet_num, byte_count, packet_data