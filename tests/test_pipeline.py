import json
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")

if SRC not in sys.path:
    sys.path.insert(0, SRC)

from async_guard_toy.run_all import run_pipeline
from async_guard_toy.simulator import FEATURE_NAMES, generate_dataset


def test_dataset_contains_all_environments_and_prefix_features():
    dataset = generate_dataset(episodes_per_env=6, seed=11)
    environments = sorted(set(row["environment"] for row in dataset["episode_rows"]))
    assert environments == ["dummy_secret", "style_guard", "test_guard"]
    assert dataset["prefix_rows"]
    first_row = dataset["prefix_rows"][0]
    assert sorted(first_row["prefix_features"].keys()) == sorted(FEATURE_NAMES)
    assert "command" in first_row
    assert "duration_seconds" in first_row
    assert "since_prev_seconds" in first_row


def test_pipeline_generates_metrics_and_figures(tmp_path):
    output_dir = str(tmp_path / "artifacts")
    figure_dir = str(tmp_path / "figures")
    report_path = str(tmp_path / "benchmark_report.md")
    metrics = run_pipeline(
        output_dir=output_dir,
        figure_dir=figure_dir,
        report_path=report_path,
        episodes_per_env=12,
        seed=13,
        train_ratio=0.7,
    )

    assert metrics["rules_monitor"]["auc"] > 0.55
    assert metrics["learned_monitor"]["auc"] >= metrics["rules_monitor"]["auc"]
    assert metrics["learned_monitor"]["auc"] > 0.75
    assert metrics["learned_monitor"]["threshold_metrics"]["recall"] >= 0.40

    metrics_path = os.path.join(output_dir, "metrics.json")
    assert os.path.exists(metrics_path)
    with open(metrics_path) as handle:
        saved_metrics = json.load(handle)
    assert saved_metrics["learned_monitor"]["auc"] == metrics["learned_monitor"]["auc"]
    assert os.path.exists(os.path.join(figure_dir, "monitor_roc.svg"))
    assert os.path.exists(os.path.join(output_dir, "example_failure_cases.json"))
    assert os.path.exists(report_path)
