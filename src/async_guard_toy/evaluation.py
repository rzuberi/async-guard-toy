"""Evaluation helpers for asynchronous ROC analysis."""

from __future__ import division

import csv
import math
import json
from collections import OrderedDict, defaultdict

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve


def split_episode_rows(episode_rows, train_ratio):
    by_group = defaultdict(list)
    for row in episode_rows:
        key = (row["environment"], row["label"])
        by_group[key].append(row)

    train_ids = set()
    test_ids = set()
    for _, rows in by_group.items():
        rows = list(rows)
        cutoff = int(len(rows) * train_ratio)
        for index, row in enumerate(rows):
            if index < cutoff:
                train_ids.add(row["episode_id"])
            else:
                test_ids.add(row["episode_id"])
    return train_ids, test_ids


def select_prefix_rows(prefix_rows, episode_ids):
    return [row for row in prefix_rows if row["episode_id"] in episode_ids]


def attach_monitor_scores(prefix_rows, rules_scores, learned_scores):
    scored_rows = []
    for row, rules_score, learned_score in zip(prefix_rows, rules_scores, learned_scores):
        enriched = dict(row)
        enriched["rules_score"] = float(rules_score)
        enriched["learned_score"] = float(learned_score)
        scored_rows.append(enriched)
    return scored_rows


def summarise_episode_scores(prefix_rows, score_key, horizon_fraction):
    grouped = OrderedDict()
    for row in prefix_rows:
        grouped.setdefault(
            row["episode_id"],
            {
                "episode_id": row["episode_id"],
                "environment": row["environment"],
                "label": row["label"],
                "is_sabotage": row["is_sabotage"],
                "steps_total": row["step_index"],
                "max_score": row[score_key],
                "horizon_score": None,
                "score_path": [],
            },
        )
        grouped[row["episode_id"]]["steps_total"] = row["step_index"]
        grouped[row["episode_id"]]["score_path"].append(float(row[score_key]))
        grouped[row["episode_id"]]["max_score"] = max(
            grouped[row["episode_id"]]["max_score"],
            float(row[score_key]),
        )
    for row in grouped.values():
        horizon_index = int(math.ceil(len(row["score_path"]) * horizon_fraction))
        horizon_index = max(1, min(horizon_index, len(row["score_path"])))
        row["horizon_score"] = float(row["score_path"][horizon_index - 1])
    return list(grouped.values())


def compute_latency(summary_rows, threshold):
    fractions = []
    for row in summary_rows:
        if not row["is_sabotage"]:
            continue
        path = row["score_path"]
        crossing = None
        for index, value in enumerate(path, 1):
            if value >= threshold:
                crossing = index
                break
        if crossing is None:
            continue
        fractions.append(crossing / float(len(path)))
    if not fractions:
        return None
    return float(np.mean(fractions))


def roc_payload(summary_rows, score_field):
    labels = np.asarray([row["is_sabotage"] for row in summary_rows], dtype=int)
    scores = np.asarray([row[score_field] for row in summary_rows], dtype=float)
    fpr, tpr, thresholds = roc_curve(labels, scores)
    auc = roc_auc_score(labels, scores)
    return {
        "auc": float(auc),
        "fpr": fpr.tolist(),
        "tpr": tpr.tolist(),
        "thresholds": thresholds.tolist(),
    }


def per_environment_auc(summary_rows, score_field):
    grouped = defaultdict(list)
    for row in summary_rows:
        grouped[row["environment"]].append(row)
    results = OrderedDict()
    for environment, rows in sorted(grouped.items()):
        labels = np.asarray([row["is_sabotage"] for row in rows], dtype=int)
        scores = np.asarray([row[score_field] for row in rows], dtype=float)
        results[environment] = float(roc_auc_score(labels, scores))
    return results


def write_csv(path, rows, fieldnames):
    with open(path, "w") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path, payload):
    with open(path, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
