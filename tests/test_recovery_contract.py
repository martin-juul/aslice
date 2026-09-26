"""Structural and decision models only; not runtime cryptography or durability tests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / 'tests/fixtures' / (name + '.json')).read_text())


def validate(name, value):
    schema = json.loads((ROOT / 'schematics/json' / (name + '.schema.json')).read_text())
    Draft202012Validator(schema).validate(value)


def decision_model(records, decision_accessible=True, finalize_validated=False):
    """Input records already have authenticated chain/owner/operation bindings."""
    if not decision_accessible:
        return 'blocked'
    terminals = {r for r in records if r in ('committed', 'rolled-back')}
    if len(terminals) > 1:
        return 'blocked'
    if not terminals and 'pending-reboot' in records:
        return 'finalize' if finalize_validated else 'pending'
    return 'forward' if 'committed' in terminals else 'reverse'


def receipt_model(receipts, owner, operation, step, intent, state_matches):
    """A retained effect receipt takes precedence over a lost transport ack."""
    receipt = receipts.get((owner, operation, step))
    if receipt is None:
        return 'inspect-before-execution'
    if receipt['intent'] != intent or not state_matches:
        return 'blocked'
    return 'return-receipt'


def checkpoint_model(bundle, surviving, now, authority_verified, history_complete):
    """Cryptographic verification is an explicit input, never inferred from JSON."""
    body = bundle['signed']
    if not authority_verified or not history_complete:
        return False
    if not body['issued_at'] <= now < body['expires_at']:
        return False
    if body['expires_at'] - body['issued_at'] != 7 * 86400:
        return False
    for role, previous in surviving.items():
        offered = body['floors'].get(role)
        if offered is None or offered['version'] < previous['version']:
            return False
        if offered['version'] == previous['version'] and offered['metadata'] != previous['metadata']:
            return False
    return True


def target_model(requested, argument):
    matches = [name for name in requested if argument.startswith(name + ':')]
    if len(matches) != 1:
        raise ValueError('ambiguous or unknown target')
    name = matches[0]
    value = argument[len(name) + 1:]
    if not value:
        raise ValueError('missing value')
    return name, value


class RecoveryContracts(unittest.TestCase):
    def test_structural_fixtures_and_unknown_versions(self):
        for name in ('recovery-record', 'recovery-receipt', 'execution-catalog',
                     'recovery-gate', 'recovery-export', 'recovery-checkpoint',
                     'operation-request', 'operation-outcome', 'recovery-head',
                     'recovery-initialization', 'recovery-plan'):
            with self.subTest(name=name):
                value = fixture(name)
                validate(name, value)
                body = value['signed'] if name == 'recovery-checkpoint' else value
                body['format'] += 1
                with self.assertRaises(ValidationError):
                    validate(name, value)

    def test_conflicting_terminal_evidence_never_votes(self):
        self.assertEqual('blocked', decision_model(['committed'] * 3 + ['rolled-back']))
        self.assertEqual('forward', decision_model(['prepared', 'committed']))
        self.assertEqual('reverse', decision_model(['prepared', 'activated']))
        self.assertEqual('blocked', decision_model([], decision_accessible=False))

    def test_pending_reboot_requires_explicit_validated_finalization(self):
        self.assertEqual('pending', decision_model(['prepared', 'pending-reboot']))
        self.assertEqual('finalize', decision_model(['pending-reboot'], finalize_validated=True))
        self.assertEqual('blocked', decision_model(['pending-reboot'], decision_accessible=False,
                                                    finalize_validated=True))
        self.assertEqual('forward', decision_model(['pending-reboot', 'committed']))

    def test_lost_acknowledgement_does_not_repeat_effect(self):
        r = fixture('recovery-receipt')
        key = (r['owner'], r['operation_id'], r['step'])
        receipts = {key: r}
        self.assertEqual('return-receipt', receipt_model(receipts, *key, r['intent'], True))
        self.assertEqual('blocked', receipt_model(receipts, *key, r['intent'], False))
        self.assertEqual('blocked', receipt_model(receipts, *key, 'sha256:' + 'b' * 64, True))
        self.assertEqual('inspect-before-execution', receipt_model({}, *key, r['intent'], True))

    def test_checkpoint_requires_authority_history_and_monotonic_floors(self):
        b = fixture('recovery-checkpoint')
        old = deepcopy(b['signed']['floors'])
        self.assertTrue(checkpoint_model(b, old, 1, True, True))
        for authority, history in ((False, True), (True, False)):
            self.assertFalse(checkpoint_model(b, old, 1, authority, history))
        self.assertFalse(checkpoint_model(b, old, 604800, True, True))
        old['targets']['version'] += 1
        self.assertFalse(checkpoint_model(b, old, 1, True, True))
        old['targets']['version'] -= 1
        old['targets']['metadata']['digest'] = 'sha256:' + 'b' * 64
        self.assertFalse(checkpoint_model(b, old, 1, True, True))
        old = {'delegated/extra': {'version':1, 'metadata':{'digest':'sha256:'+'a'*64, 'size':1}}}
        self.assertFalse(checkpoint_model(b, old, 1, True, True))

    def test_qualified_target_keeps_namespace_version_and_value_colons(self):
        self.assertEqual(('audiolab:convolver@2', '+feature'),
                         target_model(['extended:ffmpeg', 'audiolab:convolver@2'], 'audiolab:convolver@2:+feature'))
        self.assertEqual(('extended:ffmpeg', '-Wl,-rpath,/example:a'),
                         target_model(['extended:ffmpeg'], 'extended:ffmpeg:-Wl,-rpath,/example:a'))
        for names, value in ((['extended:ffmpeg'], 'other:+x'), (['extended:ffmpeg'], 'extended:ffmpeg:'),
                             (['foo', 'foo:bar'], 'foo:bar:+x')):
            with self.assertRaises(ValueError):
                target_model(names, value)

    def test_unattended_activation_requires_exact_confirmation(self):
        value = fixture('operation-request')
        value['plan_digest'] = None
        with self.assertRaises(ValidationError):
            validate('operation-request', value)
        value['dry_run'] = True
        validate('operation-request', value)
        value['action'] = 'stop'
        value['operation_id'] = None
        with self.assertRaises(ValidationError):
            validate('operation-request', value)

    def test_recovery_plan_changes_invalidate_confirmation(self):
        plan = fixture('recovery-plan')
        # This ASCII-only fixture uses the same bytes under RFC 8785 and this encoding.
        def digest(p):
            return hashlib.sha256(json.dumps(p, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        old = digest(plan)
        plan['omissions'] = ['audiolab:convolver']
        self.assertNotEqual(old, digest(plan))
        plan['action'] = 'continue'
        with self.assertRaises(ValidationError):
            validate('recovery-plan', plan)
        plan['interrupted_operation'] = '1' * 32
        validate('recovery-plan', plan)

    def test_post_commit_health_failure_is_not_retry_or_rollback(self):
        value = fixture('operation-outcome')
        validate('operation-outcome', value)
        self.assertTrue(value['data']['committed'])
        self.assertFalse(value['data']['recovery_required'])
        self.assertFalse(value['data']['verification_complete'])
        value['data']['retry_safe'] = True
        with self.assertRaises(ValidationError):
            validate('operation-outcome', value)

    def test_partial_recovery_cannot_claim_activation_or_completed_repair(self):
        value = fixture('operation-outcome')
        value['data']['outcome'] = 'replacement_prepared_activation_blocked'
        value['data']['activation_allowed'] = True
        with self.assertRaises(ValidationError):
            validate('operation-outcome', value)
        value['data']['activation_allowed'] = False
        value['data']['outcome'] = 'repaired'
        value['data']['recovery_required'] = True
        with self.assertRaises(ValidationError):
            validate('operation-outcome', value)

    def test_export_cannot_claim_completeness_with_missing_participants(self):
        value = fixture('recovery-export')
        value['missing_components'] = ['protected']
        with self.assertRaises(ValidationError):
            validate('recovery-export', value)
        value['complete'] = False
        validate('recovery-export', value)
        value['files'][0]['path'] = '../outside'
        with self.assertRaises(ValidationError):
            validate('recovery-export', value)

    def test_record_chain_and_unknown_change_kind_refused(self):
        value = fixture('recovery-record')
        value['sequence'] = 2
        with self.assertRaises(ValidationError):
            validate('recovery-record', value)
        value['previous'] = 'sha256:' + 'a' * 64
        value['changes'] = [{'kind':'grant-root', 'version':1, 'key':'x', 'before':None, 'after':None}]
        with self.assertRaises(ValidationError):
            validate('recovery-record', value)


if __name__ == '__main__':
    unittest.main()
