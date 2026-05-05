import io
import re
from datetime import datetime

import matplotlib.pyplot as plt
import streamlit as st


def parse_setonix_usage(fn: str, time: str):
    allocation = {}
    used_cpu, used_gpu = {}, {}
    percentage_cpu, percentage_gpu = {}, {}
    with open(fn, "r") as f:
        lines = f.readlines()[4:]
        split_idx = 0
        for x in lines:
            if "gpu" in x:
                split_idx = lines.index(x)
                break
        for x in lines[:split_idx]:
            user = x.split()[0]
            if user == "pawsey0420":
                allocation[user] = float(x.split()[1])
                used_cpu[user] = float(x.split()[2])
                percentage_cpu[user] = round(
                    float(used_cpu[user] / allocation[user] * 100), 1
                )
            else:
                used_cpu[user] = float(x.split()[1])
                percentage_cpu[user] = round(
                    float(used_cpu[user] / allocation["pawsey0420"] * 100), 1
                )
        for x in lines[split_idx:]:
            user = x.split()[0]
            if user == "pawsey0420-gpu":
                allocation[user] = float(x.split()[1])
                used_gpu[user] = float(x.split()[2])
                percentage_gpu[user] = round(
                    float(used_gpu[user] / allocation[user] * 100), 1
                )
            else:
                used_gpu[user] = float(x.split()[1])
                percentage_gpu[user] = round(
                    float(used_gpu[user] / allocation["pawsey0420-gpu"] * 100), 1
                )
    # return allocation, used_cpu, percentage_cpu, used_gpu, percentage_gpu
    data_raw_cpu = {k.replace("-", ""): v for k, v in used_cpu.items()}
    data_raw_cpu["remaining"] = allocation["pawsey0420"] - used_cpu["pawsey0420"]
    data_raw_cpu.pop("pawsey0420")
    data_percent_cpu = {k.replace("-", ""): v for k, v in percentage_cpu.items()}
    data_percent_cpu["remaining"] = 100 - percentage_cpu["pawsey0420"]
    data_percent_cpu.pop("pawsey0420")
    data_raw_gpu = {k.replace("-", ""): v for k, v in used_gpu.items()}
    data_raw_gpu["remaining"] = (
        allocation["pawsey0420-gpu"] - used_gpu["pawsey0420-gpu"]
    )
    data_raw_gpu.pop("pawsey0420gpu")
    data_percent_gpu = {k.replace("-", ""): v for k, v in percentage_gpu.items()}
    data_percent_gpu["remaining"] = 100 - percentage_gpu["pawsey0420-gpu"]
    data_percent_gpu.pop("pawsey0420gpu")

    return data_raw_cpu, data_percent_cpu, data_raw_gpu, data_percent_gpu


def parse_gadi_usage(fn: str, time: str):
    unit_map = {"SU": 1, "KSU": 1000, "MSU": 1000000}

    total = []
    split_idx = 0
    with open(fn, "r") as f:
        lines = f.readlines()
        for x in lines:
            if "MAS" in x:
                total = [
                    [float(x.split()[1]), x.split()[2]],
                    [float(x.split()[3]), x.split()[4]],
                ]

    user_usage = {}
    for x in lines:
        if re.match(r"[a-z]{2}[0-9]{4}", x):
            user_usage[x.split()[0]] = [float(x.split()[1]), x.split()[2]]

    for user, usage in user_usage.items():
        if usage[1] in unit_map:
            usage[0] *= unit_map[usage[1]]
            usage[1] = "SU"
        else:
            print(f"Unknown unit {usage[1]} for user {user}")
            continue
    for idx, (number, unit) in enumerate(total):
        if unit in unit_map:
            total[idx][0] *= unit_map[unit]
            total[idx][1] = "SU"
        else:
            print(f"Unknown unit {unit} for total")
            continue

    percentage_usage = {}
    for user, usage in user_usage.items():
        percentage_usage[user] = round(usage[0] / total[0][0] * 100, 1)

    data_raw = {k: v[0] for k, v in user_usage.items()}
    data_raw["remaining"] = total[0][0] - total[1][0]
    data_percent = {k: v for k, v in percentage_usage.items()}
    data_percent["remaining"] = (total[0][0] - total[1][0]) / total[0][0] * 100

    return data_raw, data_percent


def plot(
    data_raw: dict,
    data_percent: dict,
    today: str,
    cluster: str,
    ax,
    threshold: float = 5,
):
    assert set(data_raw.keys()) == set(
        data_percent.keys()
    ), "Keys of raw data and percentage data must be the same"
    data_raw = data_raw.copy()
    data_percent = data_percent.copy()
    percent_exceeding = 0
    if data_percent["remaining"] < 0:
        print(
            f"Warning: exeeding allocation on {cluster} by {-data_percent['remaining']:.1f}%"
        )
        percent_exceeding = -data_percent["remaining"]
        data_percent["remaining"] = 0
        data_raw["remaining"] = 0
    ax.pie(
        [v for v in data_percent.values()],
        labels=[k if v > threshold else "" for k, v in data_percent.items()],
        autopct=lambda p: f"{p:.1f}%" if p > threshold else "",
    )
    ax.legend(
        [f"{k}: {v:.1f}%" for k, v in zip(data_raw.keys(), data_percent.values())],
        bbox_to_anchor=(0.3, -1, 0.5, 1),
        title="As a percent of total allocation",
    )

    ax.set_title(
        f"{cluster} Usage on {today} \n as a percent of overall used,\n exceeding allocation by {percent_exceeding:.1f}%"
        if percent_exceeding > 0
        else f"{cluster} Usage on {today} \n as a percent of overall used"
    )


if __name__ == "__main__":

    st.set_page_config(layout="wide")
    st.subheader("Omara lab supercomputer usage", text_alignment="center")
    login_placeholder = st.empty()
    threshold = st.sidebar.slider("Hide slices below %", 0, 20, 5)

    if 'auth' not in st.session_state:
        st.session_state.auth = False

    if not st.session_state.auth:
        # --- LOGIN UI ---
        _, col2, _ = st.columns([1, 1, 1])
        with col2:
            user_input = st.text_input("Enter Password", type="password")
            if user_input == st.secrets["password"]:
                st.session_state.auth = True
                st.success("Access granted")
                st.rerun() # Reruns the script to clear the login UI
            elif user_input:
                st.error("Access denied")
        st.stop() # Prevents anything below from running until auth is True

    # --- ACTUAL APP CONTENT ---
    # This only runs if st.session_state.auth is True
    # (Your plotting logic here)
    col1, col2, col3 = st.columns([1, 1, 1])

    today = datetime.now().strftime("%Y-%m-%d")

    setonix_raw_cpu, setonix_percent_cpu, setonix_raw_gpu, setonix_percent_gpu = (
        parse_setonix_usage(f"data/{today}_setonix_usage.txt", today)
    )
    gadi_raw, gadi_percent = parse_gadi_usage(f"data/{today}_gadi_usage.txt", today)

    fig, axs = plt.subplots(1, 3, figsize=(18, 6), dpi=200)

    plot(gadi_raw, gadi_percent, today, "Gadi", axs[0], threshold=threshold)
    plot(
        setonix_raw_cpu,
        setonix_percent_cpu,
        today,
        "Setonix CPU",
        axs[1],
        threshold=threshold,
    )
    plot(
        setonix_raw_gpu,
        setonix_percent_gpu,
        today,
        "Setonix GPU",
        axs[2],
        threshold=threshold,
    )
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    _, mid_col, _ = st.columns([1, 6, 1])
    with mid_col:
        st.image(buf.getvalue(), use_container_width=True)
    st.markdown("---")
    st.markdown(
    "**Author: Frank, Emily**",
    )
