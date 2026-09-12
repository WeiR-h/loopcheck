"""Read-only connection diagnostics; never invokes a model or approves a requirement."""
import time
from urllib.parse import urlsplit

import httpx

from .project_checks import local_url
from .projects import snapshot
from .settings import MODEL_PRICES, public_model, settings


def preview_link(project, public=False):
    if public:
        path = urlsplit(project['url']).path
        # Public projects are server-owned samples. Never point a judge at their
        # own localhost or turn an arbitrary URL into a public reverse proxy.
        return path if project.get('sample') and path.startswith('/samples/') else None
    return project['url']


def probe_preview(url):
    url = local_url(url)
    try:
        with httpx.stream('GET', url, follow_redirects=False, trust_env=False, timeout=3) as response:
            if 200 <= response.status_code < 300:
                return {'ready': True, 'status': response.status_code, 'reason': 'reachable'}
            return {'ready': False, 'status': response.status_code,
                    'reason': 'redirect' if 300 <= response.status_code < 400 else 'http_error'}
    except httpx.TimeoutException:
        return {'ready': False, 'reason': 'timeout'}
    except httpx.HTTPError:
        return {'ready': False, 'reason': 'unreachable'}


def inspect(service, owner, project_id):
    p = service.get(owner, project_id, 'project')
    try:
        source = snapshot(p['root'])
        source_result = {'ready': True, 'version': source['hash'], 'files': len(source['files'])}
    except (OSError, ValueError):
        source_result = {'ready': False, 'reason': 'source_unavailable'}
    preview = probe_preview(p['url'])
    model = public_model()
    budget = service.store.budget()
    remaining = max(0, settings()['budget_cny'] - budget['reported_cny'] - budget['unknown_reserved_cny'])
    prices = MODEL_PRICES.get(model['model'], (0, 0))
    reservation = (32000 * prices[0] + 2500 * prices[1]) / 1000000
    # Enough for one request is a readiness hint, not a guarantee that a whole
    # planning run will fit. BudgetModel remains the authoritative request gate.
    model['can_start'] = bool(model['configured'] and remaining >= reservation)
    reqs = service.current_requirements(owner, project_id)
    active = [r for r in reqs if r['enabled']]
    return {'checked_at': time.time(), 'project_id': project_id, 'source': source_result,
            'preview': preview, 'model': model, 'remaining_budget_cny': round(remaining, 6),
            'active_requirements': len(active), 'uncovered_requirements': sum(not r['flow'] for r in active),
            'can_recheck': bool(source_result['ready'] and preview['ready'] and active),
            'can_plan': bool(source_result['ready'] and preview['ready'] and model['can_start']),
            'model_calls': 0, 'note': 'Connection readiness only; not an acceptance result or a model-availability test.'}
