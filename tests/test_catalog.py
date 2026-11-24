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


class CalendarTest(unittest.TestCase):
    """Regression for Codex review: 'today'/'7 days' must be calendar days."""
    def load_report(self):
        import importlib.machinery, importlib.util
        loader = importlib.machinery.SourceFileLoader('report', str(ROOT / 'scripts/report'))
        spec = importlib.util.spec_from_loader('report', loader)
        mod = importlib.util.module_from_spec(spec); loader.exec_module(mod)
        return mod

    def test_idle_today_is_empty_and_old_data_falls_out(self):
        from datetime import date
        cal = self.load_report().calendar(
            {'2026-01-01': {'claude': {'totalTokens': 999}}, '2026-01-09': {'codex': {'totalTokens': 5}}},
            7, today=date(2026, 1, 10))
        self.assertEqual(len(cal), 7)
        self.assertEqual(cal[-1], {'day': '2026-01-10'})            # nothing used today -> empty
        self.assertEqual(cal[-2]['codex']['totalTokens'], 5)
        self.assertNotIn('2026-01-01', [d['day'] for d in cal])     # older than 7 days -> excluded


class SafePathTest(unittest.TestCase):
    def test_safe_dir_rejects_traversal(self):
        from tools.skill_hub.catalog import SAFE_DIR
        for ok in ('skills', 'plugin/skills', 'plugins/modern-cpp/skills'):
            self.assertTrue(SAFE_DIR.fullmatch(ok), ok)
        for bad in ('../x', 'a/../b', '/etc', 'a//b', '.', './a', ''):
            self.assertFalse(SAFE_DIR.fullmatch(bad), bad)

    def test_per_skill_dir_overrides_vendor_and_unsafe_is_rejected(self):
        from tools.skill_hub.catalog import load, skill_rel_dir
        with tempfile.TemporaryDirectory() as tmp:
            vend = {'v': {'repo': 'o/r', 'path': 'vendor/v', 'skills_dir': 'skills'}}
            Path(tmp, 'skills.json').write_text(json.dumps({'vendors': vend, 'skills': [
                {'name': 'a', 'source': 'vendor', 'vendor': 'v'},
                {'name': 'b', 'source': 'vendor', 'vendor': 'v', 'skills_dir': 'plugins/b/skills'}]}))
            data = load(tmp)
            self.assertEqual(skill_rel_dir(data, data['skills'][0]), 'skills/a')
            self.assertEqual(skill_rel_dir(data, data['skills'][1]), 'plugins/b/skills/b')
            Path(tmp, 'skills.json').write_text(json.dumps({'vendors': vend, 'skills': [
                {'name': 'c', 'source': 'vendor', 'vendor': 'v', 'skills_dir': '../../etc'}]}))
            with self.assertRaises(ValueError):
                load(tmp)


class AgentsTest(unittest.TestCase):
    def test_agents_default_both_and_validation(self):
        from tools.skill_hub.catalog import agents_of, load
        with tempfile.TemporaryDirectory() as tmp:
            def write(agents):
                s = {'name': 'a', 'source': 'local'}
                if agents is not None:
                    s['agents'] = agents
                Path(tmp, 'skills.json').write_text(json.dumps({'vendors': {}, 'skills': [s]}))
            write(None); self.assertEqual(agents_of(load(tmp)['skills'][0]), ['claude', 'codex'])
            write(['codex']); self.assertEqual(agents_of(load(tmp)['skills'][0]), ['codex'])
            for bad in ([], ['gemini'], ['codex', 'x']):
                write(bad)
                with self.assertRaises(ValueError):
                    load(tmp)


class UpstreamTest(unittest.TestCase):
    def test_wrapper_upstream_symlinks_resolve(self):
        from tools.skill_hub.catalog import load
        data = load()
        for s in data['skills']:
            if 'upstream' in s:
                from tools.skill_hub.catalog import upstream_link
                link, target = upstream_link(data, s)
                self.assertTrue(link.is_symlink(), s['name'])
                self.assertEqual(link.resolve(), target.resolve())

    def test_bad_upstream_rejected(self):
        from tools.skill_hub.catalog import load
        with tempfile.TemporaryDirectory() as tmp:
            for up in ({'vendor': 'nope', 'file': 'a.md'}, {'vendor': 'v', 'file': '../x.md'}):
                Path(tmp, 'skills.json').write_text(json.dumps({
                    'vendors': {'v': {'repo': 'o/r', 'path': 'vendor/v', 'skills_dir': 'skills'}},
                    'skills': [{'name': 'w', 'source': 'local', 'upstream': up}]}))
                with self.assertRaises(ValueError):
                    load(tmp)
