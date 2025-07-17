import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import matplotlib.patches as mpatches

# === CONFIG ===
SAVE_PATH = r"C:\Users\zhoul\Desktop\Hantek scope\Hantek Python API\python code"
SAVE_PATH = os.path.join(SAVE_PATH, "pico_I2C(400kHz)")
NUM_RUNS  = 10
CHANNELS  = ['CH1', 'CH4']
COLORS    = {'CH1': 'blue', 'CH4': 'green'}

# === 1) LOAD ALL RUNS ===
data = {ch: [] for ch in CHANNELS}
time = None

for i in range(1, NUM_RUNS+1):
    fn = os.path.join(SAVE_PATH, f"pico_I2C_run{i:02d}.txt")
    df = pd.read_csv(fn, sep='\t')
    if time is None:
        time = df['Time(s)'].values
    for ch in CHANNELS:
        data[ch].append(df[ch].values)

# === 2) STACK & COMPUTE VOLTAGE MEAN/STD ===
stacked   = {ch: np.vstack(data[ch]) for ch in CHANNELS}  # shape (runs, samples)
mean_vals = {ch: np.mean(stacked[ch], axis=0) for ch in CHANNELS}
std_vals  = {ch: np.std (stacked[ch], axis=0) for ch in CHANNELS}

# === 3) PULSE DURATION ON THE MEAN TRACE ===
durations = {}
for ch in CHANNELS:
    mv     = mean_vals[ch]
    thr    = 0.5*(mv.min() + mv.max())
    high   = mv > thr
    diffs  = np.diff(high.astype(int))

    # rising = low→high, falling = high→low
    ris_idx = np.where(diffs ==  1)[0] + 1
    fal_idx = np.where(diffs == -1)[0] + 1
    # edge‐cases
    if high[0]:   ris_idx = np.insert(ris_idx,  0, 0)
    if high[-1]:  fal_idx = np.append( fal_idx, len(high)-1)

    dur = time[fal_idx] - time[ris_idx]
    durations[ch] = {'ris_idx': ris_idx, 'fal_idx': fal_idx, 'dur': dur}

    # print
    print(f"\n=== {ch} pulse durations ===")
    for i, d in enumerate(dur,1):
        print(f" Pulse #{i}: {d*1e6:6.2f} µs")
    #print(f" → mean = {dur.mean()*1e6:6.2f} µs ± {dur.std()*1e6:6.2f} µs")

# === 4) EDGE‑TIME JITTER ACROSS RUNS ===
jitter = {}
for ch in CHANNELS:
    run_r, run_f = [], []

    for run in range(NUM_RUNS):
        v    = stacked[ch][run]
        thr  = 0.5*(v.min() + v.max())
        high = v > thr
        diffs = np.diff(high.astype(int))

        ris = np.where(diffs ==  1)[0] + 1
        fal = np.where(diffs == -1)[0] + 1
        if high[0]:  ris = np.insert(ris,  0, 0)
        if high[-1]: fal = np.append( fal, len(high)-1)

        run_r.append(time[ris])
        run_f.append(time[fal])

    run_r = np.vstack(run_r)   # (runs, pulses)
    run_f = np.vstack(run_f)

    r_mean = run_r.mean(axis=0)
    f_mean = run_f.mean(axis=0)
    r_std  = run_r.std(axis=0)
    f_std  = run_f.std(axis=0)

    jitter[ch] = {
        'r_mean': r_mean, 'f_mean': f_mean,
        'r_std' : r_std,  'f_std' : f_std
    }

    # print
    print(f"\n=== {ch} edge-time jitter ===")
    for i,(rm, rs, fm, fs) in enumerate(zip(r_mean, r_std, f_mean, f_std),1):
        print(f" Pulse #{i}: rising-σ = {rs*1e6:6.2f} µs,  falling-σ = {fs*1e6:6.2f} µs")

# === 5) PLOT EVERYTHING ===
plt.figure(figsize=(12,6))

# a) raw runs + mean±std in voltage
for ch in CHANNELS:
    for run in range(NUM_RUNS):
        plt.plot(time, stacked[ch][run],
                 color=COLORS[ch], alpha=0.3,
                 label=f"{ch} Run {run+1}" if run==0 else None)
    plt.plot(time, mean_vals[ch],
             color=COLORS[ch], lw=2, label=f"{ch} Mean")
    # plt.fill_between(time,
    #                  mean_vals[ch]-std_vals[ch],
    #                  mean_vals[ch]+std_vals[ch],
    #                  color=COLORS[ch], alpha=0.2,
    #                  label=f"{ch} ±1 Std V")

# # b) horizontal shading for edge‑time jitter
# for ch in CHANNELS:
#     col = COLORS[ch]
#     jm = jitter[ch]
#     for i, (rm, rs, fm, fs) in enumerate(zip(jm['r_mean'], jm['r_std'],
#                                            jm['f_mean'], jm['f_std'])):
#         # rising edge jitter
#         plt.axvspan(rm-rs, rm+rs, ymin=0, ymax=1,
#                     color=col, alpha=0.15,
#                     label=f"{ch} rising ±1σ" if i==0 else "")
#         # falling edge jitter
#         plt.axvspan(fm-fs, fm+fs, ymin=0, ymax=1,
#                     color=col, alpha=0.15,
#                     label=f"{ch} falling ±1σ" if i==0 else "")
#         # # mark the mean edge times
#         # plt.axvline(rm, color=col, ls='--', lw=1)
#         # plt.axvline(fm, color=col, ls='--', lw=1)

# tidy up
plt.title("Channel 1 & 4: Pulse Durations + Edge-Time Jitter with 400kHz I2C")
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.gca().xaxis.set_major_locator(MaxNLocator(nbins=20))
plt.xticks(rotation=45)
plt.legend(ncol=2, fontsize='small', loc='upper right')
plt.tight_layout()
plt.show()
