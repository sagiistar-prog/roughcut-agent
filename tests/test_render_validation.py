import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from stage3_render_rough_cut import validate_render_rows

class RenderValidation(unittest.TestCase):
    def test_missing_and_out_of_media_ranges_are_rejected_before_render(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'synthetic.mp4';source.write_bytes(b'fixture')
            row={'source_file':str(source),'start_time':'0','end_time':'2','duration_seconds':'2','order':'1'}
            with patch('stage3_render_rough_cut.subprocess.run',return_value=SimpleNamespace(stdout='{"format":{"duration":"3"}}')):
                validate_render_rows([row])
                for invalid in ({'start_time':'nan'},{'end_time':'4','duration_seconds':'4'},{'duration_seconds':'1'},{'source_file':str(source)+'.missing'}):
                    with self.assertRaises(ValueError):validate_render_rows([{**row,**invalid}])
                with self.assertRaises(ValueError):validate_render_rows([row,row])
