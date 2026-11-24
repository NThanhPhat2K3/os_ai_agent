import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class PinsTest(unittest.TestCase):
    def test_reads_configured_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'pins.json'
            path.write_text(json.dumps({'context7': '9.2.0'}))
            p = subprocess.run([sys.executable, str(ROOT / 'tools/skill_hub/pins.py'), str(path), 'context7'], capture_output=True, text=True)
            self.assertEqual((p.returncode, p.stdout.strip()), (0, '9.2.0'))

    def test_rejects_missing_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'pins.json'
            path.write_text('{}')
            p = subprocess.run([sys.executable, str(ROOT / 'tools/skill_hub/pins.py'), str(path), 'context7'], capture_output=True, text=True)
            self.assertNotEqual(p.returncode, 0)
