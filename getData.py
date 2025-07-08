from ctypes import wintypes
from pickle import TRUE
import sys
import time
import json
from ctypes import *
import time
import numpy
import matplotlib.pyplot as plt
from ctypes import WinDLL
import os

################################################
#              DLL LOADING
################################################
DLL_PATH = r"C:\Users\zhoul\Desktop\Hantek scope\Hantek Python API\Dll\x64\HTHardDll.dll"
OBJdll = WinDLL(DLL_PATH)
#OBJdll = windll.LoadLibrary(r".\Dll\x64\HTHardDll.dll") # (64 bit)
# OBJdll = windll.LoadLibrary(r".\Dll\x86\HTHardDll.dll") # (32 bit)

################################################
#              CLASS DEFINITIONS
################################################
class RELAYCONTROL(Structure):
    _fields_ = [('bCHEnable', wintypes.BOOL * 4),
    ('nCHVoltDIV', wintypes.WORD * 4),
    ('nCHCoupling', wintypes.WORD * 4),
    ('bCHBWLimit', wintypes.BOOL * 4),
    ('nTrigSource', wintypes.WORD),
    ('bTrigFilt', wintypes.BOOL),
    ('nALT', wintypes.WORD)]

class DATACONTROL(Structure):
    _fields_ = [('nCHSet', wintypes.WORD), #0x0F in hexadecimal notation means all 4 channels are open
    ('nTimeDIV', wintypes.WORD),
    ('nTriggerSource', wintypes.WORD), #Trigger source
    ('nHTriggerPos', wintypes.WORD), #horizontal trigger position
    ('nVTriggerPos', wintypes.WORD), #Vertical trigger position
    ('nTriggerSlope', wintypes.WORD), #Use the rising edge as the trigger method
    ('nBufferLen', wintypes.ULONG), # the length of the collected data
    ('nReadDataLen', wintypes.ULONG), # the length of the read data
    ('nAlreadyReadLen', wintypes.ULONG), # the length that has been read, only used in scan scrolling
    ('nALT', wintypes.WORD), #Whether to trigger alternately. Note that alternate triggering is a software function
    ('nETSOpen', wintypes.WORD),
    ('nDriverCode', wintypes.WORD), # drive number
    ('nLastAddress', wintypes.ULONG), # record the last read end address of scan mode
    ('nFPGAVersion', wintypes.WORD)] #FPGA version number
    #('nAddressOffset', wintypes.WORD) #Trigger jitter plus offset

################################################
#              GLOBAL SETTINGS
################################################
BUFFER_LEN = 4096
SAVE_PATH = "./"
SAMPLE_TIMES = 5
# Define your sampling rate and voltage settings here
#0=2nS, 1=5nS, 2=10nS, 3=20nS, 4=50nS, 5=100nS, 6=200nS, 7=500nS, 8=1uS, 9=2uS, 10=5uS, 11=10uS, 12=20uS, 13=50uS, 14=100uS, 15=200uS, 16=500uS 
#17=1mS, 18=2mS, 19=5mS, 20=10mS, 21=20mS, 22=50mS, 23=100mS, 24=200mS, 25=500mS, 26=1S, 27=2S, 28=5S, 29=10S, 30=20S
#31=50S, 32=100S, 33=200S, 34=500S, 35=1000S
TIME_PER_DIVISION = 19
#0=2mV, 1=5mV, 2=10mV, 3=20mV, 4=50mV, 5=100mV, 6=200mV, 7=500mV, 8=1V, 9=2V, 10=5V, 11=10V (w/ x1 probe)
VOLTS_PER_DIVISION = 8
#OSCILLOSCOPE:
PROBE_MULTIPLIER = 1 # 1 or 10 x probe
ADC_CHANNEL_MODE = 1 #1, 2 or 4
ENABLED_CHANNELS = [1, 1, 1, 1]
CHANNEL_COUPLING = 0 # DC=0, AC=1
CHANS_MASK = 0x0F # 0x0F in hexadecimal notation means all 4 channels are open

TRIGGER_CHANNEL = 0 # CH1=0, CH2=1, CH3=2, CH4=3
TRIGGER_SLOPE = 0 # rising=0
TRIGGER_MODE = 0 # edge=0
TRIGGER_SWEEP = 1 # Auto trigger = 0, Normal trigger =1
TRIGGER_COUPLE = 0 # DC=0, AC=1
TRIGGER_V = 200 # Trigger Voltage (vertical)


TIME_MULT = [2E-9, 5E-9, 1E-8, 2E-8, 5E-8, 1E-7, 2E-7, 5E-7, 1E-6, 2E-6, 5E-6, 1E-5, 2E-5, 5E-5, 1E-4, 2E-4, 5E-4, 1E-3, 2E-3, 5E-3, 1E-2, 2E-2, 5E-2, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
SAMPLING_RATE_SINGLE = [1E9, 1E9, 1E9, 1E9, 1E9, 1E9, 1E9, 500E6, 250E6, 125E6, 50E6, 25E6, 12.5E6, 5E6, 2.5E6, 1.25E6, 500E3, 250E3, 125E3, 50E3, 25E3, 12.5E3, 5E3, 2.5E3, 1.25E3, 500, 250, 125, 50, 25, 12.5, 5, 2.5, 1.25, 0.5, 0.25]
SAMPLING_RATE_DUAL =   [500E6, 500E6, 500E6, 500E6, 500E6, 500E6, 500E6, 500E6, 250E6, 125E6, 50E6, 25E6, 12.5E6, 5E6, 2.5E6, 1.25E6, 500E3, 250E3, 125E3, 50E3, 25E3, 12.5E3, 5E3, 2.5E3, 1.25E3, 500, 250, 125, 50, 25, 12.5, 5, 2.5, 1.25, 0.5, 0.25]
SAMPLING_RATE_QUAD =   [250E6, 250E6, 250E6, 250E6, 250E6, 250E6, 250E6, 250E6, 250E6, 125E6, 50E6, 25E6, 12.5E6, 5E6, 2.5E6, 1.25E6, 500E3, 250E3, 125E3, 50E3, 25E3, 12.5E3, 5E3, 2.5E3, 1.25E3, 500, 250, 125, 50, 25, 12.5, 5, 2.5, 1.25, 0.5, 0.25]

VOLT_MULT = [0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10]
VOLT_DIVISIONS = 8
VOLT_RESOLUTION = 256 #8 bit ADC

CH_ZERO_POS = [128, 128, 128, 128] # vertical zero position 0-255 [CH1, CH2, CH3, CH4]

################################################
#            INITIALIZE VARIABLES
################################################

#SIGNAL GENERATOR
FREQUENCY = 17000 # Hz
AMPLITUDE = 1000 # mV-peak
OFFSET = 0 # mV
WAVE_TYPE = 0 #0=sine, 1=ramp, 2=square, 4=DC, 8=noise
WAVE_MODE = 0 #0=continuous wave, 1=single wave

################################################
#           DEVICE SETUP
################################################
def get_device_index():
    search = OBJdll.dsoHTSearchDevice
    search.argtypes = [POINTER(wintypes.WORD)]
    search.restype = wintypes.WORD

    devices = (wintypes.WORD * 32)()
    if search(devices) == 0:
        raise RuntimeError("No device found")

    for i, dev in enumerate(devices):
        if dev:
            return i
    raise RuntimeError("Device index not found")

def initialize_device(index):
    init = OBJdll.dsoInitHard
    init.argtypes = [wintypes.WORD]
    init.restype = wintypes.WORD
    if init(index) != 1:
        raise RuntimeError("Device initialization failed")

def configure_scope(index, rc, dc):
    OBJdll.dsoHTSetSampleRate(index, 0, byref(rc), byref(dc))
    OBJdll.dsoHTSetCHAndTrigger(index, byref(rc), dc.nTimeDIV)
    OBJdll.dsoHTSetRamAndTrigerControl(index, dc.nTimeDIV, dc.nCHSet, dc.nTriggerSource, 0)
    for i in range(4):
        OBJdll.dsoHTSetCHPos(index, rc.nCHVoltDIV[i], CH_ZERO_POS[i], i, 1)
    OBJdll.dsoHTSetVTriggerLevel(index, dc.nVTriggerPos, 4)
    OBJdll.dsoHTSetTrigerMode(index, TRIGGER_MODE, dc.nTriggerSlope, 0)

def collect_data(index):
    OBJdll.dsoHTStartCollectData(index, 1)
    while (OBJdll.dsoHTGetState(index) & 2) == 0:
        time.sleep(0.001)

def save_data_to_file(run_index, timeData, scaled):
    filename = os.path.join(SAVE_PATH, f"waveform_run{run_index}.txt")
    with open(filename, 'w') as f:
        f.write("Time(s)\tCH1(V)\tCH2(V)\tCH3(V)\tCH4(V)\n")
        for i in range(len(timeData)):
            f.write(f"{timeData[i]:.9e}\t" + "\t".join(f"{scaled[ch][i]:.6f}" for ch in range(4)) + "\n")
    print(f"Saved: {filename}")

def read_and_save(index, dc, run_index):
    CH = [(wintypes.WORD * BUFFER_LEN)() for _ in range(4)]
    OBJdll.dsoHTGetData(index, *map(byref, CH), byref(dc))

    fs = SAMPLING_RATE_SINGLE[TIME_PER_DIVISION]
    timeData = [i / fs for i in range(BUFFER_LEN)]
    scaled = [[] for _ in range(4)]

    for i in range(BUFFER_LEN):
        for ch in range(4):
            raw = CH[ch][i] - (255 - CH_ZERO_POS[ch])
            scaled[ch].append(raw * PROBE_MULTIPLIER * VOLT_MULT[VOLTS_PER_DIVISION] * VOLT_DIVISIONS / 256)

    save_data_to_file(run_index, timeData, scaled)

def main():
    rc = RELAYCONTROL(
        bCHEnable=(wintypes.BOOL * 4)(1, 1, 1, 1),
        nCHVoltDIV=(wintypes.WORD * 4)(*([VOLTS_PER_DIVISION] * 4)),
        nCHCoupling=(wintypes.WORD * 4)(0, 0, 0, 0),
        bCHBWLimit=(wintypes.BOOL * 4)(0, 0, 0, 0),
        nTrigSource=TRIGGER_CHANNEL,
        bTrigFilt=0,
        nALT=0
    )

    dc = DATACONTROL(
        nCHSet=0x0F,
        nTimeDIV=TIME_PER_DIVISION,
        nTriggerSource=TRIGGER_CHANNEL,
        nHTriggerPos=50,
        nVTriggerPos=TRIGGER_V,
        nTriggerSlope=TRIGGER_SLOPE,
        nBufferLen=BUFFER_LEN,
        nReadDataLen=BUFFER_LEN,
        nAlreadyReadLen=0,
        nALT=0
    )

    idx = get_device_index()
    initialize_device(idx)
    configure_scope(idx, rc, dc)

    for run in range(1, SAMPLE_TIMES + 1):
        print(f"\n--- Capturing Run {run} ---")
        collect_data(idx)
        read_and_save(idx, dc, run)

if __name__ == "__main__":
    main()