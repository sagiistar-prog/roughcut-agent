from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def read_feedback(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Feedback file not found: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def preference_root(preferences: dict[str, Any]) -> dict[str, Any]:
    return preferences.setdefault("user_preferences", {})


def summarize_feedback(rows: list[dict[str, str]]) -> dict[str, Any]:
    actions = Counter((row.get("action") or "unknown").strip() for row in rows)
    tags = Counter((row.get("tag") or "untagged").strip() for row in rows)
    comments = [row.get("comment", "").strip() for row in rows if row.get("comment", "").strip()]

    signals: list[str] = []
    if actions["shorten"] > actions["extend_end"] + actions["extend_start"]:
        signals.append("prefer tighter pacing")
    if actions["extend_end"] or any("句尾" in comment or "切太紧" in comment for comment in comments):
        signals.append("avoid cutting sentence endings too tightly")
    if tags["strong_hook"]:
        signals.append("keep clear problem-led hooks")
    if tags["product_value"]:
        signals.append("prioritize product value statements")
    if tags["reviewability"]:
        signals.append("prioritize reviewability and risk-note explanations")

    return {
        "actions": dict(actions),
        "tags": dict(tags),
        "signals": signals,
        "comments": comments,
    }


def update_preferences(preferences: dict[str, Any], summary: dict[str, Any], feedback_path: Path) -> dict[str, Any]:
    root = preference_root(preferences)
    root.setdefault("pacing", {})
    root.setdefault("cut_padding", {})
    root.setdefault("content_style", {})
    root.setdefault("learned_from_feedback", [])
    root.setdefault("review_notes", [])

    signals = summary.get("signals", [])
    if "prefer tighter pacing" in signals:
        root["pacing"]["style"] = "tighter_with_breath"
        preferred = root["pacing"].setdefault("preferred_clip_seconds", {"min": 4, "max": 16})
        preferred["max"] = min(int(preferred.get("max", 16)), 16)

    if "avoid cutting sentence endings too tightly" in signals:
        root["cut_padding"]["end_padding_seconds"] = max(
            float(root["cut_padding"].get("end_padding_seconds", root["cut_padding"].get("end_post_roll_seconds", 0.3))),
            0.35,
        )

    preferred_topics = root["content_style"].setdefault("preferred_topics", [])
    if "prioritize product value statements" in signals and "product_value" not in preferred_topics:
        preferred_topics.append("product_value")
    if "prioritize reviewability and risk-note explanations" in signals and "reviewability" not in preferred_topics:
        preferred_topics.append("reviewability")

    learned_entry = {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "source": feedback_path.as_posix(),
        "summary": summary,
    }
    root["learned_from_feedback"].append(learned_entry)

    note_text = "; ".join(signals) if signals else "Feedback recorded for future review."
    root["review_notes"].append(
        {
            "date": learned_entry["date"],
            "note": note_text,
        }
    )
    return preferences


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append user feedback learning into user_preferences.yaml.")
    parser.add_argument("--feedback", default="output/feedback.csv", help="Feedback CSV from output or examples.")
    parser.add_argument("--preferences", default="configs/user_preferences.yaml", help="User preferences YAML to update.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    feedback_path = Path(args.feedback)
    preferences_path = Path(args.preferences)
    rows = read_feedback(feedback_path)
    summary = summarize_feedback(rows)
    preferences = load_yaml(preferences_path)
    updated = update_preferences(preferences, summary, feedback_path)
    write_yaml(preferences_path, updated)
    print(f"Updated {preferences_path.as_posix()} from {feedback_path.as_posix()} with {len(rows)} feedback rows.")


if __name__ == "__main__":
    main()
