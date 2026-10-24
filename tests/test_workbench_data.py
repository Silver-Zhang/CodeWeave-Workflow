"""Public handoffs cannot select or smuggle native/authorization receipts."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from studio.graph import Invalid
from studio.workbench_graph import transfer, request_text


class PublicHandoffTests(unittest.TestCase):
    def test_private_receipt_cannot_be_selected_as_a_field(self):
        with self.assertRaises(Invalid):
            transfer({'receipt': {'session_id': 'private'}}, {'transfer': 'field', 'field': 'receipt'})

    def test_nested_receipt_path_is_rejected(self):
        with self.assertRaises(Invalid):
            transfer({'result': {'receipt': {'secret': 'private'}}},
                     {'transfer': 'field', 'field': 'result.receipt.secret'})

    def test_nested_private_values_do_not_cross_full_result_edge(self):
        output = {'answer': 'public', 'result': {'score': 2, 'receipt': {'sid': 'private'}},
                  'sources': [{'content': {'authorization': 'private', 'answer': 'public'}}]}
        value = transfer(output, {'transfer': 'result'})
        self.assertEqual(value['result'], {'score': 2})
        self.assertEqual(value['sources'][0]['content'], {'answer': 'public'})
        self.assertIn('receipt', output['result'], 'handoff cleaning cannot mutate authoritative outputs')

    def test_credential_shaped_text_is_redacted(self):
        value = transfer({'answer': 'api_key=do-not-forward-this'}, {'transfer': 'answer'})
        self.assertNotIn('do-not-forward-this', value)

    def test_public_structured_field_keeps_json_type(self):
        self.assertIs(transfer({'result': {'accepted': False}},
                               {'transfer': 'field', 'field': 'result.accepted'}), False)

    def test_budget_truncation_remains_explicit(self):
        value = transfer({'answer': 'a' * 200}, {'transfer': 'answer', 'max_chars': 128})
        self.assertTrue(value['truncated'])
        self.assertEqual(value['budget'], 128)

    def test_role_and_background_are_actual_provider_input(self):
        node = dict(mode='Ask', responsibility='VISIBLE-RESPONSIBILITY', background='VISIBLE-BACKGROUND',
                    initial_prompt='INIT', round_prompt='ROUND', handoff_prompt='OUTPUT')
        text = request_text(node, [], first=False)
        self.assertIn('VISIBLE-RESPONSIBILITY', text)
        self.assertIn('VISIBLE-BACKGROUND', text)
        self.assertNotIn('INIT', text)


if __name__ == '__main__':
    unittest.main()
