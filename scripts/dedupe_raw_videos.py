from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm"}


@dataclass
class VideoRecord:
    path: Path
    size_bytes: int
    sha256: str
    duplicate_group: str
    duplicate_of: str
    action: str


def hash_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def iter_video_files(raw_dir: Path, quarantine_dir: Path) -> list[Path]:
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw directory does not exist: {raw_dir}")

    videos: list[Path] = []
    quarantine_resolved = quarantine_dir.resolve()
    for path in raw_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        try:
            path.resolve().relative_to(quarantine_resolved)
            continue
        except ValueError:
            videos.append(path)
    return sorted(videos)


def build_report(raw_dir: Path, quarantine_dir: Path) -> list[VideoRecord]:
    seen: dict[str, Path] = {}
    duplicate_counts: dict[str, int] = {}
    records: list[VideoRecord] = []

    for video in iter_video_files(raw_dir, quarantine_dir):
        file_hash = hash_file(video)
        size_bytes = video.stat().st_size
        duplicate_of = ""
        action = "keep"

        if file_hash in seen:
            duplicate_counts[file_hash] = duplicate_counts.get(file_hash, 1) + 1
            duplicate_of = str(seen[file_hash].as_posix())
            action = "duplicate_found"
        else:
            seen[file_hash] = video
            duplicate_counts[file_hash] = 1

        records.append(
            VideoRecord(
                path=video,
                size_bytes=size_bytes,
                sha256=file_hash,
                duplicate_group=file_hash[:12],
                duplicate_of=duplicate_of,
                action=action,
            )
        )

    return records


def write_report(records: list[VideoRecord], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_file",
                "size_bytes",
                "sha256",
                "duplicate_group",
                "duplicate_of",
                "action",
            ],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "source_file": record.path.as_posix(),
                    "size_bytes": record.size_bytes,
                    "sha256": record.sha256,
                    "duplicate_group": record.duplicate_group,
                    "duplicate_of": record.duplicate_of,
                    "action": record.action,
                }
            )


def quarantine_duplicates(records: list[VideoRecord], raw_dir: Path, quarantine_dir: Path) -> int:
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    moved = 0

    for record in records:
        if record.action != "duplicate_found":
            continue
        relative_path = record.path.relative_to(raw_dir)
        target = quarantine_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(record.path), str(target))
        record.action = f"moved_to_quarantine:{target.as_posix()}"
        moved += 1

    return moved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a duplicate report for raw videos.")
    parser.add_argument("--raw-dir", default="raw", help="Directory containing local raw videos.")
    parser.add_argument("--quarantine-dir", default="raw_duplicates_quarantine", help="Duplicate quarantine directory.")
    parser.add_argument("--output", default="output/dedupe_report.csv", help="CSV report path.")
    parser.add_argument(
        "--quarantine-duplicates",
        action="store_true",
        help="Move duplicate copies into quarantine. Originals are never hard-deleted.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_dir = Path(args.raw_dir)
    quarantine_dir = Path(args.quarantine_dir)
    output = Path(args.output)

    records = build_report(raw_dir, quarantine_dir)
    moved = 0
    if args.quarantine_duplicates:
        moved = quarantine_duplicates(records, raw_dir, quarantine_dir)

    write_report(records, output)
    duplicate_count = sum(1 for record in records if "duplicate" in record.action or "quarantine" in record.action)
    print(f"Wrote {output.as_posix()} with {len(records)} videos, {duplicate_count} duplicates, {moved} moved.")


if __name__ == "__main__":
    main()

