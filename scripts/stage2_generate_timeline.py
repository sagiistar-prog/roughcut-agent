from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[1]
TIMELINE_FIELDS = ['order', 'source_file', 'start_time', 'end_time', 'duration_seconds', 'transcript', 'role', 'reason', 'risk_note']


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (ValueError, TypeError):
        return default


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in ('true', '1', 'yes', 'y')


def load_yaml(path: Path) -> dict:
    with path.open(encoding='utf-8-sig') as handle:
        return yaml.safe_load(handle) or {}


def preference_root(preferences: dict) -> dict:
    return preferences.get('user_preferences', preferences)


def invalid_time_reason(row: dict) -> str | None:
    try:
        start, end, duration = (float(row[key]) for key in ('segment_start', 'segment_end', 'video_duration_seconds'))
    except (KeyError, ValueError, TypeError):
        return '时间信息缺失或格式错误'
    if not all(math.isfinite(value) for value in (start, end, duration)):
        return '时间必须是有限数值'
    if not 0 <= start < end <= duration:
        return '时间范围超出素材或起止点颠倒'
    return None


def plan_timeline(material_rows: list[dict], rules: dict, preferences: dict) -> tuple[list[dict], list[dict]]:
    prefs = preference_root(preferences)
    pacing = prefs.get('pacing', {})
    maximum = int(pacing.get('max_clip_count', rules.get('pacing', {}).get('max_clip_count', 13)))
    budget = as_float(pacing.get('preferred_total_duration_seconds', pacing.get('target_total_seconds')), 180)
    preferred_max = as_float(pacing.get('max_single_clip_seconds'), 22)
    if maximum < 1 or budget <= 0:
        raise ValueError('Clip count and duration budget must be positive')
    padding = prefs.get('cut_padding', {})
    rule_padding = rules.get('cut_padding', {})
    pre = max(0, as_float(padding.get('start_padding_seconds'), rule_padding.get('start_pre_roll_seconds', .5)))
    post = max(0, as_float(padding.get('end_padding_seconds'), rule_padding.get('end_post_roll_seconds', .3)))
    eligible = [(i, row) for i, row in enumerate(material_rows) if not invalid_time_reason(row)]
    chosen: list[dict] = []
    candidates: list[dict] = []
    occupied: dict[str, list[tuple[float, float]]] = {}
    total = 0.0
    for index, row in enumerate(material_rows):
        reason = invalid_time_reason(row)
        source = str(row.get('source_file', '')).strip()
        text = str(row.get('transcript', '')).strip()
        if not reason and (not source or 'raw_duplicates_quarantine' in source.replace('\\', '/').split('/')):
            reason = '源文件缺失或属于隔离目录'
        if not reason and not text:
            reason = '无转写内容，请先检查识别结果'
        if reason:
            candidates.append({'row': index + 1, 'selected': False, 'reason': reason, 'clip': None})
            continue
        start, end, duration = (float(row[k]) for k in ('segment_start', 'segment_end', 'video_duration_seconds'))
        risks = [str(row['risk_note'])] if row.get('risk_note') else []
        risks.append('自动转写与句子边界需试听核对')
        if not row.get('quality_score') or not row.get('semantic_score'):
            risks.append('音画质量与内容价值未测量')
        if as_bool(row.get('noise_flag')) or as_bool(row.get('overlap_speech_flag')):
            risks.append('输入标记存在噪声或重叠人声')
        left = max(0, start - pre)
        right = min(duration, end + post)
        if as_bool(row.get('noise_flag')) or as_bool(row.get('overlap_speech_flag')) or any(k in str(row.get('risk_note', '')) for k in ('noise before', 'overlap speech before', 'unrelated before')):
            left = start
        for neighbor_index, neighbor in eligible:
            if neighbor_index == index or neighbor.get('source_file') != source:
                continue
            ns, ne = float(neighbor['segment_start']), float(neighbor['segment_end'])
            if ne <= start:
                left = max(left, (ne + start) / 2)
            if ns >= end:
                right = min(right, (end + ns) / 2)
        left, right = round(left, 3), round(right, 3)
        length = round(right - left, 3)
        if length > preferred_max:
            risks.append('超过偏好长度，保留完整识别片段，未自动截句')
        clip = dict(order=0, source_file=source, start_time=left, end_time=right,
                    duration_seconds=length, transcript=text, role=row.get('role') or '未标注',
                    reason='按输入素材顺序保留；未进行语义排名', risk_note='；'.join(risks))
        if as_bool(row.get('is_duplicate')) or as_bool(row.get('off_topic_flag')):
            reason = '输入已标记重复或跑题'
        elif any(left < previous_end and right > previous_start for previous_start, previous_end in occupied.get(source, [])):
            reason = '与已选源素材时间重叠，避免重复播放'
        elif len(chosen) >= maximum:
            reason = '达到初选片数上限'
        elif total + length > budget:
            reason = '超出初选总时长，保留候选供手动恢复'
        else:
            chosen.append(clip)
            clip['order'] = len(chosen)
            total += length
            occupied.setdefault(source, []).append((left, right))
        candidates.append({'row': index + 1, 'selected': reason is None,
                           'reason': reason or clip['reason'], 'source_duration_seconds': duration, 'clip': clip})
    return chosen, candidates


def generate_timeline(material_rows: list[dict], rules: dict, preferences: dict) -> list[dict]:
    return plan_timeline(material_rows, rules, preferences)[0]


def read_material_index(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def write_timeline(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=TIMELINE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate an honest, reviewable initial selection without reading media.')
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', default='output/timeline_review.csv', type=Path)
    parser.add_argument('--rules', default=ROOT / 'configs/editing_rules.yaml', type=Path)
    parser.add_argument('--preferences', default=ROOT / 'configs/user_preferences.yaml', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    timeline, candidates = plan_timeline(read_material_index(args.input), load_yaml(args.rules), load_yaml(args.preferences))
    if args.dry_run:
        print(json.dumps({'timeline': timeline, 'candidates': candidates}, ensure_ascii=False))
        return
    if not args.output.resolve().is_relative_to(ROOT / 'output'):
        raise ValueError('Generated timelines must stay inside output/')
    from plugin_run import run
    result = run({'material_rows': read_material_index(args.input)})
    # Preserve the caller's rules/preferences in both artifacts.
    result['result'].update(timeline=timeline, candidates=candidates,
                            clip_count=len(timeline), total_duration_seconds=round(sum(x['duration_seconds'] for x in timeline), 3),
                            rejected_rows=[{'row': item['row'], 'reason': item['reason']} for item in candidates if not item['selected']])
    report = args.output.with_suffix('.json')
    if report.exists() or args.output.exists():
        raise FileExistsError('Existing results are preserved')
    write_timeline(timeline, args.output)
    result['result']['csv'] = args.output.read_text(encoding='utf-8')
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {len(timeline)} initial clips and {len(candidates)} review candidates.')


if __name__ == '__main__':
    main()
