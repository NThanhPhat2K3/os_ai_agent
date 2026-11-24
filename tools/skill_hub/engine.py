"""Release selection and upstream checks for the Skill Hub."""
import re
from datetime import datetime, timezone


def version_key(value):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', value)
    if not match:
        raise ValueError(f'unsupported release version: {value}')
    return tuple(map(int, match.groups()))


def choose_release(current, releases, cooldown=14, now=None):
    now = now or datetime.now(timezone.utc)
    current_key = version_key(current)
    valid = []
    for version, date in releases:
        try:
            key = version_key(version)
            when = datetime.fromisoformat(date.replace('Z', '+00:00'))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if key > current_key and when <= now:
                valid.append((key, version, when))
        except (ValueError, TypeError, AttributeError):
            continue
    valid.sort(reverse=True)
    if not valid:
        return {'status': 'up-to-date', 'recommended': None}
    eligible = [entry for entry in valid if (now - entry[2]).total_seconds() >= cooldown * 86400]
    return {'status': 'update-available' if eligible else 'too-new',
            'latest': valid[0][1], 'recommended': eligible[0][1] if eligible else None}


def new_dependencies(old, new, enabled):
    pattern = r'superpowers:([a-z0-9-]+)'
    return set(re.findall(pattern, new)) - set(re.findall(pattern, old)) - set(enabled)

import concurrent.futures
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
from tools.skill_hub.catalog import enabled as _enabled, load as _load_catalog
ENABLED = frozenset(_enabled(_load_catalog(ROOT), 'superpowers'))
NPM = 'https://registry.npmjs.org/'
PYPI = 'https://pypi.org/pypi/'
GITHUB = 'https://api.github.com/'


def get_json(url):
    request = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'os-ai-agent-skill-hub'})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


NPM_PACKAGES = {'context7': '@upstash/context7-mcp', 'ccusage': 'ccusage', 'tokscale': 'tokscale', 'skills-cli': 'skills'}
PYPI_PACKAGES = {'serena': 'serena-agent', 'basic-memory': 'basic-memory'}


def check_package(name, pin, cooldown, now):
    if name in NPM_PACKAGES:
        data = get_json(NPM + urllib.parse.quote(NPM_PACKAGES[name], safe=''))
        versions = [(v, t) for v, t in data['time'].items() if v in data['versions']]
    else:
        package = PYPI_PACKAGES[name]
        data = get_json(PYPI + package + '/json')
        versions = []
        for version, artifacts in data['releases'].items():
            dates = [item.get('upload_time_iso_8601') for item in artifacts if not item.get('yanked') and item.get('upload_time_iso_8601')]
            if dates:
                versions.append((version, min(dates)))
    return {'id': name, 'current': pin, **choose_release(pin, versions, cooldown, now)}


def choose_commit(current, candidates, cooldown=14, now=None):
    """Pick an upgrade target from commits listed newest first (GitHub order).

    Only commits NEWER than `current` are considered, so this can never suggest a
    downgrade. If `current` is not in the list, it is older than every listed commit.
    """
    now = now or datetime.now(timezone.utc)
    shas = [sha for sha, _ in candidates]
    newer = candidates[:shas.index(current)] if current in shas else candidates
    base = {'id': 'superpowers', 'current': current, 'latest': shas[0] if shas else current}
    if not newer:
        return {**base, 'status': 'up-to-date', 'recommended': None}
    eligible = [sha for sha, when in newer if when <= now and (now - when).total_seconds() >= cooldown * 86400]
    if not eligible:
        return {**base, 'status': 'too-new', 'recommended': None}
    return {**base, 'status': 'update-available', 'recommended': eligible[0]}


def run_git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True, text=True, timeout=10).stdout.strip()


def get_submodule_pin():
    return run_git('rev-parse', 'HEAD:vendor/superpowers')


def github_json(path):
    auth = subprocess.run(['gh', 'auth', 'status'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10) if __import__('shutil').which('gh') else None
    if auth and auth.returncode == 0:
        return json.loads(subprocess.run(['gh', 'api', path], check=True, capture_output=True, text=True, timeout=10).stdout)
    return get_json(GITHUB + path)


def check_superpowers(cooldown, now):
    current = get_submodule_pin()
    commits = github_json('repos/obra/superpowers/commits?sha=main&per_page=100')
    if not isinstance(commits, list) or not commits:
        raise ValueError('GitHub returned no commits')
    candidates = [(item['sha'], datetime.fromisoformat(item['commit']['committer']['date'].replace('Z', '+00:00'))) for item in commits]
    result = choose_commit(current, candidates, cooldown, now)
    candidate = result['recommended']
    if candidate:
        # Would the enabled trio start depending on a skill we have not enabled?
        missing = set()
        for skill in sorted(ENABLED):
            old = skill_text(current, skill)
            new = skill_text(candidate, skill)
            if old != new:
                result.setdefault('changed_skills', []).append(skill)
            missing |= new_dependencies(old, new, ENABLED)
        if missing:
            result['status'] = 'warning'
            result['warning'] = 'enabled skills now require: ' + ', '.join(sorted(missing))
    return result


def skill_text(ref, skill):
    url = f'https://raw.githubusercontent.com/obra/superpowers/{ref}/skills/{skill}/SKILL.md'
    request = urllib.request.Request(url, headers={'User-Agent': 'os-ai-agent-skill-hub'})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return ''   # skill removed upstream: treat as changed
        raise


def checks(cooldown=14):
    with (ROOT / 'pins.json').open(encoding='utf-8') as source:
        pins = json.load(source)
    now = datetime.now(timezone.utc)
    jobs = [(key, lambda key=key: check_package(key, pins[key], cooldown, now)) for key in (*NPM_PACKAGES, *PYPI_PACKAGES) if key in pins]
    jobs.append(('superpowers', lambda: check_superpowers(cooldown, now)))
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = [(name, pool.submit(fn)) for name, fn in jobs]
        for name, future in futures:
            try:
                results.append(future.result())
            except Exception as error:
                results.append({'id': name, 'current': pins.get(name, ''), 'status': 'error', 'error': str(error)})
    return results
