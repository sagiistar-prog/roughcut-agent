"""Summarize a real run on our two original TTS fixtures, never on arbitrary private media."""
import argparse
import json
import re
from pathlib import Path
from create_acceptance_media import ROOT, SPEECH


def word_error_rate(expected, observed):
    a, b = re.findall(r'\w+', expected.lower()), re.findall(r'\w+', observed.lower())
    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        current = [i]
        for j, right in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = current
    return round(previous[-1] / len(a), 4)


def check(report):
    sources = report['sources']
    assert len(sources) == 2, 'Expected exactly two original synthetic sources'
    results = []
    for number, source in enumerate(sources):
        assert source['source_file'].endswith(f'speech{number+1}.mp4'), 'Unexpected fixture'
        assert source['status'] == 'ok' and source['segments']
        assert source['sha256_before'] == source['sha256_after']
        assert all(0 <= segment['start'] < segment['end'] <= source['duration_seconds'] and segment['words'] for segment in source['segments'])
        observed = ' '.join(segment['transcript'] for segment in source['segments'])
        results.append({'source':f'speech{number+1}.mp4','segments':len(source['segments']),
                        'source_sha256':source['sha256_before'],'source_unchanged':True,
                        'synthetic_transcript':observed,'word_error_rate':word_error_rate(SPEECH[number],observed)})
    return {'scope':'Two original synthetic English TTS fixtures, not real-world ASR accuracy',
            'engine': report['engine'], 'engine_version':report['engine_version'], 'model':report['model'],
            'device': report['device'],'compute_type':report['compute_type'], 'sources':results}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--report',type=Path,required=True); parser.add_argument('--output',type=Path,required=True); args=parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT / 'output'):
        raise ValueError('Acceptance output must stay inside output/')
    result=check(json.loads(args.report.read_text(encoding='utf-8')))
    with args.output.open('x',encoding='utf-8') as handle: json.dump(result,handle,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False))
