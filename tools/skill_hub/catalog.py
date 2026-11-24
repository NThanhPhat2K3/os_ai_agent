#!/usr/bin/env python3
"""Read skills.json. As a script, prints `name<TAB>absolute-skill-dir<TAB>agents` for shell clients."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAME = re.compile(r'[a-z0-9][a-z0-9-]{0,63}')
AGENTS = ('claude', 'codex')
# Relative path made of plain segments: no '..', no absolute paths, no empty parts.
SAFE_DIR = re.compile(r'(?!.*(?:^|/)\.\.?(?:/|$))[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*')


def load(root=ROOT):
    data = json.loads((Path(root) / 'skills.json').read_text(encoding='utf-8'))
    seen = set()
    for skill in data['skills']:
        if not NAME.fullmatch(skill['name']) or skill['name'] in seen:
            raise ValueError(f"bad or duplicate skill name: {skill['name']!r}")
        seen.add(skill['name'])
        if skill['source'] == 'vendor' and skill.get('vendor') not in data['vendors']:
            raise ValueError(f"unknown vendor for {skill['name']}")
        agents = skill.get('agents', list(AGENTS))
        if not agents or any(a not in AGENTS for a in agents):
            raise ValueError(f"bad agents for {skill['name']}: {agents!r}")
        up = skill.get('upstream')
        if up is not None and (up.get('vendor') not in data['vendors'] or not SAFE_DIR.fullmatch(up.get('file', ''))
                               or up.get('link', 'upstream.md') not in ('upstream.md', 'upstream')):
            raise ValueError(f"bad upstream for {skill['name']}")
        for key in ('skills_dir',):
            if key in skill and not SAFE_DIR.fullmatch(skill[key]):
                raise ValueError(f"unsafe {key} for {skill['name']}: {skill[key]!r}")
    for name, vendor in data['vendors'].items():
        if not SAFE_DIR.fullmatch(vendor['skills_dir']) or not SAFE_DIR.fullmatch(vendor['path']):
            raise ValueError(f'unsafe path in vendor {name}')
    return data


def skill_rel_dir(data, skill):
    """Skill folder relative to its vendor repo root (per-skill skills_dir overrides the vendor's)."""
    vendor = data['vendors'][skill['vendor']]
    return f"{skill.get('skills_dir', vendor['skills_dir'])}/{skill['name']}"


def skill_dir(data, skill, root=ROOT):
    if skill['source'] == 'local':
        return Path(root) / 'skills' / skill['name']
    vendor = data['vendors'][skill['vendor']]
    return Path(root) / vendor['path'] / skill_rel_dir(data, skill)


def agents_of(skill):
    """Which agents get this skill (default: both)."""
    return list(skill.get('agents', AGENTS))


def upstream_link(data, skill, root=ROOT):
    """(link path inside the wrapper, path it must resolve to) for a wrapper skill."""
    up = skill['upstream']
    target = Path(root) / data['vendors'][up['vendor']]['path'] / up['file']
    name = up.get('link', 'upstream.md')
    return Path(root) / 'skills' / skill['name'] / name, (target if name == 'upstream.md' else target.parent)


def enabled(data, vendor):
    return {s['name'] for s in data['skills'] if s.get('vendor') == vendor}


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    root = Path(args[0]) if args else ROOT
    catalog = load(root)
    for item in catalog['skills']:
        print(f"{item['name']}\t{skill_dir(catalog, item, root)}\t{','.join(agents_of(item))}")
    if '--check-upstream' in sys.argv:
        bad = [s['name'] for s in catalog['skills'] if 'upstream' in s
               and (lambda l, t: not (l.is_symlink() and l.resolve() == t.resolve() and t.exists()))(*upstream_link(catalog, s, root))]
        sys.exit(f"upstream link wrong or missing: {', '.join(bad)}" if bad else 0)
