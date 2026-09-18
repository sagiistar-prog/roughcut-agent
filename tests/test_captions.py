import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from captions import build_captions, encode, validate_sources


class CaptionMapping(unittest.TestCase):
    def setUp(self):
        self.name = 'examples/synthetic.mp4'
        self.hashes = {self.name: 'a'*64}
        self.words = [{'start': 1., 'end': 1.4, 'word': ' Hello'}, {'start': 1.5, 'end': 1.9, 'word': ' world.'},
                      {'start': 4., 'end': 4.5, 'word': ' Later.'}]
        self.source = {'source_file': self.name, 'status': 'ok', 'sha256_before': 'a'*64, 'sha256_after': 'a'*64,
                       'duration_seconds': 10., 'segments': [{'start': 0., 'end': 6., 'words': self.words}]}
        self.report = {'schema_version': '1.0', 'engine': 'faster-whisper', 'word_timestamps': True, 'sources': [self.source]}

    def row(self, start=0, end=6, order=1):
        return {'source_file': str(ROOT/self.name), 'start_time': start, 'end_time': end, 'order': order}

    def build(self, rows=None, durations=None, rules=None):
        return build_captions(rows or [self.row()], durations or [6.], self.report, self.hashes, ROOT, rules or {})

    def test_reordered_repeated_source_uses_measured_offsets(self):
        result = self.build([self.row(3, 5), self.row(0, 2, 2)], [2.04, 2.01])
        self.assertEqual([c['text'] for c in result['cues']], ['Later.', 'Hello world.'])
        self.assertEqual([c['start_ms'] for c in result['cues']], [1000, 3040])
        self.assertEqual(result['segment_mapping'][1]['output_start'], 2.04)

    def test_trim_does_not_show_full_words_across_cut(self):
        result = self.build([self.row(1.2, 1.8)], [.6])
        self.assertEqual(result['cues'], [])
        self.assertEqual(sum(r['code']=='word_crosses_cut' for r in result['risks']), 2)

    def test_missing_times_and_zero_duration_keep_gaps(self):
        self.source['segments'].append({'start': 7., 'end': 9., 'words': []})
        self.words.append({'start': 5., 'end': 5., 'word': ' uncertain'})
        result = self.build([self.row(0, 10)], [10.])
        self.assertEqual({r['code'] for r in result['risks']}, {'missing_word_timestamps', 'zero_duration_word'})
        self.assertEqual(result['cues'][-1]['text'], 'Later.')

    def test_source_change_and_duplicate_records_rejected(self):
        self.source['sha256_after'] = 'b'*64
        with self.assertRaisesRegex(ValueError, 'differs'):self.build()
        self.source['sha256_after'] = 'a'*64
        self.report['sources'].append(copy.deepcopy(self.source))
        with self.assertRaisesRegex(ValueError, 'duplicate'):self.build()

    def test_invalid_and_unordered_words_rejected(self):
        for value in [float('nan'), float('inf'), -1., True, 11.]:
            with self.subTest(value=value):
                self.words[0]['start'] = value
                with self.assertRaises(ValueError):validate_sources(self.report, self.hashes)
        self.words[0]['start'] = 1.
        self.words.reverse()
        with self.assertRaises(ValueError):self.build()

    def test_pause_and_character_limits_preserve_words(self):
        result = self.build(rules={'max_cue_characters': 8})
        self.assertEqual([c['text'] for c in result['cues']], ['Hello', 'world.', 'Later.'])
        self.assertEqual(result['status'], 'needs_review')

    def test_chinese_and_html_are_not_rewritten_or_executable(self):
        self.words[:] = [{'start': 1., 'end': 2., 'word': '你好'}, {'start': 2., 'end': 3., 'word': '世界。'},
                         {'start': 4., 'end': 5., 'word': ' <b>tag</b> -->'}]
        result = self.build()
        self.assertEqual(result['cues'][0]['text'], '你好世界。')
        self.assertIn('&lt;b&gt;tag&lt;/b&gt; --&gt;', encode(result['cues']))
        self.assertTrue(encode(result['cues'], True).startswith('WEBVTT\n\n1\n00:00:01.000'))

    def test_readability_limit_reports_indivisible_word(self):
        self.words[:] = [{'start': 1., 'end': 5.5, 'word': 'unusuallylongword'}]
        result = self.build(rules={'max_cue_characters': 5})
        self.assertEqual(result['risks'][0]['code'], 'single_word_exceeds_readability_limit')

    def test_overlap_between_cues_requires_timing_review(self):
        self.words[:] = [{'start': 1., 'end': 2., 'word': ' First.'}, {'start': 1.8, 'end': 3., 'word': ' Second.'}]
        with self.assertRaisesRegex(ValueError, 'overlap'):self.build()

    def test_export_does_not_use_mutated_csv_transcript(self):
        row = {**self.row(), 'transcript': 'Replacement which has no word alignment'}
        result = self.build([row])
        self.assertEqual(result['cues'][0]['text'], 'Hello world.')
        self.assertEqual(result['text_basis'], 'original_asr_words')


if __name__ == '__main__':unittest.main()
