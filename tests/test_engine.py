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
