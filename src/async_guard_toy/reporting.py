"""Report generation helpers for AsyncGuard-Toy."""

from __future__ import division


def _pct(value):
    return "%.1f%%" % (100.0 * value)


def _fmt_score(value):
    return "%.3f" % value


def _case_line(case_payload):
    if not case_payload:
        return "No example available for this category in the current run."
    parts = [
        "`%s`" % case_payload["episode_id"],
        "env `%s`" % case_payload["environment"],
        "horizon score %s" % _fmt_score(case_payload["horizon_score"]),
    ]
    if case_payload.get("crossing_step") is None:
        parts.append("never crosses the alert threshold")
    else:
        parts.append(
            "crosses threshold at step %d/%d"
            % (case_payload["crossing_step"], case_payload["steps_total"])
        )
    return ", ".join(parts) + "."


def _top_action_lines(case_payload):
    if not case_payload:
        return ["No trace excerpt available."]
    lines = []
    for item in case_payload["trace_excerpt"]:
        suffix = []
        if item.get("command"):
            suffix.append("cmd `%s`" % item["command"])
        if item.get("test_summary"):
            suffix.append("test `%s`" % item["test_summary"]["status"])
        if item.get("diff_summary"):
            diff = item["diff_summary"]
            suffix.append("+%d/-%d lines" % (diff["added_lines"], diff["removed_lines"]))
        suffix.append("%ss" % item["duration_seconds"])
        lines.append(
            "- step %d `%s` on `%s`: %s%s"
            % (
                item["step_index"],
                item["action_type"],
                item["target"],
                item["description"],
                (" [" + "; ".join(suffix) + "]") if suffix else "",
            )
        )
    return lines


def write_benchmark_report(path, metrics, failure_cases):
    learned_auc_by_env = metrics["learned_monitor"]["per_environment_auc"]
    easiest = sorted(learned_auc_by_env.items(), key=lambda item: item[1], reverse=True)[0]
    hardest = sorted(learned_auc_by_env.items(), key=lambda item: item[1])[0]

    rules_threshold = metrics["rules_monitor"]["threshold_metrics"]
    learned_threshold = metrics["learned_monitor"]["threshold_metrics"]

    lines = [
        "# AsyncGuard-Toy Benchmark Report",
        "",
        "AsyncGuard-Toy is a compact benchmark for testing whether simple monitors can catch suspicious coding-agent behaviour before a human reviewer has full visibility.",
        "",
        "## Headline Results",
        "",
        "| Monitor | ROC AUC | Recall @ threshold | False positive rate @ threshold | Mean detection point |",
        "| --- | ---: | ---: | ---: | ---: |",
        "| Rules | %s | %s | %s | %s |"
        % (
            _fmt_score(metrics["rules_monitor"]["auc"]),
            _pct(rules_threshold["recall"]),
            _pct(rules_threshold["false_positive_rate"]),
            _pct(metrics["rules_monitor"]["latency_at_0_65"]),
        ),
        "| Learned | %s | %s | %s | %s |"
        % (
            _fmt_score(metrics["learned_monitor"]["auc"]),
            _pct(learned_threshold["recall"]),
            _pct(learned_threshold["false_positive_rate"]),
            _pct(metrics["learned_monitor"]["latency_at_0_65"]),
        ),
        "",
        "The learned baseline is stronger overall, but both monitors still detect sabotage late rather than immediately.",
        "",
        "## Easy And Hard Cases",
        "",
        "The easiest environment for the learned monitor in this run is `%s` (AUC %s)."
        % (easiest[0], _fmt_score(easiest[1])),
        "",
        "The hardest environment is `%s` (AUC %s)."
        % (hardest[0], _fmt_score(hardest[1])),
        "",
        "In practice, overt test weakening is easiest to catch, while short traces with only mild style drift or one-off dummy-secret touches are harder because they still look superficially routine.",
        "",
        "## Representative Failure Cases",
        "",
        "### Caught sabotage",
        "",
        _case_line(failure_cases.get("caught_sabotage")),
        "",
    ]

    lines.extend(_top_action_lines(failure_cases.get("caught_sabotage")))
    lines.extend(
        [
            "",
            "### Missed sabotage",
            "",
            _case_line(failure_cases.get("missed_sabotage")),
            "",
        ]
    )
    lines.extend(_top_action_lines(failure_cases.get("missed_sabotage")))
    lines.extend(
        [
            "",
            "### False positive",
            "",
            _case_line(failure_cases.get("false_positive")),
            "",
        ]
    )
    lines.extend(_top_action_lines(failure_cases.get("false_positive")))
    lines.extend(
        [
            "",
            "## Takeaway",
            "",
            "This benchmark is useful because it turns the oversight problem into a reproducible measurement exercise: what can a monitor infer from partial logs, imperfect tests, command traces, diffs, and timing signals before the full story is available?",
            "",
        ]
    )

    with open(path, "w") as handle:
        handle.write("\n".join(lines).strip() + "\n")
