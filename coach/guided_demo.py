"""Optional, clearly disclosed zero-model walkthrough. Never edits a connected user project."""
import os
from pathlib import Path
import re
import shutil

from .projects import snapshot
from .settings import ROOT
from .store import uid


DISCLOSURE = 'Predefined demonstration requirements and scripted sample changes; real browser checks, no model calls. Only this session-owned sample copy is modified.'


def step(action, role=None, name='', value=''):
    return {'action': action, 'value': value, **({'target': {'by': 'role', 'value': role, 'name': name}} if role else {})}


BASELINE = [
    {'title': 'Quantity and total', 'expectation': 'Set quantity to 2: cart total is 200.00', 'steps': [step('fill', 'spinbutton', 'Quantity', '2'), step('click', 'button', 'Update cart'), step('expect_text', 'status', 'Cart total', '200.00')]},
    {'title': 'Quantity validation', 'expectation': 'Quantity 0 is rejected with a validation message', 'steps': [step('fill', 'spinbutton', 'Quantity', '0'), step('click', 'button', 'Update cart'), step('expect_text', 'alert', value='Enter a quantity from 1 to 20')]},
    {'title': 'Persist quantity', 'expectation': 'Quantity 3 remains after reload, total is 300.00', 'steps': [step('fill', 'spinbutton', 'Quantity', '3'), step('click', 'button', 'Update cart'), step('reload'), step('expect_value', 'spinbutton', 'Quantity', '3'), step('expect_text', 'status', 'Cart total', '300.00')]},
]
COUPON = {'title': 'Coupon discount', 'expectation': 'Quantity 2 with SAVE10 costs 180.00', 'purpose': 'new', 'steps': [
    step('fill', 'spinbutton', 'Quantity', '2'), step('click', 'button', 'Update cart'), step('fill', 'textbox', 'Coupon', 'SAVE10'), step('click', 'button', 'Apply coupon'), step('expect_text', 'status', 'Cart total', '180.00')]}
FEATURE = '''
const couponLabel=document.createElement('label');couponLabel.textContent='Coupon';couponLabel.htmlFor='coupon';
const coupon=document.createElement('input');coupon.id='coupon';
const apply=document.createElement('button');apply.textContent='Apply coupon';
document.querySelector('main').append(couponLabel,coupon,apply);
apply.onclick=()=>{if(coupon.value==='SAVE10')total.textContent=(Number(quantity.value)*100*.9).toFixed(2);};
'''


def directory(service, token):
    if not re.fullmatch(r'[0-9a-f]{32}', token): raise ValueError('Invalid demo identifier')
    base = (service.store.root / 'guided-demos').resolve()
    folder = base / token
    if folder.resolve() != folder or folder.is_symlink(): raise ValueError('Invalid demo directory')
    return folder


def start(service, owner):
    with service.lock:
        if service.active: raise ValueError('Wait for the current check before starting a demo')
        p = next((p for p in service.list(owner, 'project') if p.get('guided_demo')), None)
        if not p:
            if len(service.list(owner, 'project')) >= 10: raise ValueError('At most 10 projects per session')
            token = uid()
            folder = directory(service, token)
            shutil.copytree(ROOT / 'examples/cart', folder)
            p = service.connect(owner, folder, f'http://127.0.0.1:{os.environ.get("PORT", "8791")}/samples/guided/{token}/', 'Guided Cart · no API key', sample=True)
            p.update(guided_demo=token, demo_stage='baseline', demo_disclosure=DISCLOSURE)
            service.save('project', p)
        draft = None if p['contract_id'] else service.draft(owner, p['id'], 'Review predefined cart requirements. ' + DISCLOSURE, BASELINE, snapshot(p['root'])['hash'])
        return {'project': service.public(p), 'draft': service.public(draft) if draft else None, 'disclosure': DISCLOSURE}


def advance(service, owner, project_id, action, expected_source, expected_contract):
    with service.lock:
        if service.active: raise ValueError('Wait for the current check before changing the sample')
        p = service.get(owner, project_id, 'project')
        if not p.get('guided_demo'): raise ValueError('Scripted changes are only available for the guided sample copy')
        folder = directory(service, p['guided_demo'])
        if Path(p['root']).resolve() != folder: raise ValueError('Demo source does not match')
        if snapshot(folder)['hash'] != expected_source or p['contract_id'] != expected_contract:
            raise ValueError('The source or requirements changed. Refresh and review again.')
        reqs = service.current_requirements(owner, p['id'])
        if not reqs: raise ValueError('Review and confirm the baseline requirements first')
        for flow in BASELINE:
            if not any(r['enabled'] and r['expectation'] == flow['expectation'] and r['flow'] for r in reqs):
                raise ValueError('This walkthrough requires its three baseline checks. Custom requirements remain unchanged.')
        coupon = next((r for r in reqs if r['enabled'] and r['expectation'] == COUPON['expectation']), None)
        if action == 'future':
            if coupon: raise ValueError('The coupon requirement already exists')
            draft = service.requirement_draft(owner, p['id'], 'Add a future coupon requirement. ' + DISCLOSURE,
                [{'action': 'add', 'intent': {k: COUPON[k] for k in ('title', 'expectation', 'purpose')}}], expected_source,
                parent=expected_contract, check_parent=True)
            return {'draft': service.public(draft)}
        if not coupon: raise ValueError('Confirm the future coupon requirement first')
        if action == 'feature' and coupon['flow']: raise ValueError('The coupon check is already bound')
        if action == 'repair' and (p['demo_stage'] != 'fault' or not coupon['flow']):
            raise ValueError('Confirm the feature checks before restoring the sample')
        if action not in {'feature', 'repair'}: raise ValueError('Unknown demonstration action')
        base = (ROOT / 'examples/cart/app.js').read_text(encoding='utf-8')
        if base.count('count*100') != 1: raise ValueError('Bundled sample changed; cannot apply this preset')
        source = (base.replace('count*100', 'count*150') if action == 'feature' else base) + FEATURE
        target = folder / 'app.js'
        before = target.read_bytes()
        try:
            temporary = folder / 'app.tmp'
            temporary.write_text(source, encoding='utf-8')
            temporary.replace(target)
            if action == 'feature':
                draft = service.requirement_draft(owner, p['id'], 'Review preset coupon steps; a price regression was deliberately introduced in the sample. ' + DISCLOSURE,
                    [{'action': 'bind', 'id': coupon['id'], 'revision': coupon['revision'], 'flow': COUPON}], snapshot(folder)['hash'],
                    parent=expected_contract, check_parent=True)
                result = {'draft': service.public(draft)}
            else:
                result = {}
            p['demo_stage'] = 'fault' if action == 'feature' else 'repaired'
            service.save('project', p)
        except Exception:
            target.write_bytes(before)
            raise
        if action == 'repair': result['run'] = service.public(service.submit(owner, project_id))
        return result
