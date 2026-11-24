import time, statistics, argparse
from mac_algorithms import get_mac, ALGORITHMS

KEY = bytes.fromhex("00112233445566778899aabbccddeeff")
RAPL = "/sys/class/powercap/intel-rapl:0/"

def read_energy_uj():
    """Package energy in microjoules (Linux/Intel/AMD). May need root; returns None if unavailable."""
    try:
        with open(RAPL + "energy_uj") as f:
            return int(f.read())
    except OSError:
        return None

def rapl_max():
    with open(RAPL + "max_energy_range_uj") as f:
        return int(f.read())

def energy_delta(e0, e1):
    return (e1 - e0) % rapl_max() if e0 is not None else None

def bench(mac, data, n, warmup=5000):
    for _ in range(warmup):
        mac.compute(data)

    # Pass 1: bulk loop -> throughput, CPU time, energy
    e0, c0, t0 = read_energy_uj(), time.process_time_ns(), time.perf_counter_ns()
    for _ in range(n):
        mac.compute(data)
    t1, c1, e1 = time.perf_counter_ns(), time.process_time_ns(), read_energy_uj()

    # Pass 2: per-call latency distribution
    lat = []
    for _ in range(min(n, 20000)):
        a = time.perf_counter_ns(); mac.compute(data); lat.append(time.perf_counter_ns() - a)
    lat.sort()

    return {
        "us_per_mac": (t1 - t0) / n / 1e3,
        "cpu_us_per_mac": (c1 - c0) / n / 1e3,
        "median_ns": statistics.median(lat),
        "p95_ns": lat[int(len(lat) * .95)],
        "stdev_ns": statistics.stdev(lat),
        "uJ_total": energy_delta(e0, e1),
        "wall_s": (t1 - t0) / 1e9,
    }

def idle_power_w(seconds=5):
    e0 = read_energy_uj(); time.sleep(seconds); e1 = read_energy_uj()
    return energy_delta(e0, e1) / 1e6 / seconds if e0 is not None else None

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=200_000)
    ap.add_argument("--tag-len", type=int, default=16)
    ap.add_argument("--repeats", type=int, default=5)
    args = ap.parse_args()

    data = (0x123).to_bytes(2, "big") + bytes(4)          # CAN ID + rpm + counter
    p_idle = idle_power_w()
    print("name,run,us_per_mac,cpu_us,median_ns,p95_ns,uJ_per_mac,net_uJ_per_mac")

    for run in range(args.repeats):
        for name in ALGORITHMS:
            if name == "none":
                continue
            r = bench(get_mac(name, KEY, args.tag_len), data, args.n)
            uj = r["uJ_total"] / args.n if r["uJ_total"] is not None else float("nan")
            net = ((r["uJ_total"] - p_idle * r["wall_s"] * 1e6) / args.n
                   if r["uJ_total"] is not None and p_idle is not None else float("nan"))
            print(f'{name},{run},{r["us_per_mac"]:.3f},{r["cpu_us_per_mac"]:.3f},'
                  f'{r["median_ns"]:.0f},{r["p95_ns"]:.0f},{uj:.4f},{net:.4f}')