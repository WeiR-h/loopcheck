import test_support
import json
from types import SimpleNamespace
import unittest
from openai.types.chat import ChatCompletion
from strands import Agent, tool
from strands.models.openai import OpenAIModel
from coach.planning_hooks import StopAtReview


class PlanningStopTests(unittest.TestCase):
    def test_real_strands_stops_after_saved_draft_without_another_provider_call(self):
        run = {}
        calls = []
        @tool
        def save_review() -> dict:
            """Save a test draft without approving it."""
            run['draft_id'] = 'offline-draft'
            return {'status':'awaiting_human_review'}
        async def create(**request):
            calls.append(request)
            self.assertEqual(len(calls),1,'No final summarization request is needed')
            return ChatCompletion.model_validate({'id':'offline','created':0,'model':'offline','object':'chat.completion',
                'choices':[{'index':0,'finish_reason':'tool_calls','message':{'role':'assistant','content':None,
                  'tool_calls':[{'id':'one','type':'function','function':{'name':'save_review','arguments':'{}'}}]}}],
                'usage':{'prompt_tokens':10,'completion_tokens':10,'total_tokens':20}})
        model=OpenAIModel(client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))),model_id='offline',stream=False)
        result=Agent(model=model,tools=[save_review],hooks=[StopAtReview(run)],callback_handler=None)('Save a draft')
        self.assertEqual(len(calls),1)
        self.assertIn('No requirements or checks have been approved',str(result))


if __name__=='__main__':unittest.main()
