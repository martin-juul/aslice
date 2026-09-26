"""Check JSON schemas/fixtures, TOML syntax, and archived-source integrity offline.

Run from any directory: python tests/check_contracts.py
Install tests/requirements.txt first. TOML parsing is not TOSD validation.
"""
import ast
import hashlib
import json
from pathlib import Path
import tomllib

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
schemas = {}
for path in (ROOT / 'schematics/json').rglob('*.schema.json'):
    data = json.loads(path.read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(data)
    schemas[path] = data
registry = Registry().with_resources(
    (data['$id'], Resource.from_contents(data)) for data in schemas.values())
fixtures = list((ROOT / 'tests/fixtures').glob('*.json'))
for path in fixtures:
    schema = schemas[ROOT / 'schematics/json' / (path.stem + '.schema.json')]
    Draft202012Validator(schema, registry=registry).validate(
        json.loads(path.read_text(encoding='utf-8')))
tomls = list((ROOT / 'schematics/toml').glob('*.tosd')) + list((ROOT / 'tests/fixtures').glob('*.toml'))
for path in tomls:
    tomllib.loads(path.read_text(encoding='utf-8'))
for path in (ROOT / 'schematics/starlark').glob('*.schema.star'):
    module = ast.parse(path.read_text(encoding='utf-8'))
    assignment = next(node for node in module.body if isinstance(node, ast.Assign))
    assert isinstance(ast.literal_eval(assignment.value), dict), path
refs = ROOT / 'docs/refs'
listed = set()
for line in (refs / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
    digest, name = line.split('  ', 1)
    assert name not in listed, f'Duplicate checksum: {name}'
    listed.add(name)
    assert hashlib.sha256((refs / name).read_bytes()).hexdigest() == digest, name
assert listed == {p.name for p in refs.iterdir() if p.is_file() and p.name != 'SHA256SUMS'}
print(f'Checked {len(schemas)} JSON schemas, {len(fixtures)} JSON fixtures, '
      f'{len(tomls)} TOML documents, Starlark data literals, and {len(listed)} archived files.')
print('TOML schema semantics and runtime security properties require separate validators/tests.')
