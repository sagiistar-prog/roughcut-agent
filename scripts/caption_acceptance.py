"""Real caption integration on the two original generated speech fixtures only."""
import argparse
import csv
import json
from pathlib import Path
import subprocess

from asr_acceptance import check
from stage2_generate_timeline import TIMELINE_FIELDS
from stage3_render_rough_cut import ROOT, render


def accept(asr_path: Path, directory: Path):
    asr_path, directory = asr_path.resolve(), directory.resolve()
    if not asr_path.is_relative_to(ROOT/'output') or not directory.is_relative_to(ROOT/'output'):
        raise ValueError('Use explicitly generated fixture paths inside output/')
    asr = json.loads(asr_path.read_text(encoding='utf-8'))
    evidence = check(asr)
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    for order, source in enumerate(reversed(asr['sources']), 1):
        rows.append(dict(order=order, source_file=source['source_file'], start_time=0, end_time=source['duration_seconds'],
                         duration_seconds=source['duration_seconds'], transcript='Original synthetic fixture',
                         role='fixture', reason='Reverse source order to verify caption mapping', risk_note='Synthetic English TTS'))
    timeline = directory/'timeline_review.csv'
    with timeline.open('x', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=TIMELINE_FIELDS);writer.writeheader();writer.writerows(rows)
    result = render(timeline, directory/'render', 'captioned-cut.mp4', True, asr_path)
    captions = json.loads((directory/'render/captions.json').read_text(encoding='utf-8'))
    assert captions['cue_count'] > 0
    assert captions['cues'][0]['source_file'].endswith('speech2.mp4')
    assert captions['cues'][-1]['source_file'].endswith('speech1.mp4')
    for cue in captions['cues']:
        mapping = captions['segment_mapping'][cue['order']-1]
        assert cue['start_ms'] == round((mapping['output_start']+cue['source_start']-mapping['source_start'])*1000)
        assert 0 <= cue['start_ms'] < cue['end_ms'] <= result['actual_seconds']*1000+1
    parsers = []
    for suffix in ['srt','vtt']:
        probe = subprocess.run(['ffprobe','-v','error','-show_packets','-of','json',str(directory/'render'/('captioned-cut.'+suffix))],check=True,capture_output=True,text=True,timeout=30)
        packets = json.loads(probe.stdout)['packets']
        assert len(packets) == captions['cue_count']
        assert all(abs(float(packet['pts_time'])-cue['start_ms']/1000)<.001 for packet,cue in zip(packets,captions['cues']))
        parsers.append({'format':suffix,'packet_count':len(packets),'timestamps_match':True})
    summary = {'scope':'Original synthetic English TTS; not real-world ASR or customer outcomes',
               'asr':evidence,'caption_count':captions['cue_count'],'risk_count':captions['risk_count'],
               'source_order':['speech2.mp4','speech1.mp4'],'actual_render_seconds':result['actual_seconds'],
               'source_hashes_unchanged':result['sources_unchanged'],'subtitle_parsers':parsers,
               'review_status':captions['status']}
    (directory/'acceptance.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--asr',required=True,type=Path);parser.add_argument('--output-dir',required=True,type=Path)
    args=parser.parse_args();accept(args.asr,args.output_dir)
