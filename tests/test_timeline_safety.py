import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from stage2_generate_timeline import invalid_time_reason,generate_timeline,load_yaml
from apply_user_feedback import update_preferences

class TimelineSafety(unittest.TestCase):
    def test_invalid_times(self):
        for start,end,total in [('nan','4','8'),('-1','4','8'),('3','3','8'),('0','9','8'),('0','inf','8')]:
            self.assertIsNotNone(invalid_time_reason({'segment_start':start,'segment_end':end,'video_duration_seconds':total}))
    def test_feedback_updates_effective_limit(self):
        prefs={'user_preferences':{'pacing':{'preferred_clip_seconds':{'min':4,'max':18},'max_single_clip_seconds':18}}}
        changed=update_preferences(prefs,{'signals':['prefer tighter pacing']},Path('examples/feedback.csv'))
        self.assertEqual(changed['user_preferences']['pacing']['max_single_clip_seconds'],16)
    def test_invalid_rows_never_enter_timeline(self):
        rules=load_yaml(ROOT/'configs/editing_rules.yaml');prefs=load_yaml(ROOT/'configs/user_preferences.yaml')
        rows=[{'source_file':'fictional.mp4','segment_start':'-2','segment_end':'10','video_duration_seconds':'8','quality_score':'1','semantic_score':'1'}]
        self.assertEqual(generate_timeline(rows,rules,prefs),[])

if __name__=='__main__':unittest.main()
