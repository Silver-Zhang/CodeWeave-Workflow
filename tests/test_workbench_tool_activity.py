import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from studio.tool_activity import group_tools,visible_content

class ToolProjectionTests(unittest.TestCase):
    def test_visible_text_blocks_are_readable_without_protocol_or_hidden_thinking(self):
        text=visible_content('[{"type":"input_text","text":"Script completed\\n12 tests passed"},{"type":"thinking","text":"HIDDEN"}]')
        self.assertEqual(text,'Script completed\n12 tests passed');self.assertNotIn('HIDDEN',text)
    def test_ordinary_structured_tool_data_is_preserved(self):
        import json
        for value in ({'rows':[1,2],'answer':'data'},{'type':{'schema':'object'},'rows':[1]},[{'type':['custom'],'value':2}]):
            self.assertEqual(json.loads(visible_content(value)),value)
    def test_double_encoded_visible_text_is_decoded_before_final_redaction(self):
        import json
        from studio.agent_sessions import safe_text
        text=visible_content(json.dumps(json.dumps([{'type':'text','text':'token=synthetic-private-value'}])))
        self.assertEqual(text,'token=synthetic-private-value');self.assertNotIn('synthetic-private-value',safe_text(text))
    def test_parallel_same_name_results_pair_by_native_id_not_order(self):
        rows=group_tools([
            dict(kind='custom_tool_call',call_id='alpha',name='exec',content='alpha-command',at='2026-10-24T00:00:00Z'),
            dict(kind='custom_tool_call',call_id='beta',name='exec',content='beta-command',at='2026-10-24T00:00:01Z'),
            dict(kind='custom_tool_call_output',call_id='beta',content='beta-result',at='2026-10-24T00:00:03Z'),
            dict(kind='custom_tool_call_output',call_id='alpha',content='alpha-result',at='2026-10-24T00:00:12Z')])
        self.assertEqual([(r['result'],r['duration_seconds']) for r in rows],[('alpha-result',12),('beta-result',2)])
    def test_missing_id_never_guesses_by_same_name(self):
        rows=group_tools([dict(kind='tool_use',name='Read',content='file'),dict(kind='tool_result',content='result')])
        self.assertEqual(len(rows),2);self.assertTrue(all(r['association']=='unknown' and r['duration_seconds'] is None for r in rows))
    def test_conflicting_duplicate_identity_is_explicit_not_false_success(self):
        rows=group_tools([dict(kind='function_call',call_id='x',content='first'),dict(kind='function_call',call_id='x',content='other'),dict(kind='function_call_output',call_id='x',content='result')])
        self.assertEqual(rows[0]['association'],'conflict');self.assertIsNone(rows[0]['result']);self.assertIsNone(rows[0]['duration_seconds']);self.assertEqual(rows[0]['content'],'');self.assertIsNone(rows[0]['arguments'])
    def test_missing_or_backwards_clock_stays_unknown(self):
        for times in [(None,None),(12,3),('bad','2026-10-24T00:00:03Z')]:
            rows=group_tools([dict(kind='tool_use',call_id='x',content='read',at=times[0]),dict(kind='tool_result',call_id='x',content='text',at=times[1])]);self.assertIsNone(rows[0]['duration_seconds'])
    def test_out_of_order_events_still_use_explicit_identity(self):
        rows=group_tools([dict(kind='tool_result',call_id='x',content='result',at=12),dict(kind='tool_use',call_id='x',name='Read',content='read',at=1)])
        self.assertEqual(rows[0]['association'],'matched');self.assertEqual(rows[0]['duration_seconds'],11)

    def test_mixed_blocks_and_nested_transport_exclude_hidden_protocol(self):
        blocks=[dict(type='thinking',text='HIDDEN'),dict(type='new_protocol_block',payload='SECRET'),dict(type='text',text='public')]
        for value in (blocks,dict(type='tool_result',content=blocks),dict(type='custom_tool_call_output',output=dict(type='tool_result',content=blocks))):
            self.assertEqual(visible_content(value),'public')
    def test_unknown_only_and_nested_protocol_payloads_fail_closed(self):
        import json
        secret='INDEPENDENT-HIDDEN-PROTOCOL-SECRET'
        unknown=dict(type='new_protocol_block',payload=secret)
        for value in (unknown,[unknown],dict(type='tool_result',content=unknown),
                      {'result':{'nested':[unknown]}},json.dumps(json.dumps(unknown)),
                      [{'type':'reasoning','summary':secret}]):
            with self.subTest(value=type(value).__name__):
                self.assertNotIn(secret,visible_content(value))
                self.assertIn('没有可展示',visible_content(value))
        self.assertEqual(json.loads(visible_content({'rows':[1,2],'internal':unknown})),{'rows':[1,2]})

    def test_native_history_does_not_expose_unknown_tool_protocol(self):
        import json
        from test_workbench_runtime import fixture,structured_session
        from studio.workbench_sessions import WorkbenchSessions
        base,rt=fixture(self);path,_=structured_session(base,rt,'unknown-tool-protocol','codex')
        for payload in [dict(type='custom_tool_call',call_id='x',name='exec',input='safe'),
                        dict(type='custom_tool_call_output',call_id='x',output=dict(type='new_protocol_block',payload='INDEPENDENT-HIDDEN-PROTOCOL-SECRET'))]:
            with path.open('a') as stream:stream.write(json.dumps(dict(type='response_item',payload=payload))+'\n')
        rows=rt.session_center.discover(base.project['id'],True)['discovery']['sessions']
        row=next(x for x in rows if rt.db.get('session-handle',x['handle'])['native']['path']==str(path))
        history=WorkbenchSessions(rt).history(base.project['id'],row['handle'])
        self.assertNotIn('INDEPENDENT-HIDDEN-PROTOCOL-SECRET',json.dumps(history))
        self.assertTrue(any('没有可展示' in item['content'] for item in history['activity']))

    def test_malformed_result_types_are_not_treated_as_public_arguments(self):
        for kind in (None,True,0,[],['future_private_protocol'],{}):
            value=dict(type=kind,payload='MALFORMED-PRIVATE-PROTOCOL')
            self.assertNotIn('MALFORMED-PRIVATE-PROTOCOL',visible_content(value,protocol=True))
            self.assertNotIn('MALFORMED-PRIVATE-PROTOCOL',visible_content({'type':'tool_result','content':value}))
        ordinary={'type':{'schema':'object'},'rows':[1]}
        import json
        self.assertEqual(json.loads(visible_content(ordinary)),ordinary)
        self.assertIn('没有可展示',visible_content(ordinary,protocol=True))
        self.assertEqual(json.loads(visible_content({'rows':[1]},protocol=True)),{'rows':[1]})

    def test_encoded_protocol_budget_never_returns_opaque_private_payload(self):
        import json
        for layers in (3,4,8,12):
            value={'type':'future_private_protocol','payload':'ENCODED-PRIVATE-PROTOCOL'}
            for _ in range(layers):value=json.dumps(value)
            self.assertNotIn('ENCODED-PRIVATE-PROTOCOL',visible_content(value))
            self.assertNotIn('ENCODED-PRIVATE-PROTOCOL',visible_content(value,protocol=True))

    def test_native_history_malformed_and_encoded_results_remain_private(self):
        import json
        from test_workbench_runtime import fixture,structured_session
        from studio.workbench_sessions import WorkbenchSessions
        base,rt=fixture(self);path,_=structured_session(base,rt,'malformed-tool-results','codex')
        secret='MALFORMED-NATIVE-PRIVATE-PROTOCOL'
        values=[dict(type=t,payload=secret) for t in (None,False,0,[],['future_private_protocol'],{})]
        encoded=dict(type='future_private_protocol',payload=secret)
        for _ in range(4):encoded=json.dumps(encoded)
        values.append(encoded)
        for i,value in enumerate(values):
            with path.open('a') as stream:
                for payload in [dict(type='custom_tool_call',call_id=str(i),name='exec',input='public'),dict(type='custom_tool_call_output',call_id=str(i),output=value)]:
                    stream.write(json.dumps(dict(type='response_item',payload=payload))+'\n')
        rows=rt.session_center.discover(base.project['id'],True)['discovery']['sessions']
        row=next(x for x in rows if rt.db.get('session-handle',x['handle'])['native']['path']==str(path))
        history=WorkbenchSessions(rt).history(base.project['id'],row['handle'])
        self.assertNotIn(secret,json.dumps(history));self.assertEqual(len(history['activity']),7)
        self.assertTrue(all('没有可展示' in item['result'] for item in history['activity']))

    def test_bounded_history_reports_omitted_records(self):
        rows=group_tools([dict(kind='tool_use',call_id=str(i),content='command') for i in range(102)])
        self.assertEqual(len(rows),100);self.assertTrue(rows[0]['history_truncated']);self.assertEqual(rows[0]['call_id'],'2')
    def test_missing_content_is_unknown_and_millisecond_timestamp_is_not_guessed(self):
        rows=group_tools([dict(kind='tool_use',call_id='x',at=1780000000000,truncated='invalid'),dict(kind='tool_result',call_id='x',content='')])
        self.assertEqual(rows[0]['association'],'unknown');self.assertIsNone(rows[0]['started_at']);self.assertIsNone(rows[0]['result'])
    def test_duplicate_untimed_result_preserves_known_return_time(self):
        rows=group_tools([dict(kind='tool_use',call_id='x',content='a',at=1),dict(kind='tool_result',call_id='x',content='b',at=3),dict(kind='tool_result',call_id='x',content='b')])
        self.assertEqual(rows[0]['duration_seconds'],2);self.assertEqual(rows[0]['finished_at'],3)

if __name__=='__main__' :unittest.main()
