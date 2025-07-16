import os
import time
from ctypes import Structure, POINTER, byref, windll, wintypes
import numpy as np

# ── DLL LOADING ────────────────────────────────────────────────────────────────
DLL_PATH = r"C:\Users\zhoul\Desktop\Hantek scope\Hantek Python API\Dll\x64\HTHardDll.dll"
_scope   = windll.LoadLibrary(DLL_PATH)

# ── OUTPUT FOLDER ──────────────────────────────────────────────────────────────
SAVE_FOLDER = os.path.join(os.getcwd(), "pico_I2C(100kHz)")
os.makedirs(SAVE_FOLDER, exist_ok=True)

# ── CONSTANTS ──────────────────────────────────────────────────────────────────
BUFFER_LEN         = 4096
RUN_COUNT          = 5
# Define your sampling rate and voltage settings here
#0=2nS, 1=5nS, 2=10nS, 3=20nS, 4=50nS, 5=100nS, 6=200nS, 7=500nS, 8=1uS, 9=2uS, 10=5uS, 11=10uS, 12=20uS, 13=50uS, 14=100uS, 15=200uS, 16=500uS 
#17=1mS, 18=2mS, 19=5mS, 20=10mS, 21=20mS, 22=50mS, 23=100mS, 24=200mS, 25=500mS, 26=1S, 27=2S, 28=5S, 29=10S, 30=20S
#31=50S, 32=100S, 33=200S, 34=500S, 35=1000S
TIME_PER_DIVISION  = 15
#0=2mV, 1=5mV, 2=10mV, 3=20mV, 4=50mV, 5=100mV, 6=200mV, 7=500mV, 8=1V, 9=2V, 10=5V, 11=10V (w/ x1 probe)
VOLTS_PER_DIVISION = 8
PROBE_MULTIPLIER   = 1
CH_ZERO_POS        = [128, 128, 128, 128]

SAMPLING_RATE_SINGLE = [1E9, 1E9, 1E9, 1E9, 1E9, 1E9, 1E9, 500E6, 
                        250E6, 125E6, 50E6, 25E6, 12.5E6, 5E6, 2.5E6, 
                        1.25E6, 500E3, 250E3, 125E3, 50E3, 25E3, 12.5E3, 
                        5E3, 2.5E3, 1.25E3, 500, 250, 125, 50, 25, 12.5, 
                        5, 2.5, 1.25, 0.5, 0.25]

VOLT_MULT       = [0.002, 0.005, 0.01, 0.02, 0.05, 0.1,
                   0.2, 0.5, 1, 2, 5, 10]

# ── STRUCT DEFINITIONS ─────────────────────────────────────────────────────────
class RelayControl(Structure):
    _fields_ = [
        ("bCHEnable",   wintypes.BOOL * 4),
        ("nCHVoltDIV",  wintypes.WORD * 4),
        ("nCHCoupling", wintypes.WORD * 4),
        ("bCHBWLimit",  wintypes.BOOL * 4),
        ("nTrigSource", wintypes.WORD),
        ("bTrigFilt",   wintypes.BOOL),
        ("nALT",        wintypes.WORD),
    ]

class DataControl(Structure):
    _fields_ = [
        ("nCHSet",          wintypes.WORD),
        ("nTimeDIV",        wintypes.WORD),
        ("nTriggerSource",  wintypes.WORD),
        ("nHTriggerPos",    wintypes.WORD),
        ("nVTriggerPos",    wintypes.WORD),
        ("nTriggerSlope",   wintypes.WORD),
        ("nBufferLen",      wintypes.ULONG),
        ("nReadDataLen",    wintypes.ULONG),
        ("nAlreadyReadLen", wintypes.ULONG),
        ("nALT",            wintypes.WORD),
        ("nETSOpen",        wintypes.WORD),
        ("nDriverCode",     wintypes.WORD),
        ("nLastAddress",    wintypes.ULONG),
        ("nFPGAVersion",    wintypes.WORD),
    ]

# ── SCOPE INTERFACE ────────────────────────────────────────────────────────────
def get_device_index() -> int:
    search = _scope.dsoHTSearchDevice
    search.argtypes = [POINTER(wintypes.WORD)]
    search.restype  = wintypes.WORD

    devices = (wintypes.WORD * 32)()
    if search(devices) == 0:
        raise RuntimeError("No Hantek device found")
    for i, present in enumerate(devices):
        if present:
            return i
    raise RuntimeError("No valid device index returned")

def initialize_device(idx: int) -> None:
    init = _scope.dsoInitHard
    init.argtypes = [wintypes.WORD]
    init.restype  = wintypes.WORD
    if init(idx) != 1:
        raise RuntimeError("Device initialization failed")

def configure_scope(idx: int, rc: RelayControl, dc: DataControl) -> None:
    _scope.dsoHTSetSampleRate(idx, 0, byref(rc), byref(dc))
    _scope.dsoHTSetCHAndTrigger(idx, byref(rc), dc.nTimeDIV)
    _scope.dsoHTSetRamAndTrigerControl(idx,
        dc.nTimeDIV, dc.nCHSet, dc.nTriggerSource, 0)
    for ch in range(4):
        _scope.dsoHTSetCHPos(idx,
            rc.nCHVoltDIV[ch],
            CH_ZERO_POS[ch],
            ch, 1
        )
    _scope.dsoHTSetVTriggerLevel(idx, dc.nVTriggerPos, 4)
    _scope.dsoHTSetTrigerMode(idx, 0, dc.nTriggerSlope, 0)

def collect_data(idx: int) -> None:
    _scope.dsoHTStartCollectData(idx, 1)
    while (_scope.dsoHTGetState(idx) & 2) == 0:
        time.sleep(0.001)

def save_data(run: int, time_axis: np.ndarray, scaled: np.ndarray) -> None:
    """
    Write one run’s data to disk. Expects `scaled` shape = (BUFFER_LEN, 4).
    """
    fn = os.path.join(SAVE_FOLDER, f"pico_I2C_run{run:02d}.txt")
    with open(fn, "w") as f:
        f.write("Time(s)\tCH1\tCH2\tCH3\tCH4\n")
        for t, vals in zip(time_axis, scaled):
            line = "\t".join(f"{v:.6f}" for v in vals)
            f.write(f"{t:.9e}\t{line}\n")
    print(f"Saved: {fn}")

def read_and_save(idx: int, dc: DataControl, run: int) -> None:
    # 1) Allocate raw‐data buffers
    raw = [(wintypes.WORD * BUFFER_LEN)() for _ in range(4)]
    _scope.dsoHTGetData(
        idx,
        byref(raw[0]), byref(raw[1]),
        byref(raw[2]), byref(raw[3]),
        byref(dc)
    )

    # 2) Build time axis
    fs = SAMPLING_RATE_SINGLE[TIME_PER_DIVISION]
    time_axis = np.arange(BUFFER_LEN) / fs

    # 3) Scale into volts
    scaled = np.zeros((BUFFER_LEN, 4), dtype=float)
    vpdiv  = VOLT_MULT[VOLTS_PER_DIVISION] * PROBE_MULTIPLIER
    for i in range(BUFFER_LEN):
        for ch in range(4):
            raw_val       = raw[ch][i] - (255 - CH_ZERO_POS[ch])
            scaled[i, ch] = raw_val * vpdiv * 8 / 256

    # 4) Write it out
    save_data(run, time_axis, scaled)

def main():
    # Build control structs
    rc = RelayControl(
        bCHEnable=(wintypes.BOOL * 4)(1,1,1,1),
        nCHVoltDIV=(wintypes.WORD * 4)(*(VOLTS_PER_DIVISION,)*4),
        nCHCoupling=(wintypes.WORD * 4)(0,0,0,0),
        bCHBWLimit=(wintypes.BOOL * 4)(0,0,0,0),
        nTrigSource=0, bTrigFilt=0, nALT=0
    )

    dc = DataControl()
    # only set the fields you need; the rest stay at zero
    dc.nCHSet          = 0x0F
    dc.nTimeDIV        = TIME_PER_DIVISION
    dc.nTriggerSource  = 0
    dc.nHTriggerPos    = 50
    dc.nVTriggerPos    = 200
    dc.nTriggerSlope   = 0
    dc.nBufferLen      = BUFFER_LEN
    dc.nReadDataLen    = BUFFER_LEN
    dc.nAlreadyReadLen = 0
    dc.nALT            = 0
    dc.nETSOpen        = 0
    dc.nDriverCode     = 0
    dc.nLastAddress    = 0
    dc.nFPGAVersion    = 0

    idx = get_device_index()
    initialize_device(idx)
    configure_scope(idx, rc, dc)

    for run in range(1, RUN_COUNT + 1):
        print(f"--- Capturing Run {run}/{RUN_COUNT} ---")
        collect_data(idx)
        read_and_save(idx, dc, run)

if __name__ == "__main__":
    main()
