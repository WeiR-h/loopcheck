import test_support
import copy
from unittest.mock import patch
from test_projects import ProjectTests, wait
from coach.projects import Projects, snapshot
from coach.project_checks import Exploration


class RequirementTests(ProjectTests):
    # Only new behaviors; the original suite runs separately.
    def change(self, operations):
        p = self.service.get(self.owner, self.p['id'], 'project')
        return self.service.requirement_draft(self.owner, p['id'], 'Daily development change', operations,
            snapshot(self.project)['hash'], p['contract_id'], check_parent=True)

    def confirm_change(self, d):
        return wait(self.service, self.owner, self.service.confirm(self.owner, d['id'], d['digest'])['id'])

    def test_uncovered_revision_lifecycle_and_history(self):
        baseline = self.approve()
        self.assertTrue(self.service.result_view(baseline)['can_accept'])
        d = self.change([{'action':'add','intent':{'title':'New coupon feature','expectation':'SAVE10 reduces the total by 10 percent','purpose':'new'}}])
        first = self.confirm_change(d)
        self.assertEqual(first['state'], 'incomplete', first)
        self.assertEqual(first['coverage']['passed'], 3)
        self.assertEqual(first['coverage']['uncovered'], 1)
        self.assertFalse(self.service.result_view(first)['can_accept'])
        self.assertFalse(self.service.result_view(baseline)['can_accept'])
        req = self.service.current_requirements(self.owner, self.p['id'])[-1]
        with self.assertRaises(ValueError): self.change([{'action':'retire','id':req['id'],'revision':1,'reason':''}])
        retired = self.confirm_change(self.change([{'action':'retire','id':req['id'],'revision':1,'reason':'Deferred to next release'}]))
        self.assertEqual(retired['state'],'passed')
        self.assertEqual(retired['coverage']['retired'],1)
        restored = self.confirm_change(self.change([{'action':'restore','id':req['id'],'revision':2}]))
        self.assertEqual(restored['state'],'incomplete')
        old = self.service.current_requirements(self.owner, self.p['id'])[0]
        revised = self.confirm_change(self.change([{'action':'revise','id':old['id'],'revision':old['revision'],
            'intent':{'title':old['title'],'expectation':'Income 1200 minus expenses 350 equals 800','purpose':'preserve'}}]))
        self.assertEqual(revised['coverage']['bound'],2)
        self.assertEqual(revised['coverage']['uncovered'],2)
        self.assertEqual(self.store.budget()['calls'],0)
        self.assertIn('UNCOVERED',revised['repair_brief'])

    def test_empty_scope_never_passes_and_old_source_invalidates(self):
        baseline=self.approve()
        source=self.project/'app.js'
        original=source.read_bytes();source.write_bytes(original+b'\n// source changed\n')
        self.assertFalse(self.service.result_view(baseline)['can_accept'])
        reqs=self.service.current_requirements(self.owner,self.p['id'])
        empty=self.confirm_change(self.change([{'action':'retire','id':r['id'],'revision':r['revision'],'reason':'Scope removed'} for r in reqs]))
        self.assertEqual(empty['state'],'incomplete')
        self.assertEqual(empty['coverage']['active'],0)

    def test_migration_preserves_old_records_and_backs_up(self):
        baseline=self.approve()
        p=self.service.get(self.owner,self.p['id'],'project')
        contract=self.service.get(self.owner,p['contract_id'],'contract')
        contract.pop('requirements');contract.pop('schema')
        self.service.save('contract',contract)
        restarted=Projects(self.store)
        try:
            upgraded=restarted.get(self.owner,p['id'],'project')
            self.assertNotEqual(upgraded['contract_id'],p['contract_id'])
            self.assertNotIn('requirements',restarted.get(self.owner,p['contract_id'],'contract'))
            self.assertTrue(list(self.store.root.glob('pre-v05-*.sqlite3')))
            self.assertFalse(restarted.result_view(baseline)['can_accept'])
        finally: restarted.stop()

    def test_exploration_limits(self):
        with self.assertRaises(ValueError): Exploration.model_validate({'steps':[{'action':'navigate','value':'/'}]*7})
        with self.assertRaises(ValueError): Exploration.model_validate({'steps':[{'action':'reload'}]})

    def test_hidden_assertion_cannot_pass_with_invented_locator(self):
        from coach.project_browser import run_browser
        flow={'title':'Close an absent dialog','expectation':'The opened dialog closes','steps':[
            {'action':'expect_hidden','target':{'by':'text','value':'A control that never existed'}}]}
        result=run_browser(self.p['url'],[flow],self.root/'hidden-check')
        self.assertEqual(result['checks'][0]['status'],'inconclusive')
        self.assertFalse(result['all_passed'])

    def test_strands_dictionary_tool_arguments_save_intent(self):
        class AgentStub:
            def __init__(self, **kwargs): self.tools=kwargs['tools']
            def __call__(self, prompt):
                return self.tools[1](proposal={'requirements':[{'title':'New coupon','expectation':'SAVE10 gives ten percent discount','purpose':'new'}]})
        self.service.model_factory=lambda *args: object()
        with patch('strands.Agent',AgentStub):
            result=wait(self.service,self.owner,self.service.submit(self.owner,self.p['id'],'prepare','Add coupon functionality')['id'])
        self.assertEqual(result['state'],'awaiting_review',result)
        d=self.service.get(self.owner,result['draft_id'],'draft')
        self.assertIsNone(d['requirements'][0]['flow'])

    def test_retired_capacity_and_stale_requirement_drafts(self):
        d=self.change([{'action':'add','intent':{'title':f'Future behavior {i}','expectation':f'Business result {i}','purpose':'new'}} for i in range(10)])
        self.assertEqual(self.confirm_change(d)['state'],'incomplete')
        req=self.service.current_requirements(self.owner,self.p['id'])[0]
        stale=self.change([{'action':'revise','id':req['id'],'revision':1,'intent':{'title':'Changed behavior','expectation':'New expected outcome','purpose':'new'}}])
        retired=self.change([{'action':'retire','id':req['id'],'revision':1,'reason':'Replaced in this release'}])
        self.confirm_change(retired)
        with self.assertRaises(ValueError):self.service.confirm(self.owner,stale['id'],stale['digest'])
        self.confirm_change(self.change([{'action':'add','intent':{'title':'Replacement behavior','expectation':'Replacement outcome','purpose':'new'}}]))
        with self.assertRaises(ValueError):self.change([{'action':'restore','id':req['id'],'revision':2}])

    def test_rebuild_preserves_intent_but_clears_approval(self):
        previous=self.approve()
        req=self.service.current_requirements(self.owner,self.p['id'])[0]
        rebuilt=self.confirm_change(self.change([{'action':'rebuild','id':req['id'],'revision':1}]))
        changed=self.service.current_requirements(self.owner,self.p['id'])[0]
        self.assertEqual(changed['expectation'],req['expectation'])
        self.assertIsNone(changed['flow']);self.assertEqual(changed['revision'],2)
        self.assertEqual(rebuilt['state'],'incomplete')
        self.assertFalse(self.service.result_view(previous)['can_accept'])

    def test_restart_interrupts_queued_check(self):
        d=self.change([{'action':'add','intent':{'title':'Future feature','expectation':'Correct future result'}}])
        done=self.confirm_change(d)
        queued=copy.deepcopy(done);queued['id']='interrupted-test';queued['state']='running';queued['created']+=1
        self.service.save('run',queued)
        restarted=Projects(self.store)
        try:
            result=restarted.result_view(restarted.get(self.owner,queued['id'],'run'))
            self.assertEqual(result['state'],'interrupted');self.assertFalse(result['can_accept'])
        finally:restarted.stop()

    def test_failed_trial_retry_preserves_assertions_and_human_approval(self):
        self.confirm_change(self.change([{'action':'add','intent':{'title':'Exact item text','expectation':'The added item displays Milk'}}]))
        req=self.service.current_requirements(self.owner,self.p['id'])[0]
        case=self
        first={'bindings':[{'id':req['id'],'revision':1,'flow':{'title':req['title'],'expectation':req['expectation'],
            'steps':[{'action':'expect_text','target':{'by':'role','value':'listitem'},'value':'Milk'}]}}]}
        class AgentStub:
            def __init__(self,**kwargs):self.tools=kwargs['tools']
            def __call__(self,prompt):
                observation=self.tools[0](exploration={'steps':[]})
                case.assertIn('COMPLETE path',observation['context_rule'])
                unknown=copy.deepcopy(first);unknown['bindings'][0]['id']='wrong-reference'
                feedback=self.tools[1](proposal=unknown)
                case.assertEqual(feedback['allowed'][0]['id'],'R1')
                duplicate=copy.deepcopy(first)
                duplicate['bindings'].append({**copy.deepcopy(first['bindings'][0]),'id':'R1'})
                with case.assertRaisesRegex(ValueError,'Duplicate'):self.tools[1](proposal=duplicate)
                no_assertion=copy.deepcopy(first)
                no_assertion['bindings'][0]['flow']['steps']=[{'action':'reload'}]
                with case.assertRaisesRegex(ValueError,'independent browser assertion'):self.tools[1](proposal=no_assertion)
                trial=self.tools[1](proposal=first)
                case.assertEqual(trial['status'],'review_failed_trial')
                weak=copy.deepcopy(first);weak['bindings'][0]['flow']['steps'][0]['value']=''
                with case.assertRaisesRegex(ValueError,'SAME|same'):self.tools[1](proposal=weak)
                corrected=copy.deepcopy(first);corrected['bindings'][0]['flow']['steps'][0]['target']={'by':'text','value':'Milk'}
                corrected['bindings'][0]['id']='R1'
                corrected['bindings'][0]['flow'].pop('title')
                corrected['bindings'][0]['flow'].pop('expectation')
                return self.tools[1](proposal=corrected)
        self.service.model_factory=lambda *args:object()
        with patch('strands.Agent',AgentStub), patch('coach.project_browser.run_browser',side_effect=[
            {'source':'live_browser','page':'Milk'}, {'checks':[{'status':'failed','actual':'MilkDelete'}]}, {'checks':[{'status':'passed'}]}]):
            result=wait(self.service,self.owner,self.service.submit(self.owner,self.p['id'],'prepare','Verify item text','en',stage='bind')['id'])
        self.assertEqual(result['state'],'awaiting_review',result)
        self.assertEqual(len(result['trials']),2)
        self.assertIsNone(self.service.current_requirements(self.owner,self.p['id'])[0]['flow'])
        draft=self.service.get(self.owner,result['draft_id'],'draft')
        self.assertEqual(draft['requirements'][0]['flow']['steps'][0]['value'],'Milk')
        view = self.service.result_view(result)
        self.assertFalse(view['historical'], 'Latest planning activity is not an old check')
        self.assertFalse(view['can_accept'], 'A planning draft never approves the change')


# Do not rerun inherited v0.4 cases under this class.
for name in list(ProjectTests.__dict__):
    if name.startswith('test_') and name not in RequirementTests.__dict__: setattr(RequirementTests,name,None)

del ProjectTests
