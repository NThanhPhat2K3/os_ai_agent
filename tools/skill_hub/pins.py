#!/usr/bin/env python3
"""Read a single validated pin for shell clients."""
import json
import re
import sys


def main():
    with open(sys.argv[1], encoding='utf-8') as source:
        value = json.load(source)[sys.argv[2]]
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+_-]*', value):
        raise ValueError('invalid pin')
    print(value)


if __name__ == '__main__':
    main()
