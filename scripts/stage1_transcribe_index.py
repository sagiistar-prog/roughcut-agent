from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path
from typing import Any


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm"}


def run_ffprobe_duration(path: Path) -> float | None:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        data = json.loads(result.stdout)
        return round(float(data["format"]["duration"]), 3)
    except Exception:
        return None


def iter_video_files(raw_dir: Path) -> list[Path]:
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw directory does not exist: {raw_dir}")
    return sorted(path for path in raw_dir.rglob("*") if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS)


def normalize_transcript(text: str, replacements: dict[str, str]) -> str:
    normalized = " ".join((text or "").split())
    for wrong, right in replacements.items():
        normalized = normalized.replace(wrong, right)
    return normalized


def transcribe_with_faster_whisper(video: Path, model_name: str, language: str) -> list[dict[str, Any]] | None:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception:
        return None

    model = WhisperModel(model_name, device="auto", compute_type="auto")
    segments, _info = model.transcribe(str(video), language=language)
    rows = []
    for index, segment in enumerate(segments, start=1):
        rows.append(
            {
                "clip_id": f"{video.stem}_{index:03d}",
                "segment_start": round(float(segment.start), 3),
                "segment_end": round(float(segment.end), 3),
                "transcript": segment.text.strip(),
                "risk_note": "",
            }
        )
    return rows


def fallback_segments(video: Path, duration: float | None) -> list[dict[str, Any]]:
    safe_duration = duration or 0
    segment_end = min(safe_duration, 12.0) if safe_duration else 0
    return [
        {
            "clip_id": f"{video.stem}_001",
            "segment_start": 0.0,
            "segment_end": round(segment_end, 3),
            "transcript": "",
            "risk_note": "ASR unavailable; transcript requires manual or model review.",
        }
    ]


def load_replacements(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data.get("transcript_replacements", {}) or {}
    except Exception:
        return {}


def write_material_index(rows: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_file",
        "clip_id",
        "video_duration_seconds",
        "segment_start",
        "segment_end",
        "transcript",
        "language",
        "subtitle_zh",
        "subtitle_en",
        "role",
        "quality_score",
        "semantic_score",
        "is_duplicate",
        "duplicate_group",
        "noise_flag",
        "overlap_speech_flag",
        "off_topic_flag",
        "risk_note",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe raw videos and build material_index.csv.")
    parser.add_argument("--raw-dir", default="raw", help="Directory containing local raw videos.")
    parser.add_argument("--output", default="output/material_index.csv", help="Material index CSV path.")
    parser.add_argument("--language", default="zh", help="ASR language hint.")
    parser.add_argument("--model", default="small", help="faster-whisper model name when installed.")
    parser.add_argument("--rules", default="configs/editing_rules.yaml", help="Rules file for transcript normalization.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_dir = Path(args.raw_dir)
    output = Path(args.output)
    replacements = load_replacements(Path(args.rules))
    rows: list[dict[str, Any]] = []

    for video in iter_video_files(raw_dir):
        duration = run_ffprobe_duration(video)
        segments = transcribe_with_faster_whisper(video, args.model, args.language)
        if segments is None:
            segments = fallback_segments(video, duration)

        for segment in segments:
            transcript = normalize_transcript(segment.get("transcript", ""), replacements)
            rows.append(
                {
                    "source_file": video.as_posix(),
                    "clip_id": segment["clip_id"],
                    "video_duration_seconds": duration or "",
                    "segment_start": segment["segment_start"],
                    "segment_end": segment["segment_end"],
                    "transcript": transcript,
                    "language": args.language,
                    "subtitle_zh": transcript if args.language.startswith("zh") else "",
                    "subtitle_en": "",
                    "role": "detail",
                    "quality_score": 0.7 if transcript else 0.0,
                    "semantic_score": 0.7 if transcript else 0.0,
                    "is_duplicate": "false",
                    "duplicate_group": "",
                    "noise_flag": "false",
                    "overlap_speech_flag": "false",
                    "off_topic_flag": "false",
                    "risk_note": segment.get("risk_note", ""),
                }
            )

    write_material_index(rows, output)
    print(f"Wrote {output.as_posix()} with {len(rows)} material rows.")


if __name__ == "__main__":
    main()

