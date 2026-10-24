"""Bounded, profile-scoped model discovery. A catalog is not an entitlement."""
from pathlib import Path
import json
import time
import urllib.request
import urllib.error
from urllib.parse import urlsplit
from orchestration.common import Blocked, digest
from .graph import Invalid
from .agent_sessions import safe_text
from .session_sources import opened
import os

TTL = 300


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Blocked('模型目录重定向被拒绝；请核对已批准的服务地址')


def configured_env(profile):
    """Read only operator-approved overlays, never accept a browser endpoint/key."""
    env = {}
    for source, target in profile.get('readonly_files', []):
        if str(target).endswith('/.claude/settings.json') or str(target).endswith('.claude/settings.json'):
            with opened(source) as fd:
                value = json.loads(os.read(fd, 200001))
            env.update(value.get('env', {}))
    return env


def proxy_models(profile):
    env = configured_env(profile)
    base = env.get('ANTHROPIC_BASE_URL', 'https://api.anthropic.com').rstrip('/')
    key = env.get('ANTHROPIC_AUTH_TOKEN') or env.get('ANTHROPIC_API_KEY')
    if not key:
        raise Blocked('未配置此 Claude Profile 的 API 认证；请通过本机认证入口配置后刷新')
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise Blocked('模型发现仅访问已批准的 HTTPS 服务地址')
    url = base + ('/models' if base.endswith('/v1') else '/v1/models')
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer '+key, 'x-api-key': key,
                                              'anthropic-version': '2023-06-01'})
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=8) as response:
            raw = response.read(1000001)
        if len(raw) > 1000000: raise Invalid('代理模型目录超过读取预算')
        value = json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise Blocked(f'代理模型接口 HTTP {exc.code}；请检查认证或让中转站提供 /v1/models。预登记配置不代表完整目录') from None
    except (urllib.error.URLError, TimeoutError):
        raise Blocked('代理模型接口超时或网络不可用；可刷新或明确使用上次有效目录') from None
    if value.get('has_more'):raise Invalid('代理模型目录需要分页；当前接口未返回完整目录，请检查代理支持')
    rows = value.get('data')
    if not isinstance(rows, list) or not rows or len(rows) > 2000:
        raise Invalid('代理返回空或无效模型目录；不能据此推断只有预登记模型')
    result = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not 1 <= len(row['id']) <= 200:
            raise Invalid('代理模型目录包含无效模型身份')
        efforts = row.get('supported_reasoning_efforts', [])
        if not isinstance(efforts, list) or any(not isinstance(e, str) for e in efforts): efforts = []
        result.append(dict(id=row['id'], name=row.get('display_name') or row['id'], efforts=efforts,
                           source='proxy /v1/models', effort_source='proxy' if efforts else 'unknown',
                           inference_verified=False))
    return result


def codex_models(rpc, profile, home, cwd):
    rows, cursor, seen = [], None, set()
    for _ in range(10):
        params = {'limit': 100}
        if cursor: params['cursor'] = cursor
        response = rpc(dict(profile, home=str(home)), str(cwd), 'model/list', params)
        page = response.get('data')
        if not isinstance(page, list): raise Invalid('Codex model/list 返回无效目录')
        for row in page:
            if not isinstance(row, dict) or not isinstance(row.get('model'), str): raise Invalid('Codex 模型身份无效')
            rows.append(dict(id=row['model'], name=row.get('displayName') or row['model'],
                efforts=[e['reasoningEffort'] for e in row.get('supportedReasoningEfforts', [])],
                source='Codex app-server model/list', effort_source='Codex model/list', inference_verified=False))
        cursor = response.get('nextCursor')
        if not cursor: break
        if not isinstance(cursor, str) or cursor in seen: raise Invalid('Codex 模型分页循环或身份无效')
        seen.add(cursor)
    else: raise Invalid('Codex 模型分页超过预算；未冒充完整目录')
    if not rows: raise Invalid('Codex 返回空模型目录；请检查认证并刷新')
    return rows


class ModelCatalog:
    def __init__(self, manager):
        self.manager, self.rt, self.db = manager, manager.rt, manager.db

    def get(self, name, profile, refresh=False):
        now = time.time()
        # Profile identity + configured credential sources. Do not share a cached
        # directory across two gateways using the same Provider name.
        key = name
        identity = digest(json.dumps(profile, sort_keys=True).encode())
        try: cached = self.db.get('model-discovery', key)
        except Invalid: cached = None
        if cached and cached.get('profile_sha256') != identity: cached = None
        error = cached.get('error') if cached else None
        if refresh:
            try:
                if profile['provider'] == 'codex':
                    rows = codex_models(self.manager.rpc, profile, self.rt.rpc_home/name, self.rt.storage)
                else: rows = proxy_models(profile)
                cached = dict(id=key, profile_sha256=identity, models=rows, at=now, attempted_at=now,
                              source=rows[0]['source'], error=None)
                error = None
            except (Blocked, Invalid, OSError, ValueError, KeyError) as exc:
                error = safe_text(str(exc))
                cached = dict(cached or {}, id=key, profile_sha256=identity, attempted_at=now, error=error)
            self.db.put('model-discovery', key, cached)
            try:
                auth=self.manager.rpc(dict(profile,home=str(self.rt.rpc_home/name)),str(self.rt.storage),
                    'account/read' if profile['provider']=='codex' else 'claude/auth-status',{})
                if profile['provider']=='codex':
                    auth=dict(logged_in=bool(auth.get('account')) or auth.get('requiresOpenaiAuth') is False,
                              auth_method=(auth.get('account') or {}).get('type','unknown'),service_verified=False)
                self.db.put('auth-probe',key,dict(id=key,at=now,**auth))
            except (Blocked,OSError,ValueError,KeyError):
                self.db.put('auth-probe',key,dict(id=key,at=now,logged_in=None,auth_method='unknown',service_verified=False))
        rows = cached.get('models') if cached else None
        source = cached.get('source') if cached else None
        at = cached.get('at') if cached else None
        if rows is None:
            # Compatibility only, explicitly stale and never trusted as discovery.
            try:
                legacy = self.db.get('model-catalog', profile['provider'])
                rows, source = legacy['models'], '旧版缓存（来源尚未重新核验）'
            except Invalid:
                rows = self.rt.policy.get('models', {}).get(profile['provider'], [])
                source = '预登记配置（不是完整模型列表）'
        approved = {m['id']: m.get('efforts', []) for m in self.rt.policy.get('models', {}).get(profile['provider'], [])}
        approved.setdefault(profile['model'], [profile['effort']])
        # Always retain the explicit default, even when a gateway omits aliases.
        rows = list(rows)
        if not any(m['id'] == profile['model'] for m in rows):
            rows.append(dict(id=profile['model'], name=profile['model'], efforts=[profile['effort']],
                             source='explicit operator registration', effort_source='explicit operator registration'))
        models = []
        for m in rows:
            efforts = [e for e in m.get('efforts', []) if e in approved.get(m['id'], [])]
            if m['id'] == profile['model'] and profile['effort'] not in efforts: efforts.append(profile['effort'])
            models.append(dict(m, efforts=efforts, execution_allowed=bool(efforts),
                inference_verified=False, physical_backend='unknown', resolved_effort='unknown',
                unavailable_reason=None if efforts else '已发现；尚未登记可执行模型/强度，目录不是执行授权'))
        try:auth=self.db.get('auth-probe',key)
        except Invalid:auth=dict(logged_in=None,auth_method='unknown',service_verified=False)
        return dict(models=models, authentication=auth, source=source, updated_at=at, attempted_at=cached.get('attempted_at') if cached else None,
                    stale=at is None or now-at>TTL or bool(error), error=error, ttl_seconds=TTL,
                    discovery_complete=at is not None and now-at<=TTL and not error, physical_backend='unknown')
