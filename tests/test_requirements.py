"""Acceptance metadata refuses drift and cannot promote declarations to evidence."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.rehearsal.requirements import (
    REGISTRY, contract_anchors, documented_commands, documented_synopses, evaluate, inventory, load_json, native_evidence,
)


class RegistryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'docs').mkdir()
        (self.root / 'man').mkdir()
        (self.root / 'docs/contract.md').write_text(
            '# Contract\n\nUse exact identities.\nKeep durable receipts.\n', encoding='utf-8')
        (self.root / 'man/README.md').write_text(
            '| [aslice-x(1)](aslice-x.1.md) | `x` |\n', encoding='utf-8')
        (self.root / 'man/aslice-x.1.md').write_text('# Command x\n', encoding='utf-8')
        self.registry = {
            'version': 2, 'sources': inventory(self.root),
            'requirements': [{
                'id': 'ASLICE-TEST-001', 'statement': 'Use exact identities.',
                'owner': 'docs/contract.md', 'review': 'Reviewed the explicit clause.',
                'reviewed_sources': {'docs/contract.md': inventory(self.root)['docs/contract.md']['sha256']},
                'clauses': [{'path': 'docs/contract.md', 'start': 3, 'end': 3}],
                'implementation': [], 'implemented': False, 'platform_dependencies': [],
                'environments': ['linux-native'], 'evidence': [],
                'tests': {kind: {'scenario': kind + ' identity check', 'links': []}
                          for kind in ('positive', 'refusal', 'concurrency', 'recovery')},
            }],
            'commands': {'x': {'manuals': ['man/aslice-x.1.md'], 'implementation': 'missing',
                               'scope': 'No implementation.', 'requirements': []}},
            'classifications': [], 'specification_defects': [], 'bounded_scenarios': [],
        }

    def result(self):
        return evaluate(self.root, self.registry)

    def add_synopsis_review(self):
        name = 'man/aslice-x.1.md'
        (self.root / name).write_text('# NAME\n\nx\n\n# SYNOPSIS\n\n`aslice x` *package*\n\n# DESCRIPTION\n\nExample command.\n')
        self.registry['sources'] = inventory(self.root)
        source_hash = self.registry['sources'][name]['sha256']
        record = copy.deepcopy(self.registry['requirements'][0])
        record.update(id='ASLICE-TEST-002', owner=name+'#synopsis',
                      reviewed_sources={name: source_hash},
                      clauses=[{'path': name, 'start': 7, 'end': 7}])
        self.registry['requirements'].append(record)
        synopsis = next(iter(documented_synopses(self.root).values()))
        self.registry['commands']['x'].update(requirements=['ASLICE-TEST-002'], synopses=[{
            'id': synopsis['id'], 'sha256': synopsis['sha256'], 'source_sha256': source_hash}])
        return synopsis

    def test_syntax_mapping_needs_review_but_does_not_claim_implementation(self):
        self.add_synopsis_review()
        result = self.result()
        self.assertTrue(result['development_valid'], result['validation_errors'])
        self.assertEqual(result['synopses'][0]['commands'], ['x'])
        self.assertTrue(result['synopses'][0]['reviewed'])
        self.assertEqual(result['review_summary']['implemented'], 0)
        self.assertFalse(result['complete'])

    def test_family_tables_must_agree_after_inventory_refresh(self):
        main = self.root / 'man/aslice.1.md'
        main.write_text('| [aslice-x(1)](aslice-x.1.md) | `x`, `unlisted` |\n')
        self.registry['sources'] = inventory(self.root)
        self.assertIn('command family tables disagree: man/README.md and man/aslice.1.md',
                      self.result()['validation_errors'])

    def test_syntax_change_invalidates_binding_after_source_review(self):
        self.add_synopsis_review()
        path = self.root / 'man/aslice-x.1.md'
        path.write_text(path.read_text().replace('*package*', '*package* [`--force`]'))
        self.registry['sources'] = inventory(self.root)
        self.registry['requirements'][1]['reviewed_sources']['man/aslice-x.1.md'] = self.registry['sources']['man/aslice-x.1.md']['sha256']
        result = self.result()
        self.assertFalse(result['development_valid'])
        self.assertFalse(result['synopses'][0]['reviewed'])
        self.assertTrue(any('synopsis review invalidated' in error for error in result['validation_errors']))

    def test_body_change_invalidates_unchanged_syntax_review(self):
        self.add_synopsis_review()
        path = self.root / 'man/aslice-x.1.md'
        path.write_text(path.read_text().replace('Example command.', 'Requires fresh administrator approval.'))
        self.registry['sources'] = inventory(self.root)
        result = self.result()
        self.assertTrue(any('synopsis review invalidated' in error for error in result['validation_errors']))
        self.assertFalse(result['synopses'][0]['reviewed'])

    def test_syntax_mapping_cannot_borrow_unrelated_requirement(self):
        self.add_synopsis_review()
        self.registry['commands']['x']['requirements'] = ['ASLICE-TEST-001']
        result = self.result()
        self.assertFalse(result['synopses'][0]['reviewed'])
        self.assertTrue(any('no covering reviewed requirement' in error for error in result['validation_errors']))

    def test_duplicate_and_unknown_syntax_bindings_are_refused(self):
        self.add_synopsis_review()
        bindings = self.registry['commands']['x']['synopses']
        bindings.append(copy.deepcopy(bindings[0]))
        bindings.append({'id': 'nonexistent'})
        errors = self.result()['validation_errors']
        self.assertTrue(any('duplicate synopsis binding' in error for error in errors))
        self.assertTrue(any('unknown synopsis binding' in error for error in errors))

    def test_syntax_cannot_be_attached_to_another_family(self):
        self.add_synopsis_review()
        self.registry['commands']['x']['manuals'] = ['man/aslice-other.1.md']
        self.assertTrue(any('another command family' in error for error in self.result()['validation_errors']))

    def test_multiline_synopsis_preserves_options_and_ignores_examples(self):
        path = self.root / 'man/aslice-x.1.md'
        path.write_text('# SYNOPSIS\n\n`aslice x` [*selectors*]\n`query` *SQL* [`--json`]\n\n# EXAMPLES\n\n`aslice x` example\n')
        blocks = list(documented_synopses(self.root).values())
        self.assertEqual(len(blocks), 1)
        self.assertEqual((blocks[0]['start'], blocks[0]['end']), (3, 4))
        self.assertEqual(blocks[0]['text'], '`aslice x` [*selectors*]\n`query` *SQL* [`--json`]')

    def test_cross_reference_requires_explicit_review_and_canonical_owner(self):
        self.add_synopsis_review()
        source = 'man/aslice-db.1.md'
        (self.root / source).write_text('# SYNOPSIS\n\n`aslice x` *package*\n')
        self.registry['sources'] = inventory(self.root)
        record = copy.deepcopy(self.registry['requirements'][1])
        record.update(id='ASLICE-TEST-003', clauses=[{'path': source, 'start': 3, 'end': 3}])
        record['reviewed_sources'][source] = self.registry['sources'][source]['sha256']
        self.registry['requirements'].append(record)
        block = next(item for item in documented_synopses(self.root).values() if item['path'] == source)
        binding = {'id': block['id'], 'sha256': block['sha256'],
                   'source_sha256': self.registry['sources'][source]['sha256'],
                   'cross_reference': True, 'reason': 'Database page references the existing x command.'}
        self.registry['commands']['x']['requirements'].append('ASLICE-TEST-003')
        self.registry['commands']['x']['synopses'].append(binding)
        self.assertTrue(self.result()['development_valid'], self.result()['validation_errors'])
        binding.pop('reason')
        self.assertTrue(any('another command family' in error for error in self.result()['validation_errors']))
        binding['reason'] = 'Explicit reference.'
        record['owner'] = source+'#synopsis'
        record['reviewed_sources'].pop('man/aslice-x.1.md')
        self.assertTrue(any('another command family' in error for error in self.result()['validation_errors']))

    def test_root_syntax_is_global_only_with_a_covering_fresh_review(self):
        source = 'man/aslice.1.md'
        (self.root / source).write_text('# SYNOPSIS\n\n`aslice` *command*\n\n# FAMILIES\n\n| [aslice-x(1)](aslice-x.1.md) | `x` |\n')
        self.registry['sources'] = inventory(self.root)
        self.assertFalse(self.result()['synopses'][0]['reviewed'])
        record = copy.deepcopy(self.registry['requirements'][0])
        record.update(id='ASLICE-TEST-002', owner=source+'#synopsis',
            clauses=[{'path': source, 'start': 3, 'end': 3}],
            reviewed_sources={source: self.registry['sources'][source]['sha256']})
        self.registry['requirements'].append(record)
        result = self.result()
        self.assertTrue(result['development_valid'], result['validation_errors'])
        self.assertTrue(result['synopses'][0]['reviewed'])
        self.assertEqual(result['synopses'][0]['commands'], [])
        self.assertEqual(result['synopses'][0]['global_requirements'], ['ASLICE-TEST-002'])
        record['reviewed_sources'][source] = '0' * 64
        self.assertFalse(self.result()['synopses'][0]['reviewed'])

    def test_development_valid_does_not_mean_release_complete(self):
        result = self.result()
        self.assertTrue(result['development_valid'])
        self.assertFalse(result['complete'])
        self.assertFalse(result['requirements'][0]['implemented'])
        self.assertFalse(result['requirements'][0]['tested'])
        self.assertFalse(result['requirements'][0]['operational'])
        source = next(item for item in result['inventory'] if item['path'] == 'docs/contract.md')
        self.assertEqual(source['unreviewed_lines'], [1, 4])

    def test_source_change_invalidates_review(self):
        path = self.root / 'docs/contract.md'
        path.write_text(path.read_text() + 'Refuse old keys.\n')
        result = self.result()
        self.assertFalse(result['development_valid'])
        self.assertFalse(result['requirements'][0]['review_valid'])
        self.assertTrue(any('source changed' in error for error in result['validation_errors']))

    def test_refreshing_inventory_does_not_bless_stale_requirement_reviews(self):
        path = self.root / 'docs/contract.md'
        path.write_text(path.read_text() + 'Require administrator consent.\n')
        self.registry['sources'] = inventory(self.root)
        result = self.result()
        self.assertFalse(result['development_valid'])
        self.assertFalse(result['requirements'][0]['review_valid'])
        source = next(item for item in result['inventory'] if item['path'] == 'docs/contract.md')
        self.assertIn(3, source['unreviewed_lines'])
        self.assertIn('ASLICE-TEST-001: review invalidated: docs/contract.md', result['validation_errors'])

    def test_owning_contract_change_invalidates_unchanged_summary(self):
        owner = self.root / 'docs/authority.md'
        owner.write_text('# Authority\nExact identity includes epoch.\n')
        record = self.registry['requirements'][0]
        record['owner'] = 'docs/authority.md'
        self.registry['sources'] = inventory(self.root)
        record['reviewed_sources']['docs/authority.md'] = self.registry['sources']['docs/authority.md']['sha256']
        self.assertTrue(self.result()['development_valid'])
        owner.write_text('# Authority\nExact identity includes epoch and revision.\n')
        self.registry['sources'] = inventory(self.root)
        self.assertFalse(self.result()['requirements'][0]['review_valid'])

    def test_review_cannot_omit_source_or_authority_binding(self):
        self.registry['requirements'][0]['reviewed_sources'] = {}
        self.assertFalse(self.result()['development_valid'])

    def test_nonexistent_owner_section_does_not_count_as_reviewed(self):
        record = self.registry['requirements'][0]
        record['owner'] = 'docs/contract.md#contract'
        self.assertTrue(self.result()['development_valid'])
        record['owner'] = 'docs/contract.md#wrong-owner-section'
        result = self.result()
        self.assertFalse(result['development_valid'])
        self.assertFalse(result['requirements'][0]['review_valid'])
        source = next(item for item in result['inventory'] if item['path'] == 'docs/contract.md')
        self.assertIn(3, source['unreviewed_lines'])

    def test_anchors_in_code_examples_cannot_authorize_a_section(self):
        text = '''# Contract
## 1.2 `Exact` identity
## Repeated
## Repeated
<a id="stable-owner"></a>
```markdown
# Fake authority
<a id="fake-owner"></a>
```
~~~text
## Another fake authority
~~~
'''
        self.assertEqual(contract_anchors(text), {
            'contract', '12-exact-identity', 'repeated', 'repeated-1', 'stable-owner'})

    def test_added_and_removed_sources_are_not_silently_ignored(self):
        (self.root / 'docs/contract.md').unlink()
        (self.root / 'docs/new.md').write_text('New contract\n')
        errors = self.result()['validation_errors']
        self.assertIn('source removed: docs/contract.md', errors)
        self.assertIn('source not inventoried: docs/new.md', errors)

    def test_inventory_order_is_independent_of_host_path_comparison(self):
        (self.root / 'docs/Z.md').write_text('Uppercase filename\n')
        (self.root / 'docs/a.md').write_text('Lowercase filename\n')
        names = list(inventory(self.root))
        self.assertEqual(names, sorted(names))

    def test_git_text_newlines_are_portable_but_archive_bytes_are_exact(self):
        path = self.root / 'docs/contract.md'
        path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
        self.assertTrue(self.result()['development_valid'])
        (self.root / 'docs/refs').mkdir()
        reference = self.root / 'docs/refs/source.txt'
        reference.write_bytes(b'incorporated requirement\n')
        self.registry['sources'] = inventory(self.root)
        reference.write_bytes(b'incorporated requirement\r\n')
        self.assertFalse(self.result()['development_valid'])

    def test_duplicate_ids_and_out_of_bounds_ranges_fail(self):
        self.registry['requirements'].append(copy.deepcopy(self.registry['requirements'][0]))
        self.registry['requirements'][1]['clauses'][0]['end'] = 100
        errors = self.result()['validation_errors']
        self.assertTrue(any('duplicate requirement ID' in error for error in errors))
        self.assertTrue(any('invalid source range' in error for error in errors))

    def test_exclusion_cannot_overlap_current_requirement(self):
        self.registry['classifications'] = [{'path': 'docs/contract.md', 'start': 3, 'end': 4,
            'sha256': self.registry['sources']['docs/contract.md']['sha256'],
            'kind': 'historical', 'reason': 'Test overlap.'}]
        self.assertTrue(any('overlaps' in error for error in self.result()['validation_errors']))

    def test_exclusion_needs_review_reason(self):
        self.registry['classifications'] = [{'path': 'docs/contract.md', 'start': 4, 'end': 4,
                                            'kind': 'historical'}]
        self.assertFalse(self.result()['development_valid'])

    def test_classification_needs_fresh_review_after_source_change(self):
        self.registry['classifications'] = [{'path': 'docs/contract.md', 'start': 4, 'end': 4,
            'sha256': self.registry['sources']['docs/contract.md']['sha256'],
            'kind': 'context', 'reason': 'Test classification.'}]
        path = self.root / 'docs/contract.md'
        path.write_text(path.read_text().replace('Keep durable receipts.', 'Retain every signing reservation.'))
        self.registry['sources'] = inventory(self.root)
        result = self.result()
        self.assertIn('docs/contract.md: classification review invalidated', result['validation_errors'])
        source = next(item for item in result['inventory'] if item['path'] == 'docs/contract.md')
        self.assertIn(4, source['unreviewed_lines'])

    def test_implemented_command_cannot_rely_on_missing_implementation(self):
        self.registry['commands']['x'].update(implementation='implemented', requirements=['ASLICE-TEST-001'])
        self.assertFalse(self.result()['development_valid'])

    def test_new_command_requires_explicit_inventory_review(self):
        with (self.root / 'man/README.md').open('a') as output:
            output.write('| [aslice-x(1)](aslice-x.1.md) | `y` |\n')
        self.registry['sources'] = inventory(self.root)
        self.assertIn('command inventory changed: y', self.result()['validation_errors'])

    def test_missing_implementation_and_test_paths_fail(self):
        record = self.registry['requirements'][0]
        record['implemented'] = True
        record['implementation'] = ['src/missing.cpp']
        record['tests']['positive']['links'] = ['tests/missing.py::test_x']
        errors = self.result()['validation_errors']
        self.assertTrue(any('missing implementation file' in error for error in errors))
        self.assertTrue(any('missing test:' in error for error in errors))

    def test_path_escape_is_rejected(self):
        self.registry['requirements'][0]['implementation'] = ['../escape.cpp']
        with self.assertRaises(ValueError):
            self.result()

    def test_self_asserted_pass_does_not_create_evidence(self):
        record = self.registry['requirements'][0]
        record['evidence'] = [{'status': 'passed', 'qualification': 'physical'}]
        status = self.result()['requirements'][0]
        self.assertFalse(status['tested'])
        self.assertFalse(status['operational'])

    def test_defects_block_release_even_when_inventory_is_valid(self):
        self.registry['specification_defects'] = [{'id': 'CONFLICT-1',
            'contracts': ['docs/contract.md'], 'description': 'Conflicting ownership.'}]
        result = self.result()
        self.assertTrue(result['development_valid'])
        self.assertIn('specification defect: CONFLICT-1', result['mandatory_gaps'])
        self.assertFalse(result['complete'])

    def test_unknown_versions_and_fields_are_rejected(self):
        for version in (1, 3, True, '2'):
            self.registry['version'] = version
            with self.assertRaises(ValueError):
                self.result()
        self.registry['version'] = 2
        self.registry['complete'] = True
        with self.assertRaises(ValueError):
            self.result()

    def test_duplicate_json_keys_are_rejected(self):
        path = self.root / 'duplicate.json'
        path.write_text('{"version": 1, "version": 2}')
        with self.assertRaises(ValueError):
            load_json(path)


class RepositoryTests(unittest.TestCase):
    def test_current_inventory_is_valid_but_release_is_blocked(self):
        result = evaluate()
        self.assertEqual(result['validation_errors'], [])
        self.assertFalse(result['complete'])
        self.assertTrue(result['mandatory_gaps'])
        self.assertEqual(len(result['commands']), len(documented_commands(ROOT)))
        genesis = next(item for item in result['inventory'] if item['path'] == 'docs/runbooks/GENESIS.md')
        self.assertEqual(genesis['classification'], 'reviewed')
        self.assertEqual(genesis['unreviewed_lines'], [])
        current = [record for record in result['requirements'] if record['id'].startswith('ASLICE-GENESIS-')]
        self.assertTrue(current)
        self.assertTrue(any(clause['start'] == 19 for record in current for clause in record['clauses']))
        self.assertTrue(any(clause['start'] == 101 for record in current for clause in record['clauses']))
        self.assertTrue(all(not record['implemented'] and not record['operational'] for record in current))
        helpers = next(item for item in result['inventory'] if item['path'] == 'docs/HELPERS.md')
        self.assertEqual(helpers['classification'], 'reviewed')
        self.assertEqual(helpers['unreviewed_lines'], [])
        services = next(item for item in result['inventory'] if item['path'] == 'man/aslice-service.1.md')
        self.assertEqual(services['classification'], 'reviewed')
        self.assertTrue(all(item['reviewed'] for item in result['synopses']))
        self.assertTrue(all(command.get('synopses') for command in result['commands']))
        pin = next(command for command in result['commands'] if command['command'] == 'pin')
        self.assertEqual({binding['id'].split(':')[0] for binding in pin['synopses']},
                         {'man/aslice-uninstall.1.md', 'man/aslice-use.1.md'})

    def test_cli_gates_are_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.json'
            for gate, expected in [('development', 0), ('release', 1)]:
                process = subprocess.run([sys.executable, '-m', 'tools.rehearsal', 'coverage',
                    '--gate', gate, '--output', str(output)], cwd=ROOT, capture_output=True)
                self.assertEqual(process.returncode, expected, process.stderr)
                self.assertFalse(json.loads(output.read_text())['complete'])


class NativeEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'native.json'

    def write(self, value):
        self.path.write_text(json.dumps(value), encoding='utf-8')

    def test_simulated_and_unknown_receipts_are_refused(self):
        for receipt in ({'qualification': 'simulated'}, {'qualification': 'physical'}, 'physical'):
            self.write({'version': 1, 'receipts': [receipt]})
            with self.assertRaises(ValueError):
                native_evidence(self.path)

    def test_claimed_authority_and_signature_do_not_qualify_a_machine(self):
        receipt = {field: 'self-asserted' for field in ('machine', 'os_build', 'filesystem',
            'security_settings', 'configuration', 'authority', 'signature')}
        receipt.update(qualification='physical', executable_sha256='a' * 64, source_sha256='b' * 64)
        self.write({'version': 1, 'receipts': [receipt]})
        result = native_evidence(self.path)
        self.assertEqual(result['receipts'], 1)
        self.assertFalse(result['accepted'])
        self.assertEqual(len(result['sha256']), 64)

    def test_oversized_input_is_refused(self):
        self.path.write_bytes(b' ' * (4 * 1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            native_evidence(self.path)

    def test_bad_native_input_fails_before_workspace_creation_or_launch(self):
        self.write({'version': 1, 'receipts': [{'qualification': 'simulated'}]})
        workspace = self.root / 'workspace'
        process = subprocess.run([sys.executable, '-m', 'tools.rehearsal', 'run', '--suite', 'full',
            '--aslice', 'does-not-exist', '--workspace', str(workspace),
            '--native-evidence', str(self.path)], cwd=ROOT, capture_output=True)
        self.assertEqual(process.returncode, 2, process.stderr)
        self.assertFalse(workspace.exists())
        self.assertIn(b'physical qualification receipts', process.stderr)


if __name__ == '__main__':
    unittest.main()
