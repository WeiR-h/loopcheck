import test_support
import unittest
from coach.models import safe_error, error_code


class ModelErrorTests(unittest.TestCase):
    def test_outer_provider_status_survives_inner_transport_cause(self):
        outer = RuntimeError('secret response body')
        outer.status_code = 429
        outer.__cause__ = OSError('private token')
        self.assertEqual(error_code(outer), 'model_limit')
        self.assertIn('rate limits', safe_error(outer))
        self.assertNotIn('private', safe_error(outer))

    def test_nested_timeout_and_connection_are_actionable(self):
        for name, expected in [('ReadTimeout', 'timeout'), ('APIConnectionError', 'connection')]:
            outer = RuntimeError('secret')
            outer.__cause__ = type(name, (Exception,), {})('private credential')
            self.assertEqual(error_code(outer), expected)
            self.assertNotIn('private', safe_error(outer))
            self.assertIn('retry', safe_error(outer))

    def test_generic_failure_does_not_claim_a_repair_or_leak_text(self):
        text = safe_error(RuntimeError('sk-private-secret'))
        self.assertNotIn('sk-private', text)
        self.assertIn('cannot approve', text)

    def test_cyclic_chain_is_bounded(self):
        one, two = RuntimeError('private'), RuntimeError('private')
        one.__cause__, two.__cause__ = two, one
        self.assertEqual(error_code(one), 'task_error')


if __name__ == '__main__': unittest.main()
