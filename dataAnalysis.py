import numpy as np
import matplotlib.pyplot as plt
import glob

# --- SETTINGS ---
num_runs = 5
file_pattern = "oscilloscope_data_run*.txt"
output_stats_file = "CH1_mean_std.txt"

# --- LOAD DATA ---
all_time = []
all_ch1 = []

files = sorted(glob.glob(file_pattern))[:num_runs]
if len(files) < num_runs:
    raise Exception(f"Expected {num_runs} files, found only {len(files)}.")

for f in files:
    data = np.loadtxt(f, skiprows=1)  # skip header
    t, ch1, *_ = data.T  # only time and CH1
    all_time.append(t)
    all_ch1.append(ch1)

# Check time alignment
base_time = all_time[0]
for t in all_time[1:]:
    if not np.allclose(t, base_time, rtol=1e-5, atol=1e-8):
        raise Exception("Time axes across runs are not aligned.")

# Stack and compute mean/std
stacked_ch1 = np.vstack(all_ch1)
mean_ch1 = np.mean(stacked_ch1, axis=0)
std_ch1 = np.std(stacked_ch1, axis=0)

# --- SAVE TO FILE ---
with open(output_stats_file, "w") as f:
    f.write("Time(s)\tCH1_Mean(V)\tCH1_Std(V)\n")
    for t, mean, std in zip(base_time, mean_ch1, std_ch1):
        f.write(f"{t:.10e}\t{mean:.6f}\t{std:.6f}\n")

print(f"Mean and standard deviation saved to {output_stats_file}")

# --- PLOT ---
plt.figure(figsize=(10, 5))
plt.plot(base_time, mean_ch1, label='CH1 Mean', color='blue')
plt.fill_between(base_time, mean_ch1 - std_ch1, mean_ch1 + std_ch1,
                 alpha=0.3, color='blue', label='CH1 ±1σ')
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.title("CH1 Mean ± Std Deviation over 5 Runs")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
