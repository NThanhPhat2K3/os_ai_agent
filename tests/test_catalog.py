import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class CatalogTest(unittest.TestCase):
    def write(self, tmp, skills, vendors=None):
        Path(tmp, 'skills.json').write_text(json.dumps({'vendors': vendors or {}, 'skills': skills}))

    def test_real_catalog_is_valid_and_files_exist(self):
        from tools.skill_hub.catalog import load, skill_dir
        data = load()
        for s in data['skills']:
            self.assertTrue((skill_dir(data, s) / 'SKILL.md').is_file(), s['name'])

    def test_rejects_duplicate_and_bad_names(self):
        from tools.skill_hub.catalog import load
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, [{'name': 'a', 'source': 'local'}, {'name': 'a', 'source': 'local'}])
            with self.assertRaises(ValueError):
                load(tmp)
            self.write(tmp, [{'name': '../evil', 'source': 'local'}])
            with self.assertRaises(ValueError):
                load(tmp)

    def test_rejects_unknown_vendor(self):
        from tools.skill_hub.catalog import load
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, [{'name': 'x', 'source': 'vendor', 'vendor': 'nope'}])
            with self.assertRaises(ValueError):
                load(tmp)


class ReportTest(unittest.TestCase):
    def test_report_builds_offline_and_escapes_script_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'r.html'
            p = subprocess.run([sys.executable, str(ROOT / 'scripts/report'), '--no-network', '--no-open', '--out', str(out)],
                               capture_output=True, text=True, timeout=300)
            self.assertEqual(p.returncode, 0, p.stderr)
            html = out.read_text()
            data = html.split('<script id="data" type="application/json">', 1)[1].split('</script>', 1)[0]
            self.assertNotIn('</', data)          # JSON cannot break out of its <script>
            self.assertEqual(out.stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
