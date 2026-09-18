"""Map actual ASR words onto a reviewed render; preserve gaps and uncertainties."""
from __future__ import annotations

import html
import math
import re
from pathlib import Path


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Caption timestamps must be finite numbers')
    return float(value)


def validate_sources(report, source_hashes):
    if report.get('schema_version') != '1.0' or report.get('engine') != 'faster-whisper' or report.get('word_timestamps') is not True:
        raise ValueError('Use the original faster-whisper ASR report with word timestamps')
    sources = {}
    for source in report.get('sources', []):
        name = source.get('source_file')
        if name in sources:
            raise ValueError('ASR report contains duplicate source records')
        sources[name] = source
    for name, digest in source_hashes.items():
        source = sources.get(name)
        if not source or source.get('status') not in ('ok', 'no_speech'):
            raise ValueError('A selected source has no successful ASR record')
        if source.get('sha256_before') != digest or source.get('sha256_after') != digest:
            raise ValueError('Source differs from ASR report; transcribe the current media again')
        duration = number(source.get('duration_seconds'))
        if duration <= 0:
            raise ValueError('Invalid ASR source duration')
        previous = -1
        for segment in source.get('segments', []):
            start, end = number(segment.get('start')), number(segment.get('end'))
            if not 0 <= start < end <= duration:
                raise ValueError('Invalid ASR segment range')
            for word in segment.get('words', []):
                a, b = number(word.get('start')), number(word.get('end'))
                if not 0 <= a <= b <= duration + .001 or a < previous:
                    raise ValueError('Invalid or unordered ASR word range')
                if a < start - .05 or b > end + .05:
                    raise ValueError('ASR word lies outside its segment')
                if not isinstance(word.get('word'), str) or not word['word'].strip():
                    raise ValueError('ASR word text is missing')
                previous = a
    return sources


def join_words(words):
    text = ''
    for word in words:
        piece = word['word']
        if text and not piece[0].isspace() and text[-1].isascii() and text[-1].isalnum() and piece[0].isascii() and piece[0].isalnum():
            text += ' '
        text += piece
    return ' '.join(text.split())


def build_captions(rows, segment_durations, report, source_hashes, root: Path, rules):
    sources = validate_sources(report, source_hashes)
    if len(rows) != len(segment_durations):
        raise ValueError('Rendered segment durations do not match the reviewed timeline')
    maximum = int(rules.get('max_cue_characters', 42))
    seconds = number(rules.get('max_cue_seconds', 4.0))
    gap = number(rules.get('max_word_gap_seconds', .75))
    if maximum < 1 or seconds <= 0 or gap < 0:
        raise ValueError('Caption grouping limits must be positive')
    cues, risks, mapping = [], [], []
    offset = 0.0
    for row, rendered in zip(rows, segment_durations):
        rendered = number(rendered)
        if rendered <= 0:
            raise ValueError('Rendered segment duration must be positive')
        name = Path(row['source_file']).resolve().relative_to(root).as_posix()
        start, end = float(row['start_time']), float(row['end_time'])
        order = int(float(row['order']))
        mapping.append({'order': order, 'source_file': name, 'source_start': start, 'source_end': end,
                        'output_start': round(offset, 6), 'rendered_seconds': rendered})
        chosen = []
        for segment in sources[name].get('segments', []):
            if segment['end'] <= start or segment['start'] >= end:
                continue
            if not segment.get('words'):
                risks.append({'order': order, 'code': 'missing_word_timestamps', 'source_start': segment['start'], 'source_end': segment['end']})
            for word in segment.get('words', []):
                a, b = word['start'], word['end']
                if b < start or a >= end:
                    continue
                if a == b:
                    risks.append({'order': order, 'code': 'zero_duration_word', 'source_start': a, 'source_end': b})
                    continue
                if b <= start:
                    continue
                if a < start or b > end:
                    risks.append({'order': order, 'code': 'word_crosses_cut', 'source_start': a, 'source_end': b})
                    continue
                output_start = round((offset + a - start) * 1000)
                output_end = min(round((offset + b - start) * 1000), round((offset + rendered) * 1000))
                if output_start >= output_end:
                    risks.append({'order': order, 'code': 'word_outside_rendered_duration', 'source_start': a, 'source_end': b})
                    continue
                chosen.append({**word, 'output_start_ms': output_start, 'output_end_ms': output_end})
        if not chosen:
            risks.append({'order': order, 'code': 'no_caption_words', 'source_start': start, 'source_end': end})
        group = []

        def flush():
            if not group:
                return
            text = join_words(group)
            a, b = group[0]['output_start_ms'], max(w['output_end_ms'] for w in group)
            if cues and a < cues[-1]['end_ms']:
                raise ValueError('ASR cue ranges overlap; review source timings before subtitle export')
            cue = {'id': len(cues) + 1, 'order': order, 'start_ms': a, 'end_ms': b, 'text': text,
                   'source_file': name, 'source_start': group[0]['start'], 'source_end': max(w['end'] for w in group)}
            cues.append(cue)
            if len(text) > maximum or (b - a) / 1000 > seconds:
                risks.append({'order': order, 'code': 'single_word_exceeds_readability_limit', 'cue_id': cue['id']})
            group.clear()

        for word in chosen:
            if group and (len(join_words([*group, word])) > maximum or word['end'] - group[0]['start'] > seconds
                          or word['start'] - group[-1]['end'] > gap):
                flush()
            group.append(word)
            if re.search(r'[.!?。！？]$', word['word'].strip()):
                flush()
        flush()
        offset += rendered
    return {'schema_version': '1.0', 'status': 'needs_review', 'timing_basis': 'asr_words_and_measured_render_segments',
            'text_basis': 'original_asr_words', 'cues': cues, 'risks': risks, 'segment_mapping': mapping,
            'source_sha256': source_hashes, 'cue_count': len(cues), 'risk_count': len(risks)}


def timestamp(milliseconds, separator=','):
    seconds, ms = divmod(milliseconds, 1000)
    minutes, sec = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    return f'{hours:02}:{minute:02}:{sec:02}{separator}{ms:03}'


def encode(cues, vtt=False):
    lines = ['WEBVTT', ''] if vtt else []
    for cue in cues:
        separator = '.' if vtt else ','
        lines += [str(cue['id']), f"{timestamp(cue['start_ms'], separator)} --> {timestamp(cue['end_ms'], separator)}",
                  html.escape(cue['text'], quote=False), '']
    return '\n'.join(lines) + '\n'
