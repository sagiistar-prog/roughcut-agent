from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import yaml


TIMELINE_FIELDS = [
    "order",
    "source_file",
    "start_time",
    "end_time",
    "duration_seconds",
    "transcript",
    "role",
    "reason",
    "risk_note",
]


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def preference_root(preferences: dict[str, Any]) -> dict[str, Any]:
    return preferences.get("user_preferences", preferences)


def read_material_index(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def role_rank(role: str, role_order: list[str]) -> int:
    try:
        return role_order.index(role)
    except ValueError:
        return len(role_order)


def infer_role(row: dict[str, str]) -> str:
    role = (row.get("role") or "").strip()
    if role:
        return role
    transcript = row.get("transcript", "")
    if any(word in transcript for word in ["问题", "痛点", "耗时"]):
        return "problem"
    if any(word in transcript for word in ["解决", "流程", "生成", "Agent"]):
        return "solution"
    if any(word in transcript for word in ["结果", "跑通", "完成", "价值"]):
        return "proof"
    return "detail"


def score_row(row: dict[str, str], preferences: dict[str, Any], rules: dict[str, Any]) -> float:
    preferences = preference_root(preferences)
    quality = as_float(row.get("quality_score"), 0)
    semantic = as_float(row.get("semantic_score"), 0)
    score = quality * 0.55 + semantic * 0.45

    transcript = row.get("transcript", "")
    preferred_topics = preferences.get("content_style", {}).get("preferred_topics", []) or []
    avoid_topics = preferences.get("content_style", {}).get("avoid_topics", []) or []

    for topic in preferred_topics:
        if topic and topic.lower() in transcript.lower():
            score += 0.05
    for topic in avoid_topics:
        if topic and topic.lower() in transcript.lower():
            score -= 0.12

    if as_bool(row.get("noise_flag")) or as_bool(row.get("overlap_speech_flag")):
        score -= 0.08
    if as_bool(row.get("off_topic_flag")):
        score -= 0.25
    if as_bool(row.get("is_duplicate")):
        score -= 0.5

    minimum_quality = as_float(rules.get("selection", {}).get("minimum_quality_score"), 0.62)
    minimum_semantic = as_float(rules.get("selection", {}).get("minimum_semantic_score"), 0.55)
    if quality < minimum_quality or semantic < minimum_semantic:
        score -= 0.35

    return round(score, 4)


def has_unsafe_pre_roll(row: dict[str, str]) -> bool:
    risk_text = (row.get("risk_note") or "").lower()
    return (
        as_bool(row.get("noise_flag"))
        or as_bool(row.get("overlap_speech_flag"))
        or "noise before" in risk_text
        or "overlap" in risk_text
        or "unrelated before" in risk_text
    )


def adjust_cut_points(row: dict[str, str], rules: dict[str, Any], preferences: dict[str, Any]) -> tuple[float, float, list[str]]:
    preferences = preference_root(preferences)
    cut_rules = rules.get("cut_padding", {})
    pref_cut = preferences.get("cut_padding", {})
    start_pad = as_float(
        pref_cut.get("start_padding_seconds", pref_cut.get("start_pre_roll_seconds")),
        as_float(cut_rules.get("start_pre_roll_seconds"), 0.5),
    )
    end_pad = as_float(
        pref_cut.get("end_padding_seconds", pref_cut.get("end_post_roll_seconds")),
        as_float(cut_rules.get("end_post_roll_seconds"), 0.3),
    )

    original_start = as_float(row.get("segment_start"), as_float(row.get("start_time"), 0))
    original_end = as_float(row.get("segment_end"), as_float(row.get("end_time"), original_start))
    video_duration = as_float(row.get("video_duration_seconds"), original_end)
    risk_notes: list[str] = []

    if has_unsafe_pre_roll(row):
        start_time = original_start
        risk_notes.append("pre-roll not applied because noise, overlap speech, or unrelated content may exist before the segment")
    else:
        start_time = original_start - start_pad
        if start_time < 0:
            start_time = 0
            risk_notes.append("start_time clamped to 0; full pre-roll was not available")

    end_time = original_end + end_pad
    if video_duration and end_time > video_duration:
        end_time = video_duration
        risk_notes.append("end_time clamped to video duration; full post-roll was not available")

    if end_time <= start_time:
        end_time = max(start_time, original_end)
        risk_notes.append("invalid duration risk; check source timecode")

    return round(start_time, 3), round(end_time, 3), risk_notes


def build_reason(row: dict[str, str], score: float) -> str:
    reasons = [f"score={score:.2f}"]
    role = infer_role(row)
    if role:
        reasons.append(f"role={role}")
    if as_float(row.get("quality_score"), 0) >= 0.85:
        reasons.append("clear audio or complete expression")
    if as_float(row.get("semantic_score"), 0) >= 0.85:
        reasons.append("strong semantic value")
    return "; ".join(reasons)


def generate_timeline(material_rows: list[dict[str, str]], rules: dict[str, Any], preferences: dict[str, Any]) -> list[dict[str, Any]]:
    preferences = preference_root(preferences)
    role_order = (
        preferences.get("content_style", {}).get("preferred_roles_order")
        or rules.get("pacing", {}).get("role_order")
        or ["hook", "problem", "solution", "proof", "detail", "cta"]
    )
    pacing = preferences.get("pacing", {}) or {}
    max_clip_count = int(pacing.get("max_clip_count") or rules.get("pacing", {}).get("max_clip_count") or 13)
    target_total = as_float(
        pacing.get("preferred_total_duration_seconds", pacing.get("target_total_seconds")),
        as_float(rules.get("pacing", {}).get("target_total_seconds"), 180),
    )
    preferred_clip = pacing.get("preferred_clip_seconds", {}) or {}
    rules_clip = rules.get("pacing", {}).get("preferred_clip_seconds", {}) or {}
    max_single_clip = as_float(
        pacing.get("max_single_clip_seconds", preferred_clip.get("max")),
        as_float(rules_clip.get("max"), 22),
    )

    candidates = []
    for row in material_rows:
        transcript = (row.get("transcript") or "").strip()
        score = score_row(row, preferences, rules)
        if not transcript:
            continue
        if as_bool(row.get("is_duplicate")) or as_bool(row.get("off_topic_flag")):
            continue
        if score <= 0.25:
            continue
        role = infer_role(row)
        candidates.append((row, role, score))

    candidates.sort(key=lambda item: (role_rank(item[1], role_order), -item[2], as_float(item[0].get("segment_start"), 0)))

    timeline: list[dict[str, Any]] = []
    total_duration = 0.0
    previous_role = ""

    for row, role, score in candidates:
        if len(timeline) >= max_clip_count:
            break
        start_time, end_time, adjustment_risks = adjust_cut_points(row, rules, preferences)
        duration = round(max(0.0, end_time - start_time), 3)
        if max_single_clip and duration > max_single_clip:
            end_time = round(start_time + max_single_clip, 3)
            duration = round(max_single_clip, 3)
            adjustment_risks.append("trimmed to max_single_clip_seconds preference; review sentence ending")
        if target_total and total_duration + duration > target_total and timeline:
            continue

        risk_notes = []
        existing_risk = (row.get("risk_note") or "").strip()
        if existing_risk:
            risk_notes.append(existing_risk)
        risk_notes.extend(adjustment_risks)
        if previous_role and role_rank(role, role_order) < role_rank(previous_role, role_order):
            risk_notes.append("possible logic jump; review semantic transition")

        total_duration += duration
        previous_role = role
        timeline.append(
            {
                "order": len(timeline) + 1,
                "source_file": row.get("source_file", ""),
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": duration,
                "transcript": row.get("transcript", ""),
                "role": role,
                "reason": build_reason(row, score),
                "risk_note": " | ".join(risk_notes),
            }
        )

    return timeline


def write_timeline(rows: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TIMELINE_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in TIMELINE_FIELDS})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a reviewable rough-cut timeline.")
    parser.add_argument("--material-index", default="output/material_index.csv", help="Input material_index.csv.")
    parser.add_argument("--rules", default="configs/editing_rules.yaml", help="Editing rules YAML.")
    parser.add_argument("--preferences", default="configs/user_preferences.yaml", help="User preferences YAML.")
    parser.add_argument("--output", default="output/timeline_review.csv", help="Output timeline_review.csv.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    material_index = Path(args.material_index)
    if not material_index.exists():
        raise FileNotFoundError(f"Material index not found: {material_index}")

    rules = load_yaml(Path(args.rules))
    preferences = load_yaml(Path(args.preferences))
    material_rows = read_material_index(material_index)
    timeline = generate_timeline(material_rows, rules, preferences)
    write_timeline(timeline, Path(args.output))
    total_duration = round(sum(as_float(row["duration_seconds"]) for row in timeline), 3)
    print(f"Wrote {args.output} with {len(timeline)} clips, estimated duration {total_duration}s.")


if __name__ == "__main__":
    main()
