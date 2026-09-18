import csv
import json
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from stage2_generate_timeline import TIMELINE_FIELDS
from stage3_render_rough_cut import render


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required for actual render integration')
class RealMediaRender(unittest.TestCase):
    def test_mixed_media_order_and_silent_track(self):
        directory = ROOT / 'output' / ('render-test-' + uuid.uuid4().hex)
        directory.mkdir(parents=True)
        red, blue = directory / 'red.mp4', directory / 'blue.mp4'
        # The authored plan precedes both fixture generation and final rendering.
        timeline = directory / 'timeline_review.csv'
        rows = [dict(order=2, source_file=red.relative_to(ROOT).as_posix(), start_time=0, end_time=1,
                     duration_seconds=1, transcript='Red silence', role='fixture', reason='synthetic', risk_note=''),
                dict(order=1, source_file=blue.relative_to(ROOT).as_posix(), start_time=0, end_time=1,
                     duration_seconds=1, transcript='Blue tone', role='fixture', reason='synthetic', risk_note='')]
        with timeline.open('w', encoding='utf-8', newline='') as handle:
            writer=csv.DictWriter(handle, fieldnames=TIMELINE_FIELDS); writer.writeheader(); writer.writerows(rows)
        base = ['ffmpeg','-hide_banner','-loglevel','error','-n']
        subprocess.run(base+['-f','lavfi','-i','color=red:s=320x240:r=24','-t','1.2','-c:v','libx264','-pix_fmt','yuv420p',str(red)],check=True,timeout=60)
        subprocess.run(base+['-f','lavfi','-i','color=blue:s=240x320:r=25','-f','lavfi','-i','sine=frequency=440:sample_rate=44100','-t','1.2','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(blue)],check=True,timeout=60)
        report = render(timeline, directory / 'render', 'cut.mp4', True)
        self.assertTrue(report['sources_unchanged'])
        self.assertLess(abs(report['actual_seconds'] - 2), .15)
        video = next(s for s in report['streams'] if s['codec_type']=='video')
        audio = next(s for s in report['streams'] if s['codec_type']=='audio')
        self.assertEqual((video['width'],video['height'],video['r_frame_rate']), (1280,720,'30/1'))
        self.assertEqual((audio['sample_rate'],audio['channels']), ('48000',2))
        final = directory / 'render/cut.mp4'
        for time, channel in [('0.3', 2), ('1.3', 0)]:
            sample = subprocess.run(['ffmpeg','-v','error','-ss',time,'-i',str(final),'-frames:v','1','-vf','crop=10:10:(iw-10)/2:(ih-10)/2,scale=1:1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True,timeout=30).stdout
            self.assertEqual(max(range(3), key=lambda i: sample[i]),channel)
        with self.assertRaises(FileExistsError): render(timeline, directory / 'render', 'cut.mp4', True)
