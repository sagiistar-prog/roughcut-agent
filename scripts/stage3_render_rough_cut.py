from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path
from typing import Any


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def read_timeline(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"timeline_review.csv is required before rendering: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("Timeline is empty. Review timeline_review.csv before rendering.")
    return rows


def run_ffmpeg_cut(source: Path, start: float, duration: float, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(source),
        "-t",
        f"{duration:.3f}",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(target),
    ]
    subprocess.run(command, check=True)


def run_ffmpeg_concat(list_file: Path, target: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        str(target),
    ]
    subprocess.run(command, check=True)


def write_concat_list(segment_paths: list[Path], list_file: Path) -> None:
    list_file.parent.mkdir(parents=True, exist_ok=True)
    with list_file.open("w", encoding="utf-8") as handle:
        for segment in segment_paths:
            escaped = segment.resolve().as_posix().replace("'", "'\\''")
            handle.write(f"file '{escaped}'\n")


def write_report(rows: list[dict[str, str]], rendered: list[Path], skipped: list[str], output: Path, final_video: Path) -> None:
    total_duration = sum(as_float(row.get("duration_seconds")) for row in rows)
    lines = [
        "# Edit Report",
        "",
        f"- Timeline rows: {len(rows)}",
        f"- Rendered segments: {len(rendered)}",
        f"- Skipped segments: {len(skipped)}",
        f"- Estimated timeline duration: {total_duration:.1f} seconds",
        f"- Final video: `{final_video.as_posix()}`",
        "",
        "## Segment Review",
        "",
    ]
    for row in rows:
        lines.append(
            f"- {row.get('order')}. `{row.get('source_file')}` "
            f"{row.get('start_time')}s-{row.get('end_time')}s "
            f"role={row.get('role')} risk={row.get('risk_note') or 'none'}"
        )
    if skipped:
        lines.extend(["", "## Skipped", ""])
        lines.extend(f"- {item}" for item in skipped)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render(timeline_path: Path, output_dir: Path, final_name: str) -> None:
    rows = read_timeline(timeline_path)
    segments_dir = output_dir / "segments"
    final_video = output_dir / final_name
    report_path = output_dir / "edit_report.md"
    concat_list = output_dir / "concat_list.txt"
    output_dir.mkdir(parents=True, exist_ok=True)

    rendered: list[Path] = []
    skipped: list[str] = []

    for row in rows:
        source = Path(row.get("source_file", ""))
        start = as_float(row.get("start_time"))
        duration = as_float(row.get("duration_seconds"))
        order = int(as_float(row.get("order"), len(rendered) + 1))

        if not source.exists():
            skipped.append(f"missing source for order {order}: {source.as_posix()}")
            continue
        if duration <= 0:
            skipped.append(f"invalid duration for order {order}: {duration}")
            continue

        segment_path = segments_dir / f"segment_{order:03d}.mp4"
        run_ffmpeg_cut(source, start, duration, segment_path)
        rendered.append(segment_path)

    if not rendered:
        write_report(rows, rendered, skipped, report_path, final_video)
        raise RuntimeError("No segments were rendered. Check source paths and timeline_review.csv.")

    write_concat_list(rendered, concat_list)
    run_ffmpeg_concat(concat_list, final_video)
    write_report(rows, rendered, skipped, report_path, final_video)
    print(f"Wrote {final_video.as_posix()} and {report_path.as_posix()}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render final_rough_cut.mp4 from timeline_review.csv.")
    parser.add_argument("--timeline", default="output/timeline_review.csv", help="Reviewable timeline CSV.")
    parser.add_argument("--output-dir", default="output", help="Output directory.")
    parser.add_argument("--final-name", default="final_rough_cut.mp4", help="Final rough-cut filename.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    render(Path(args.timeline), Path(args.output_dir), args.final_name)


if __name__ == "__main__":
    main()

