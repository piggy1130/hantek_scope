import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib.ticker import MaxNLocator
import matplotlib.dates as mdates

# === CONFIG ===
SAVE_PATH = r"C:\Users\zhoul\Desktop\Hantek scope\Hantek Python API\python code"
NUM_RUNS = 5
CHANNELS = ['CH1', 'CH2']
COLORS = {'CH1': 'blue', 'CH2': 'green'}

# === LOAD DATA ===
data = {ch: [] for ch in CHANNELS}
time = None

for i in range(1, NUM_RUNS + 1):
    fname = os.path.join(SAVE_PATH, f"waveform_run{i}.txt")
    df = pd.read_csv(fname, sep='\t')
    if time is None:
        time = df['Time(s)'].values
    for ch in CHANNELS:
        data[ch].append(df[ch].values)

# === STACK, STATS ===
stacked = {ch: np.vstack(data[ch]) for ch in CHANNELS}
mean_vals = {ch: np.mean(stacked[ch], axis=0) for ch in CHANNELS}
std_vals = {ch: np.std(stacked[ch], axis=0) for ch in CHANNELS}


# === How long CH2 stays in the high-voltage ===
# === CH2 High Voltage Duration Calculation ===
threshold = 2.5  # Set a threshold between low and high states (e.g., 2.5 V)
ch2_mean = mean_vals['CH2']

# Identify high state using threshold
high_state = ch2_mean > threshold

# Find rising and falling edges
rising_edges = np.where(np.diff(high_state.astype(int)) == 1)[0]
falling_edges = np.where(np.diff(high_state.astype(int)) == -1)[0]

# Handle edge cases (e.g. if starts/ends high)
if falling_edges[0] < rising_edges[0]:
    falling_edges = falling_edges[1:]
if len(rising_edges) > len(falling_edges):
    rising_edges = rising_edges[:-1]

# Compute durations of each high state
high_durations = time[falling_edges] - time[rising_edges]


#print("Individual CH2 high pulse durations:", durations)
# Output results
for i, duration in enumerate(high_durations, 1):
    print(f"High voltage duration #{i}: {duration:.6f} seconds")




# === PLOT ALL IN ONE FIGURE ===
plt.figure(figsize=(12, 6))

for i in range(NUM_RUNS):
    plt.plot(time, stacked['CH1'][i], color='blue', alpha=0.3, label='CH1 Run' if i == 0 else "")
    plt.plot(time, stacked['CH2'][i], color='green', alpha=0.3, label='CH2 Run' if i == 0 else "")

plt.plot(time, mean_vals['CH1'], label='CH1 Mean', color='blue')
plt.fill_between(time, mean_vals['CH1'] - std_vals['CH1'], mean_vals['CH1'] + std_vals['CH1'],
                 color='blue', alpha=0.2, label='CH1 ±1 Std')

plt.plot(time, mean_vals['CH2'], label='CH2 Mean', color='green')
plt.fill_between(time, mean_vals['CH2'] - std_vals['CH2'], mean_vals['CH2'] + std_vals['CH2'],
                 color='green', alpha=0.2, label='CH2 ±1 Std')

plt.title("Channel 1 and Channel 2: 5 Runs + Mean ± Std Dev")
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.legend()
plt.grid(True)

# More x-ticks but still readable
plt.gca().xaxis.set_major_locator(MaxNLocator(nbins=20))  # reduce from 40 to avoid overcrowding
plt.xticks(rotation=45)  # rotate x-axis labels for readability

plt.tight_layout()
plt.show()
