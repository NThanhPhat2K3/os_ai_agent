import unittest
from datetime import datetime, timezone

class EngineTest(unittest.TestCase):
    def test_cooldown_never_recommends_new_release(self):
        from tools.skill_hub.engine import choose_release
        today = datetime(2026, 1, 31, tzinfo=timezone.utc)
        releases = [('2.0.0', '2026-01-30T00:00:00Z'), ('1.5.0', '2026-01-01T00:00:00Z')]
        result = choose_release('1.0.0', releases, 14, today)
        self.assertEqual(result['recommended'], '1.5.0')
        self.assertEqual(result['status'], 'update-available')

    def test_no_eligible_newer_release_is_too_new(self):
        from tools.skill_hub.engine import choose_release
        today = datetime(2026, 1, 31, tzinfo=timezone.utc)
        result = choose_release('1.0.0', [('2.0.0', '2026-01-30T00:00:00Z')], 14, today)
        self.assertEqual(result['status'], 'too-new')
        self.assertIsNone(result['recommended'])

    def test_new_disabled_dependency_warns(self):
        from tools.skill_hub.engine import new_dependencies
        self.assertEqual(new_dependencies('superpowers:test-driven-development', 'superpowers:test-driven-development superpowers:missing', {'test-driven-development'}), {'missing'})


class ChooseCommitTest(unittest.TestCase):
    """Regression for Codex review: never recommend a commit older than the pin."""
    NOW = datetime(2026, 2, 1, tzinfo=timezone.utc)

    def commits(self, *items):  # newest first, like the GitHub API
        return [(sha, datetime.fromisoformat(day + 'T00:00:00+00:00')) for sha, day in items]

    def test_young_current_pin_is_never_downgraded(self):
        from tools.skill_hub.engine import choose_commit
        c = self.commits(('cur', '2026-01-30'), ('old', '2026-01-01'))
        r = choose_commit('cur', c, 14, self.NOW)
        self.assertEqual((r['status'], r['recommended']), ('up-to-date', None))

    def test_only_newer_commits_are_candidates(self):
        from tools.skill_hub.engine import choose_commit
        c = self.commits(('new2', '2026-01-31'), ('new1', '2026-01-10'), ('cur', '2026-01-05'), ('old', '2025-12-01'))
        r = choose_commit('cur', c, 14, self.NOW)
        self.assertEqual((r['status'], r['recommended']), ('update-available', 'new1'))

    def test_newer_but_too_young(self):
        from tools.skill_hub.engine import choose_commit
        c = self.commits(('new', '2026-01-31'), ('cur', '2026-01-01'))
        r = choose_commit('cur', c, 14, self.NOW)
        self.assertEqual((r['status'], r['recommended']), ('too-new', None))

    def test_pin_older_than_listed_window(self):
        from tools.skill_hub.engine import choose_commit
        c = self.commits(('a', '2026-01-31'), ('b', '2026-01-02'))
        r = choose_commit('ancient', c, 14, self.NOW)
        self.assertEqual(r['recommended'], 'b')


class AncestryTest(unittest.TestCase):
    """Regression for Codex review: only recommend a commit GitHub confirms is ahead of the pin."""
    def run_check(self, relation):
        from unittest import mock
        from tools.skill_hub import engine
        commits = [{'sha': 'new' + '0' * 37, 'commit': {'committer': {'date': '2026-01-01T00:00:00Z'}}}]
        def fake_github(path):
            return {'status': relation} if '/compare/' in path else commits
        with mock.patch.object(engine, 'get_submodule_pin', return_value='old' + '0' * 37), \
             mock.patch.object(engine, 'github_json', side_effect=fake_github), \
             mock.patch.object(engine, 'skill_text', return_value='same'):
            return engine.check_vendor('v', {'repo': 'o/r', 'path': 'vendor/v'}, [('s', 'skills/s')],
                                       14, datetime(2026, 2, 1, tzinfo=timezone.utc))

    def test_ahead_is_recommended(self):
        r = self.run_check('ahead')
        self.assertEqual((r['status'], r['recommended'][:3]), ('update-available', 'new'))

    def test_diverged_history_is_not_recommended(self):
        for relation in ('diverged', 'behind', 'identical'):
            r = self.run_check(relation)
            self.assertEqual((r['status'], r['recommended']), ('warning', None), relation)
