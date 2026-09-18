import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from stage2_generate_timeline import plan_timeline
from stage1_transcribe_index import index_segments, safe_media
from stage3_render_rough_cut import render


def row(start=1, end=6, **extra):
    return dict(source_file='raw/fictional.mp4', segment_start=str(start), segment_end=str(end), video_duration_seconds='100', transcript='Original sentence.', **extra)


class HonestSelection(unittest.TestCase):
    def test_unmeasured_quality_does_not_discard_speech(self):
        selected, _ = plan_timeline([row()], {}, {})
        self.assertEqual(len(selected), 1)
        self.assertIn('未测量', selected[0]['risk_note'])

    def test_long_segment_is_not_cut_to_fit(self):
        selected, _ = plan_timeline([row(1, 40)], {}, {'pacing': {'max_single_clip_seconds': 10}})
        self.assertGreaterEqual(selected[0]['end_time'], 40)
        self.assertIn('未自动截句', selected[0]['risk_note'])

    def test_no_budget_fit_still_keeps_review_candidate(self):
        selected, candidates = plan_timeline([row(1, 40)], {}, {'pacing': {'target_total_seconds': 10}})
        self.assertEqual(selected, [])
        self.assertIsNotNone(candidates[0]['clip'])

    def test_input_order_and_no_keyword_role_invention(self):
        selected, _ = plan_timeline([row(20, 25), row(1, 5, role='hook', quality_score='1', semantic_score='1')], {}, {})
        self.assertGreater(selected[0]['start_time'], selected[1]['start_time'])
        self.assertEqual(selected[0]['role'], '未标注')

    def test_adjacent_padding_does_not_repeat_audio(self):
        selected, _ = plan_timeline([row(1, 6), row(6.1, 10)], {}, {})
        self.assertLessEqual(selected[0]['end_time'], selected[1]['start_time'])
        self.assertGreaterEqual(selected[0]['end_time'], 6)
        self.assertLessEqual(selected[1]['start_time'], 6.1)

    def test_overlaps_are_reviewable_not_silently_duplicated(self):
        selected, candidates = plan_timeline([row(1, 6), row(4, 8)], {}, {})
        self.assertEqual(len(selected), 1)
        self.assertIn('重叠', candidates[1]['reason'])

    def test_flags_remove_without_erasing(self):
        selected, candidates = plan_timeline([row(is_duplicate='true')], {}, {})
        self.assertEqual(selected, [])
        self.assertIsNotNone(candidates[0]['clip'])

    def test_quarantine_and_empty_text_rejected(self):
        quarantined = row(); quarantined['source_file'] = 'raw_duplicates_quarantine/a.mp4'
        blank = row(); blank['transcript'] = ''
        self.assertEqual(plan_timeline([quarantined, blank], {}, {})[0], [])

    def test_input_is_not_mutated(self):
        rows = [row()]; original = copy.deepcopy(rows)
        plan_timeline(rows, {}, {})
        self.assertEqual(rows, original)


class TranscriptionContract(unittest.TestCase):
    def test_asr_records_observations_not_quality_claims(self):
        segment = SimpleNamespace(text='Original word.', start=0, end=2, avg_logprob=-.2, no_speech_prob=.1,
                                  words=[SimpleNamespace(start=0, end=1, word='Original', probability=.9)])
        rows, details = index_segments(ROOT / 'raw/synthetic.mp4', 3, [segment], 'en', {'word': 'term'})
        for key in ('quality_score', 'semantic_score', 'noise_flag', 'overlap_speech_flag', 'role'):
            self.assertEqual(rows[0][key], '')
        self.assertEqual(details[0]['original_transcript'], 'Original word.')
        self.assertEqual(rows[0]['transcript'], 'Original term.')
        self.assertEqual(len(details[0]['words']), 1)

    def test_missing_media_and_quarantine_rejected(self):
        for path in [ROOT / 'raw/missing.mp4', ROOT / 'raw_duplicates_quarantine/a.mp4', ROOT.parent / 'outside.mp4']:
            with self.assertRaises(ValueError): safe_media(path)

    def test_render_requires_user_review_before_any_io(self):
        with patch('stage3_render_rough_cut.read_timeline') as read:
            with self.assertRaises(ValueError): render(Path('output/timeline_review.csv'), ROOT / 'output/test', 'cut.mp4')
            read.assert_not_called()
