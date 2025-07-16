#!/usr/bin/env python3
"""
Load multiple runs of scope data, compute pulse durations and jitter,
then print stats and plot raw traces + mean±std and shaded jitter bands.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

# ── CONFIG ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.getcwd()
DATA_DIR    = os.path.join(BASE_DIR, "pico_I2C(100kHz)")
NUM_RUNS    = 5
CHANNELS    = ["CH1", "CH4"]
COLORS      = {"CH1": "blue", "CH4": "green"}


def load_runs(data_dir: str, runs: int, channels: list) -> tuple:
    """Read each run’s file into a dict of arrays and return (time, data)."""
    data = {ch: [] for ch in channels}
    time = None

    for i in range(1, runs + 1):
        path = os.path.join(data_dir, f"pico_I2C_run{runs:02d}.txt")
        df = pd.read_csv(path, sep="\t")
        if time is None:
            time = df["Time(s)"].values
        for ch in channels:
            data[ch].append(df[ch].values)

    stacked = {ch: np.vstack(data[ch]) for ch in channels}
    return time, stacked


def compute_stats(stacked: dict) -> tuple:
    """Return (mean_vals, std_vals) dicts for each channel."""
    mean_vals = {ch: arr.mean(axis=0) for ch, arr in stacked.items()}
    std_vals  = {ch: arr.std(axis=0)  for ch, arr in stacked.items()}
    return mean_vals, std_vals


def detect_edges(mean_vals: dict, time: np.ndarray) -> dict:
    """
    Find rising/falling indices on the mean trace
    and compute each pulse’s duration.
    """
    durations = {}
    for ch, mv in mean_vals.items():
        thr = 0.5 * (mv.min() + mv.max())
        high = mv > thr
        diffs = np.diff(high.astype(int))

        ris_idx = np.where(diffs ==  1)[0] + 1
        fal_idx = np.where(diffs == -1)[0] + 1

        if high[0]:
            ris_idx = np.insert(ris_idx, 0, 0)
        if high[-1]:
            fal_idx = np.append(fal_idx, len(high) - 1)

        durations[ch] = {
            "ris": time[ris_idx],
            "fal": time[fal_idx],
            "dur": time[fal_idx] - time[ris_idx],
        }
    return durations


def compute_jitter(stacked: dict, time_axis: np.ndarray) -> dict:
    """
    For each channel, compute per‑pulse stddev of
    rising/falling times across runs.
    """
    jitter = {}
    for ch, arr in stacked.items():
        edge_times = {"ris": [], "fal": []}

        for run in range(arr.shape[0]):
            v = arr[run]
            thr = 0.5 * (v.min() + v.max())
            high = v > thr
            diffs = np.diff(high.astype(int))

            ris = np.where(diffs ==  1)[0] + 1
            fal = np.where(diffs == -1)[0] + 1

            if high[0]:
                ris = np.insert(ris, 0, 0)
            if high[-1]:
                fal = np.append(fal, len(high) - 1)

            edge_times["ris"].append(time_axis[ris])
            edge_times["fal"].append(time_axis[fal])

        ris_stack = np.vstack(edge_times["ris"])
        fal_stack = np.vstack(edge_times["fal"])

        jitter[ch] = {
            "r_mean": ris_stack.mean(axis=0),
            "f_mean": fal_stack.mean(axis=0),
            "r_std":  ris_stack.std(axis=0),
            "f_std":  fal_stack.std(axis=0),
        }
    return jitter


def print_stats(durations: dict, jitter: dict) -> None:
    """Print pulse durations and edge‑time jitter to console."""
    for ch in CHANNELS:
        d = durations[ch]["dur"]
        print(f"\n=== {ch} Pulse Durations ===")
        for i, dur in enumerate(d, 1):
            print(f" Pulse #{i}: {dur*1e6:.2f} µs")
        #print(f" → Mean = {d.mean()*1e6:.2f} µs ± {d.std()*1e6:.2f} µs")

    for ch in CHANNELS:
        js = jitter[ch]
        print(f"\n=== {ch} Edge‑Time Jitter ===")
        for i, (rs, fs) in enumerate(zip(js["r_std"], js["f_std"]), 1):
            print(
                f" Pulse #{i}: rising σ = {rs*1e6:.2f} µs, "+
                f"falling σ = {fs*1e6:.2f} µs"
            )


def plot_all(time, stacked, mean_vals, std_vals, durations, jitter):
    """Assemble the final figure: traces, mean±std, and jitter bands."""
    plt.figure(figsize=(12, 6))

    # Raw runs, mean, ±1σ
    for ch in CHANNELS:
        for run in range(NUM_RUNS):
            plt.plot(time, stacked[ch][run],
                     color=COLORS[ch], alpha=0.3,
                     label=f"{ch} Run" if run == 0 else "")
        plt.plot(time, mean_vals[ch],
                 color=COLORS[ch], lw=2, label=f"{ch} Mean")
        plt.fill_between(
            time,
            mean_vals[ch] - std_vals[ch],
            mean_vals[ch] + std_vals[ch],
            color=COLORS[ch], alpha=0.2,
            label=f"{ch} ±1σ"
        )

    # Jitter bands
    for ch in CHANNELS:
        j = jitter[ch]
        for rm, rs, fm, fs in zip(
            j["r_mean"], j["r_std"], j["f_mean"], j["f_std"]
        ):
            plt.axvspan(rm - rs, rm + rs, color=COLORS[ch],
                        alpha=0.15)
            plt.axvspan(fm - fs, fm + fs, color=COLORS[ch],
                        alpha=0.15)

    plt.title("Pulse Durations & Edge‑Time Jitter (CH1 & CH4)")
    plt.xlabel("Time (s)")
    plt.ylabel("Voltage (V)")
    plt.gca().xaxis.set_major_locator(MaxNLocator(nbins=20))
    plt.xticks(rotation=45)
    plt.legend(ncol=2, fontsize="small", loc="upper right")
    plt.tight_layout()
    plt.show()


def main():
    time, stacked      = load_runs(DATA_DIR, NUM_RUNS, CHANNELS)
    mean_vals, std_vals= compute_stats(stacked)
    durations          = detect_edges(mean_vals, time)
    jitter             = compute_jitter(stacked, time)

    print_stats(durations, jitter)
    plot_all(time, stacked, mean_vals, std_vals, durations, jitter)


if __name__ == "__main__":
    main()
