from strands.hooks import AfterToolsEvent, HookProvider


class StopAtReview(HookProvider):
    """A saved draft is the end of planning, not a reason for another model call."""
    def __init__(self, run): self.run = run

    def register_hooks(self, registry):
        registry.add_callback(AfterToolsEvent, self.after_tools)

    def after_tools(self, event):
        if self.run.get('draft_id'):
            event.end_turn = 'Draft saved for review. No requirements or checks have been approved by the model.'
