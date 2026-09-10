def label(value): return {'by': 'label', 'value': value}
def button(value): return {'by': 'role', 'value': 'button', 'name': value}
def step(action, target=None, **kw): return {'action': action, **({'target': target} if target else {}), **kw}

BUDGET_FLOWS = [
    {'title': 'Accurate balance', 'expectation': 'Income 1200 minus spending 350 leaves 850.00', 'steps': [
        step('fill', label('Monthly income'), value='1200'), step('fill', label('Planned spending'), value='350'),
        step('click', button('Calculate balance')), step('expect_text', label('Remaining balance'), value='850.00')]},
    {'title': 'Reject invalid amounts', 'expectation': 'A negative amount displays a validation error', 'steps': [
        step('fill', label('Planned spending'), value='-3'), step('click', button('Calculate balance')),
        step('expect_text', {'by': 'role', 'value': 'alert'}, value='Enter non-negative amounts.')]},
    {'title': 'Remember after reload', 'expectation': 'Saved income, spending, and balance survive a reload', 'steps': [
        step('fill', label('Monthly income'), value='2300'), step('fill', label('Planned spending'), value='150'),
        step('click', button('Calculate balance')), step('reload'),
        step('expect_value', label('Monthly income'), value='2300'), step('expect_value', label('Planned spending'), value='150'),
        step('expect_text', label('Remaining balance'), value='2150.00')]},
]
