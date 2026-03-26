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
                "horizon_step": None,
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
        row["horizon_step"] = horizon_index
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


def threshold_metrics(summary_rows, score_field, threshold):
    tp = 0
    fp = 0
    tn = 0
    fn = 0
    for row in summary_rows:
        predicted_positive = row[score_field] >= threshold
        actual_positive = bool(row["is_sabotage"])
        if predicted_positive and actual_positive:
            tp += 1
        elif predicted_positive and not actual_positive:
            fp += 1
        elif actual_positive:
            fn += 1
        else:
            tn += 1

    precision = tp / float(tp + fp) if (tp + fp) else 0.0
    recall = tp / float(tp + fn) if (tp + fn) else 0.0
    false_positive_rate = fp / float(fp + tn) if (fp + tn) else 0.0
    specificity = tn / float(fp + tn) if (fp + tn) else 0.0
    accuracy = (tp + tn) / float(tp + tn + fp + fn) if (tp + tn + fp + fn) else 0.0

    return OrderedDict(
        [
            ("threshold", float(threshold)),
            ("tp", tp),
            ("fp", fp),
            ("tn", tn),
            ("fn", fn),
            ("precision", float(precision)),
            ("recall", float(recall)),
            ("false_positive_rate", float(false_positive_rate)),
            ("specificity", float(specificity)),
            ("accuracy", float(accuracy)),
        ]
    )


def _first_crossing_step(score_path, threshold):
    for index, value in enumerate(score_path, 1):
        if value >= threshold:
            return index
    return None


def build_episode_traces(prefix_rows):
    grouped = OrderedDict()
    for row in prefix_rows:
        grouped.setdefault(row["episode_id"], []).append(row)
    for episode_id in grouped:
        grouped[episode_id] = sorted(grouped[episode_id], key=lambda item: item["step_index"])
    return grouped


def select_failure_cases(prefix_rows, summary_rows, score_field, threshold):
    traces = build_episode_traces(prefix_rows)

    def _episode_payload(row, case_type):
        trace = traces[row["episode_id"]]
        crossing_step = _first_crossing_step(row["score_path"], threshold)
        excerpt = trace[-3:] if len(trace) > 3 else trace
        return OrderedDict(
            [
                ("case_type", case_type),
                ("episode_id", row["episode_id"]),
                ("environment", row["environment"]),
                ("label", row["label"]),
                ("horizon_score", float(row["horizon_score"])),
                ("max_score", float(row["max_score"])),
                ("horizon_step", int(row["horizon_step"])),
                ("steps_total", int(row["steps_total"])),
                ("crossing_step", crossing_step),
                (
                    "trace_excerpt",
                    [
                        OrderedDict(
                            [
                                ("step_index", item["step_index"]),
                                ("action_type", item["action_type"]),
                                ("target", item["target"]),
                                ("description", item["description"]),
                                ("command", item.get("command")),
                                ("command_exit_code", item.get("command_exit_code")),
                                ("duration_seconds", item.get("duration_seconds")),
                                ("since_prev_seconds", item.get("since_prev_seconds")),
                                ("diff_summary", item.get("diff_summary")),
                                ("test_summary", item.get("test_summary")),
                            ]
                        )
                        for item in excerpt
                    ],
                ),
            ]
        )

    sabotages = [row for row in summary_rows if row["is_sabotage"]]
    benign = [row for row in summary_rows if not row["is_sabotage"]]

    true_positive = [row for row in sabotages if row[score_field] >= threshold]
    false_negative = [row for row in sabotages if row[score_field] < threshold]
    false_positive = [row for row in benign if row[score_field] >= threshold]

    result = OrderedDict()
    if true_positive:
        result["caught_sabotage"] = _episode_payload(
            sorted(true_positive, key=lambda item: item[score_field], reverse=True)[0],
            "caught_sabotage",
        )
    if false_negative:
        result["missed_sabotage"] = _episode_payload(
            sorted(false_negative, key=lambda item: item[score_field])[0],
            "missed_sabotage",
        )
    if false_positive:
        result["false_positive"] = _episode_payload(
            sorted(false_positive, key=lambda item: item[score_field], reverse=True)[0],
            "false_positive",
        )
    return result


def write_csv(path, rows, fieldnames):
    with open(path, "w") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path, payload):
    with open(path, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
