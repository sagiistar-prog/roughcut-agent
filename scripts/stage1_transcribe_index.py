from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path
from stage2_generate_timeline import load_yaml

ROOT = Path(__file__).resolve().parents[1]
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.m4v', '.webm'}
FIELDS = ['source_file', 'clip_id', 'video_duration_seconds', 'segment_start', 'segment_end', 'transcript', 'language', 'subtitle_zh', 'subtitle_en', 'role', 'quality_score', 'semantic_score', 'is_duplicate', 'duplicate_group', 'noise_flag', 'overlap_speech_flag', 'off_topic_flag', 'risk_note']


def safe_media(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT) or 'raw_duplicates_quarantine' in path.parts or 'raw_duplicates_quarantine' in resolved.parts:
        raise ValueError('Choose media inside the repository and outside quarantine')
    if not resolved.is_file():
        raise ValueError('Source media is missing')
    return resolved


def iter_video_files(directory: Path):
    if not directory.resolve().is_relative_to(ROOT) or 'raw_duplicates_quarantine' in directory.resolve().parts:
        raise ValueError('Choose a media directory inside the repository, outside quarantine')
    for path in sorted(directory.rglob('*')):
        if path.suffix.lower() in VIDEO_EXTENSIONS and path.is_file() and 'raw_duplicates_quarantine' not in path.parts:
            yield safe_media(path)


def probe_duration(path: Path) -> float:
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(path)], capture_output=True, text=True, check=True, timeout=30)
    duration = float(json.loads(result.stdout)['format']['duration'])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Invalid media duration')
    return duration


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def index_segments(path: Path, duration: float, segments, language: str, replacements: dict) -> tuple[list, list]:
    rows, details = [], []
    source = path.relative_to(ROOT).as_posix()
    for number, segment in enumerate(segments, 1):
        original = segment.text.strip()
        if not original:
            continue
        start, end = max(0, round(segment.start, 3)), min(duration, round(segment.end, 3))
        if not 0 <= start < end <= duration:
            raise ValueError('ASR returned an invalid segment range')
        text = ' '.join(original.split())
        for before, after in replacements.items():
            text = text.replace(str(before), str(after))
        clip_id = f'{hashlib.sha256(source.encode()).hexdigest()[:10]}_{number:04d}'
        risk = '自动转写需人工试听；音画质量、重叠人声与语义价值未测量'
        if segment.avg_logprob < -1 or segment.no_speech_prob > .6:
            risk += '；识别置信信号偏弱，请重点核对'
        row = {key: '' for key in FIELDS}
        row.update(source_file=source, clip_id=clip_id, video_duration_seconds=str(duration),
                   segment_start=str(start), segment_end=str(end), transcript=text, language=language,
                   subtitle_zh=text if language == 'zh' else '', subtitle_en=text if language == 'en' else '', risk_note=risk)
        rows.append(row)
        details.append({'clip_id': clip_id, 'original_transcript': original, 'transcript': text,
                        'start': start, 'end': end, 'avg_logprob': segment.avg_logprob,
                        'no_speech_prob': segment.no_speech_prob,
                        'words': [{'start': w.start, 'end': w.end, 'word': w.word, 'probability': w.probability} for w in (segment.words or [])]})
    return rows, details


def main() -> int:
    parser = argparse.ArgumentParser(description='Local ASR with source hashes, word timings and explicit failures.')
    parser.add_argument('--raw-dir', type=Path, default=ROOT / 'raw')
    parser.add_argument('--output', type=Path, default=ROOT / 'output/material_index.csv')
    parser.add_argument('--language', default='zh', help='Language code, or auto')
    parser.add_argument('--model', default='small', help='faster-whisper model name or local model directory')
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    parser.add_argument('--compute-type', default='int8')
    parser.add_argument('--local-files-only', action='store_true')
    parser.add_argument('--rules', type=Path, default=ROOT / 'configs/editing_rules.yaml')
    args = parser.parse_args()
    report_path = args.output.with_suffix('.asr.json')
    if not args.output.resolve().is_relative_to(ROOT / 'output'):
        raise ValueError('ASR output must stay inside output/')
    if args.output.exists() or report_path.exists():
        raise FileExistsError('Existing ASR results are preserved')
    paths = list(iter_video_files(args.raw_dir))
    if not paths:
        raise ValueError('No supported video found in the chosen directory')
    from faster_whisper import WhisperModel
    # One model instance per batch; only initial model acquisition uses network.
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type, local_files_only=args.local_files_only)
    replacements = load_yaml(args.rules).get('transcript_replacements', {})
    rows, sources = [], []
    for path in paths:
        entry = {'source_file': path.relative_to(ROOT).as_posix(), 'status': 'error'}
        try:
            entry['sha256_before'] = sha256(path)
            duration = probe_duration(path)
            segments, info = model.transcribe(str(path), language=None if args.language == 'auto' else args.language,
                                              beam_size=5, vad_filter=True, word_timestamps=True)
            indexed, details = index_segments(path, duration, segments, info.language, replacements)
            entry.update(status='ok' if indexed else 'no_speech', duration_seconds=duration,
                         language=info.language, language_probability=info.language_probability, segments=details,
                         sha256_after=sha256(path))
            if entry['sha256_before'] != entry['sha256_after']:
                raise ValueError('Source changed during transcription')
            rows.extend(indexed)
        except Exception as exc:
            entry.update(status='error', error_type=type(exc).__name__)
        sources.append(entry)
        print(f'Indexed source {len(sources)}/{len(paths)}: {entry["status"]}', flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    from importlib.metadata import version
    report = {'schema_version': '1.0', 'engine': 'faster-whisper', 'engine_version': version('faster-whisper'),
              'model': args.model, 'device': args.device, 'compute_type': args.compute_type, 'vad_filter': True,
              'word_timestamps': True, 'segment_count': len(rows), 'sources': sources,
              'unmeasured': ['semantic_quality', 'visual_quality', 'noise', 'speaker_overlap']}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    return 2 if any(source['status'] == 'error' for source in sources) else 0


if __name__ == '__main__':
    raise SystemExit(main())
