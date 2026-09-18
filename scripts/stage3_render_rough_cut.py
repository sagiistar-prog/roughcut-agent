from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_timeline(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError('Timeline is empty')
    return rows


def validate_render_rows(rows: list[dict]) -> None:
    orders, durations = set(), {}
    for row in rows:
        source = Path(row.get('source_file', '')).resolve()
        if not source.is_file():
            raise ValueError('A timeline source is missing')
        if 'raw_duplicates_quarantine' in source.parts:
            raise ValueError('Quarantined media cannot be rendered')
        start, end, duration, order = (float(row[k]) for k in ('start_time', 'end_time', 'duration_seconds', 'order'))
        if not all(math.isfinite(n) for n in (start, end, duration, order)):
            raise ValueError('Timeline contains non-finite values')
        if start < 0 or end <= start or duration <= 0 or abs(end - start - duration) > .02:
            raise ValueError('Timeline range and duration disagree')
        if order < 1 or not order.is_integer() or order in orders:
            raise ValueError('Timeline orders must be unique positive integers')
        orders.add(order)
        if source not in durations:
            result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(source)], capture_output=True, text=True, check=True, timeout=30)
            durations[source] = float(json.loads(result.stdout)['format']['duration'])
        if not math.isfinite(durations[source]) or end > durations[source] + .05:
            raise ValueError('Timeline extends beyond source duration')
    if orders != set(range(1, len(rows) + 1)):
        raise ValueError('Timeline orders must be contiguous from 1')


def run_ffmpeg_cut(source: Path, start: float, duration: float, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(source)], capture_output=True, text=True, check=True, timeout=30)
    streams = json.loads(probe.stdout)['streams']
    if not any(s['codec_type'] == 'video' for s in streams):
        raise ValueError('Source must contain video')
    audio = any(s['codec_type'] == 'audio' for s in streams)
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', '-ss', f'{start:.3f}', '-i', str(source)]
    if not audio:
        command += ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']
    command += ['-t', f'{duration:.3f}', '-map', '0:v:0', '-map', '0:a:0' if audio else '1:a:0',
                '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p,setpts=PTS-STARTPTS',
                '-af', 'aresample=48000,apad,asetpts=PTS-STARTPTS', '-ac', '2', '-ar', '48000',
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-c:a', 'aac', '-b:a', '160k',
                '-video_track_timescale', '90000', '-movflags', '+faststart', str(target)]
    subprocess.run(command, check=True, timeout=3600)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def render(timeline_path: Path, output_dir: Path, final_name: str, reviewed: bool = False) -> dict:
    if not reviewed:
        raise ValueError('Review the timeline, then pass --reviewed to render')
    if timeline_path.name != 'timeline_review.csv':
        raise ValueError('Save the reviewed file as timeline_review.csv')
    rows = read_timeline(timeline_path)
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to((ROOT / 'output').resolve()):
        raise ValueError('Render output must stay inside output/')
    if Path(final_name).name != final_name or Path(final_name).suffix.lower() != '.mp4':
        raise ValueError('Final name must be a single MP4 filename')
    reserved = (final_name, 'segments', 'edit_report.md', 'render.json', 'concat_list.txt')
    if any((output_dir / name).exists() for name in reserved):
        raise FileExistsError('Existing render artifacts are preserved. Choose a new output directory.')
    validate_render_rows(rows)
    rows.sort(key=lambda row: int(float(row['order'])))
    paths = {Path(row['source_file']).resolve() for row in rows}
    if any(not path.is_relative_to(ROOT) for path in paths):
        raise ValueError('Source media must stay inside this repository')
    hashes = {str(path.relative_to(ROOT)): digest(path) for path in paths}
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {'schema_version': '1.0', 'status': 'rendering', 'review_acknowledged': True,
              'timeline_sha256': digest(timeline_path), 'source_sha256': hashes, 'rows': rows,
              'normalization': {'width': 1280, 'height': 720, 'fps': 30, 'audio_hz': 48000, 'audio_channels': 2}}
    report_path = output_dir / 'render.json'
    try:
        segments = []
        for row in rows:
            target = output_dir / 'segments' / f"segment_{int(float(row['order'])):03}.mp4"
            run_ffmpeg_cut(Path(row['source_file']), float(row['start_time']), float(row['duration_seconds']), target)
            segments.append(target)
        concat = output_dir / 'concat_list.txt'
        concat.write_text(''.join("file '" + path.as_posix().replace("'", "'\\''") + "'\n" for path in segments), encoding='utf-8')
        final = output_dir / final_name
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', '-f', 'concat', '-safe', '0', '-i', str(concat), '-c', 'copy', '-movflags', '+faststart', str(final)], check=True, timeout=3600)
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(final)], capture_output=True, text=True, check=True, timeout=30)
        info = json.loads(probe.stdout)
        expected = sum(float(row['duration_seconds']) for row in rows)
        actual = float(info['format']['duration'])
        if abs(actual - expected) > max(.15, len(rows) * .05):
            raise ValueError('Rendered duration differs materially from the reviewed timeline')
        unchanged = all(digest(ROOT / name) == value for name, value in hashes.items())
        if not unchanged:
            raise ValueError('Source changed during render')
        report.update(status='complete', expected_seconds=round(expected, 3), actual_seconds=actual,
                      sources_unchanged=unchanged, final_sha256=digest(final), streams=info['streams'])
        (output_dir / 'edit_report.md').write_text(f'# Render report\n\nRendered {len(rows)} reviewed clips in order. Expected {expected:.3f}s; actual {actual:.3f}s.\n\nOriginal source hashes unchanged. 720p letterbox, 30fps, stereo 48kHz.\n\nNo translation, subtitle burn-in or audio enhancement was performed.\n', encoding='utf-8')
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__)
        raise
    finally:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Render an explicitly reviewed local timeline.')
    parser.add_argument('--timeline', type=Path, default=Path('output/timeline_review.csv'))
    parser.add_argument('--output-dir', type=Path, default=Path('output/render'))
    parser.add_argument('--final-name', default='final_rough_cut.mp4')
    parser.add_argument('--reviewed', action='store_true')
    args = parser.parse_args()
    report = render(args.timeline, args.output_dir, args.final_name, args.reviewed)
    print(f"Rendered {len(report['rows'])} clips; {report['actual_seconds']:.3f}s; sources unchanged.")
