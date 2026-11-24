#!/usr/bin/env python3
"""Read skills.json. As a script, prints `name<TAB>absolute-skill-dir` for shell clients."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAME = re.compile(r'[a-z0-9][a-z0-9-]{0,63}')


def load(root=ROOT):
    data = json.loads((Path(root) / 'skills.json').read_text(encoding='utf-8'))
    seen = set()
    for skill in data['skills']:
        if not NAME.fullmatch(skill['name']) or skill['name'] in seen:
            raise ValueError(f"bad or duplicate skill name: {skill['name']!r}")
        seen.add(skill['name'])
        if skill['source'] == 'vendor' and skill.get('vendor') not in data['vendors']:
            raise ValueError(f"unknown vendor for {skill['name']}")
    return data


def skill_dir(data, skill, root=ROOT):
    if skill['source'] == 'local':
        return Path(root) / 'skills' / skill['name']
    vendor = data['vendors'][skill['vendor']]
    return Path(root) / vendor['path'] / vendor['skills_dir'] / skill['name']


def enabled(data, vendor):
    return {s['name'] for s in data['skills'] if s.get('vendor') == vendor}


if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    catalog = load(root)
    for item in catalog['skills']:
        print(f"{item['name']}\t{skill_dir(catalog, item, root)}")
