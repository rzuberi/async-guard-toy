"""Plotting utilities for generated experiment artifacts."""

from __future__ import division

import os
import tempfile
from collections import defaultdict

if "MPLCONFIGDIR" not in os.environ:
    mpl_cache = os.path.join(tempfile.gettempdir(), "async_guard_toy_mpl")
    if not os.path.isdir(mpl_cache):
        os.makedirs(mpl_cache)
    os.environ["MPLCONFIGDIR"] = mpl_cache

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


def plot_monitor_roc(roc_results, output_path):
    plt.figure(figsize=(6.4, 5.2))
    for name, payload in roc_results.items():
        label = "%s (AUC=%.3f)" % (name, payload["auc"])
        plt.plot(payload["fpr"], payload["tpr"], linewidth=2.2, label=label)
    plt.plot([0, 1], [0, 1], linestyle="--", color="#7f8c8d", linewidth=1.2)
    plt.xlabel("False positive rate")
    plt.ylabel("True positive rate")
    plt.title("Episode-level monitor ROC")
    plt.legend(frameon=False, loc="lower right")
    plt.tight_layout()
    plt.savefig(output_path, format="svg")
    plt.close()


def plot_score_trajectories(prefix_rows, output_path, score_key):
    grouped = defaultdict(list)
    for row in prefix_rows:
        episode_key = (row["episode_id"], row["label"])
        grouped[episode_key].append(row)

    benign_points = []
    sabotage_points = []
    for (_, label), rows in grouped.items():
        rows = sorted(rows, key=lambda item: item["step_index"])
        total = float(rows[-1]["step_index"])
        for row in rows:
            point = (row["step_index"] / total, row[score_key])
            if label == "benign":
                benign_points.append(point)
            else:
                sabotage_points.append(point)

    plt.figure(figsize=(6.4, 4.8))
    for points, label, color in (
        (benign_points, "Benign", "#1f77b4"),
        (sabotage_points, "Sabotage", "#d62728"),
    ):
        xs = np.asarray([item[0] for item in points], dtype=float)
        ys = np.asarray([item[1] for item in points], dtype=float)
        bins = np.linspace(0, 1, 11)
        means = []
        centers = []
        for left, right in zip(bins[:-1], bins[1:]):
            mask = (xs >= left) & (xs <= right if right == 1.0 else xs < right)
            if not mask.any():
                continue
            centers.append((left + right) / 2.0)
            means.append(float(np.mean(ys[mask])))
        plt.plot(centers, means, marker="o", linewidth=2.1, label=label, color=color)
    plt.xlabel("Normalized action progress")
    plt.ylabel("Mean learned-monitor score")
    plt.title("Asynchronous score trajectories")
    plt.ylim(0.0, 1.0)
    plt.legend(frameon=False, loc="upper left")
    plt.tight_layout()
    plt.savefig(output_path, format="svg")
    plt.close()


def plot_environment_mix(episode_rows, output_path):
    counts = defaultdict(lambda: defaultdict(int))
    for row in episode_rows:
        counts[row["environment"]][row["label"]] += 1

    environments = sorted(counts.keys())
    benign = [counts[name]["benign"] for name in environments]
    sabotage = [counts[name]["sabotage"] for name in environments]
    positions = np.arange(len(environments))

    plt.figure(figsize=(7.0, 4.8))
    plt.bar(positions, benign, label="Benign", color="#4c78a8")
    plt.bar(positions, sabotage, bottom=benign, label="Sabotage", color="#f58518")
    plt.xticks(positions, environments)
    plt.ylabel("Episodes")
    plt.title("Toy environment mix")
    plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(output_path, format="svg")
    plt.close()
