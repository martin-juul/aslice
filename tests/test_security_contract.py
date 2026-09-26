"""Executable contract models; no runtime solver, VM, signature or macOS claims.

Authentication and platform observations are explicit inputs. Small exhaustive
models exercise policy order and negative cases independently of future services.
"""
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path
import sqlite3
import tomllib
import unittest

from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / 'tests/fixtures' / (name + '.json')).read_text())


SCHEMAS = [json.loads(p.read_text()) for p in (ROOT / 'schematics/json').rglob('*.schema.json')]
REGISTRY = Registry().with_resources((s['$id'], Resource.from_contents(s)) for s in SCHEMAS)


def validate(name, value):
    schema = json.loads((ROOT / 'schematics/json' / (name + '.schema.json')).read_text())
    Draft202012Validator(schema, registry=REGISTRY).validate(value)


def closure(changed, edges):
    """Return triggering paths over recipe edges, including non-dynamic inputs."""
    paths = {name: [name] for name in changed}
    while True:
        previous = len(paths)
        for edge in edges:
            if edge['provider'] in paths and edge['consumer'] not in paths:
                paths[edge['consumer']] = paths[edge['provider']] + [edge['consumer']]
        if previous == len(paths):
            return paths


def publication(affected, authorized, completed):
    required = affected & authorized
    return required <= completed, affected - authorized


def assessment(advisory, artifact, *, now, authorized, platform, held=False):
    if (not authorized or not advisory['issued_at'] <= now < advisory['expires_at']
            or platform not in advisory['platforms']):
        return 'unknown', 'unavailable'
    for record in advisory['assessments']:
        if record['artifact_id'] == artifact and record['status'] == 'not-affected':
            return 'not-affected', 'unavailable'
    for record in advisory['fixed']:
        if artifact in record['artifacts']:
            return 'fixed', 'unavailable'
    for record in advisory['affected']:
        if artifact in record['artifacts']:
            return 'vulnerable', ('held' if held else 'fix-available') if advisory['fixed'] else 'unavailable'
    return 'unknown', 'unavailable'


def security_report(findings):
    """Retain all findings; retained generations do not masquerade as active."""
    unresolved = [f for f in findings if f['retained_generation'] is None
                  and f['vulnerability'] in ('vulnerable', 'unknown')]
    return deepcopy(findings), 3 if unresolved else 0


def admit_lock(lock, identities):
    if lock.get('lock_version') != 2 or 'selections' not in lock:
        raise ValueError('unsupported lock; regenerate without inferring choices')
    if any(identities.get(r['namespace']) != r['identity'] for r in lock['repositories']):
        raise ValueError('repository identity changed')
    for selection in lock['selections']:
        namespace = selection['selected'].split(':', 1)[0]
        if identities.get(namespace) != selection['repository_identity']:
            raise ValueError('selection authority changed')
    return True


def solve(catalog, policy, *, holds=None, exact=None):
    """Exhaustive two-package fixture solver. Versions are integer fixture ranks.

    Each candidate binds a revision/artifact; fixed is an authenticated assessment,
    not inferred from rank. Dependencies are minimum fixture ranks.
    """
    holds = holds or {}
    names = sorted(catalog)
    eligible = []
    for combination in itertools.product(*(catalog[n] for n in names)):
        selection = dict(zip(names, combination))
        if any(not c['authorized'] or not c['compatible'] or not c['stream'] for c in combination):
            continue
        if any(selection[n]['rank'] != rank for n, rank in holds.items()):
            continue
        if exact and any(selection[n]['artifact'] != artifact for n, artifact in exact.items()):
            continue
        if any(selection[d]['rank'] < rank for c in combination for d, rank in c['deps'].items()):
            continue
        if policy.startswith('security') and any(c['affected'] and not c['fixed'] for c in combination):
            continue
        eligible.append(selection)
    if not eligible:
        return None
    def objective(selected):
        versions = tuple(selected[n]['rank'] for n in names)
        costs = (sum(not c['binary'] for c in selected.values()), sum(c['bytes'] for c in selected.values()))
        return (versions if policy == 'security-minimal' else tuple(-v for v in versions), costs)
    return min(eligible, key=objective)


def consent(builds, *, interactive, answer=False, allow=False):
    return not builds or (answer if interactive else allow)


def select_origin(requested, selected, identity, choices, authorized):
    if not authorized:
        return False
    if requested == selected:
        return True
    return any(c['requested'] == requested and c['selected'] == selected
               and c['repository_identity'] == identity for c in choices)


def digest(data):
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def reference(data):
    return dict(digest=digest(data), size=len(data))


def matches(data, expected):
    return data is not None and reference(data) == expected


def apply_patch_model(base, payload, expanded_limit, memory_limit):
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result
    patch = json.loads(payload, object_pairs_hook=unique_keys)
    validate('index-patch', patch)
    if not matches(base, patch['base']):
        raise ValueError('bad base')
    if patch['result']['size'] > expanded_limit or len(base)+len(payload)+patch['result']['size'] > memory_limit:
        raise ValueError('resource bound')
    output = bytearray()
    for op in patch['operations']:
        if op['op'] == 'copy':
            end = op['offset'] + op['length']
            if end > len(base):
                raise ValueError('range outside base')
            piece = base[op['offset']:end]
        else:
            piece = bytes.fromhex(op['hex'])
        if len(output)+len(piece) > patch['result']['size']:
            raise ValueError('excess output')
        output.extend(piece)
    if not matches(output, patch['result']):
        raise ValueError('bad result')
    return bytes(output)


def refresh(active, record, mirrors, *, authenticated=True, ready=True,
            patch_limit=16, transfer_limit=64*1024**2, expanded_limit=256*1024**2,
            memory_limit=512*1024**2, elapsed=0):
    """Bounded byte-splice model; full bytes supplied after decompression.

    The real compressed decoder and process/resource enforcement need integration
    tests. Failed mirror identities are retained even when a retry succeeds.
    """
    errors = []
    if not authenticated:
        return active, ['unauthorized']
    use_diff = (matches(active, record['base']) and len(record['patches']) <= patch_limit
                and sum(p['object']['size'] for p in record['patches']) <= transfer_limit
                and record['result']['size'] <= min(expanded_limit, memory_limit) and elapsed <= 30)
    for mirror in mirrors[:3]:
        staged = active
        if use_diff:
            for patch in record['patches']:
                payload = mirror.get(patch['object']['digest'])
                try:
                    if patch['codec'] != 'byte-splice-v1' or not matches(payload, patch['object']):
                        raise ValueError('bad patch object')
                    staged = apply_patch_model(staged, payload, expanded_limit, memory_limit)
                    if not matches(staged, patch['result']):
                        raise ValueError('wrong intermediate result')
                except (ValueError, ValidationError):
                    errors.append('bad-diff')
                    staged = None
                    break
        else:
            staged = None
        if not matches(staged, record['result']):
            full = mirror.get('full')
            if (not matches(mirror.get('compressed'), record['full']['object'])
                    or not matches(full, record['full']['expanded'])
                    or not matches(full, record['result'])
                    or len(full) > min(expanded_limit, memory_limit)):
                errors.append('bad-full')
                continue
            staged = full
        if not ready:
            return active, errors + ['missing-required-object']
        return staged, errors
    return active, errors


def transaction_repositories(required, available, independently_authorized):
    return required <= available and required <= independently_authorized


def dispatch(jobs, workers, now):
    priorities = {'security': 0, 'approved-release': 1, 'freshness': 2, 'backfill': 3}
    ready = [j for j in jobs if j['state'] == 'queued' and j['ready'] is not None and j['authorized']]
    def order(job):
        rank = priorities[job['priority']]
        if rank > 1 and now - job['ready'] >= 86400:
            rank = 1
        return rank, job['ready'], job['id']
    blockers = {}
    for job in sorted(ready, key=order):
        capable = [w for w in workers if w['qualified'] and job['requirements'] <= w['capabilities']
                   and w['physical'] != job.get('independent_of')]
        free = [w for w in capable if not w['busy']]
        if free:
            # Preserve v3 for jobs that need it when another capable worker is free.
            worker = min(free, key=lambda w: ('v3' in w['capabilities'], w['id']))
            return (job['id'], worker['id']), blockers
        blockers[job['id']] = 'waiting-worker' if capable else 'no-capable-worker'
    return None, blockers


def supersede(job, replacement, *, cancel=False):
    updated = deepcopy(job)
    if job['state'] == 'queued':
        updated.update(state='superseded', replacement=replacement)
    elif cancel:
        updated.update(state='cancelled', destroyed=True, evidence_retained=True, lease_revoked=True)
    return updated


def promote(record, current, required, *, authorized=True, staging_bound=True):
    validate('maintenance-promotion', record)
    mapping = {'dev': 'develop', 'staging': 'beta', 'prod': 'master'}
    branches = all(record[side+'_branch'] == 'maintenance/'+record['incident_id']+'/'+mapping[record[side+'_environment']]
                   for side in ('from', 'to'))
    gates = {g['gate']: g['verdict'] for g in record['gates']}
    return (authorized and branches and current == record['production_baseline']
            and record['source_inventory'] == record['destination_inventory']
            and all(gates.get(g) == 'pass' for g in required)
            and len(gates) == len(record['gates'])
            and (record['to_environment'] != 'prod' or staging_bound))


def restart_actions(*, old_mapping=False, static_vulnerable=False, boot_effect=False, complete=True):
    actions = []
    if old_mapping: actions.append('restart')
    if static_vulnerable: actions.append('consumer-rebuild')
    if boot_effect: actions.append('reboot')
    if not complete: actions.append('unknown')
    return actions, 3 if actions else 0


class SecurityContracts(unittest.TestCase):
    def test_lock_version_and_retained_identity(self):
        lock=tomllib.loads((ROOT/'tests/fixtures/lock.toml').read_text())
        identities={r['namespace']:r['identity'] for r in lock['repositories']}
        self.assertTrue(admit_lock(lock,identities))
        with self.assertRaises(ValueError):admit_lock(lock,dict(core='reused-namespace'))
        for version in (1,3):
            bad=deepcopy(lock);bad['lock_version']=version
            with self.assertRaises(ValueError):admit_lock(bad,identities)
        bad=deepcopy(lock);del bad['selections']
        with self.assertRaises(ValueError):admit_lock(bad,identities)

    def test_closed_versioned_fixtures(self):
        for name in ('advisory', 'build-evidence', 'worker-capabilities', 'index-diff', 'index-patch',
                     'maintenance-promotion', 'plan', 'operation-request', 'operation-outcome'):
            with self.subTest(name=name):
                value = fixture(name)
                validate(name, value)
                key = 'plan_version' if name == 'plan' else 'format'
                for version in (0, value[key]-1, value[key]+1):
                    bad = deepcopy(value); bad[key] = version
                    with self.assertRaises(ValidationError): validate(name, bad)
                value['unrecognized'] = True
                with self.assertRaises(ValidationError): validate(name, value)

    def test_transitive_static_header_generated_bundled_and_cross_orchard(self):
        value = fixture('build-evidence')
        edges = value['recipe_dependencies']
        for kind, consumer, provider in [('header','core:headers','core:client'),
                                         ('generated','core:generated','core:headers'),
                                         ('bundled','lab:app','core:generated')]:
            edges.append(dict(consumer=consumer, provider=provider, kind=kind, input_digest=value['inputs'][0]['digest']))
        validate('build-evidence', value)
        paths = closure({'core:crypto'}, edges)
        self.assertEqual(paths['lab:app'], ['core:crypto','core:client','core:headers','core:generated','lab:app'])
        affected = set(paths); authorized = affected - {'lab:app'}
        self.assertEqual(publication(affected, authorized, authorized), (True, {'lab:app'}))
        self.assertFalse(publication(affected, authorized, authorized-{'core:client'})[0])
        # Each input type invalidates the same graph; ABI equality is irrelevant.
        for kind in ('recipe','source','toolchain','build-configuration','dependency'):
            value['triggers'][0]['kind'] = kind
            validate('build-evidence', value)
            self.assertIn('lab:app', closure({value['triggers'][0]['path'][0]}, edges))

    def test_backport_stale_hold_platform_gap_and_absence(self):
        a = fixture('advisory'); platform = a['platforms'][0]
        check = lambda artifact, **kw: assessment(a, artifact, now=kw.pop('now',150), authorized=True, platform=kw.pop('platform',platform), **kw)
        self.assertEqual(check(a['fixed'][0]['artifacts'][0]), ('fixed','unavailable'))
        self.assertEqual(a['fixed'][0]['version'], a['affected'][0]['version'])
        bad = a['affected'][0]['artifacts'][0]
        self.assertEqual(check(bad,held=True), ('vulnerable','held'))
        self.assertEqual(check(bad,now=200), ('unknown','unavailable'))
        self.assertEqual(check(bad,platform=dict(os='10.11',flavor='v1')), ('unknown','unavailable'))
        self.assertEqual(check('sha256:'+'f'*64), ('unknown','unavailable'))
        a['assessments'].append(dict(artifact_id='sha256:'+'f'*64,component=None,status='not-affected',
                                    evidence=a['assessments'][0]['evidence'],reason='Component disabled'))
        self.assertEqual(check('sha256:'+'f'*64), ('not-affected','unavailable'))
        a['fixed'] = []
        self.assertEqual(check(bad), ('vulnerable','unavailable'))

    def catalog(self):
        def candidate(rank, binary=True, fixed=True, deps=None):
            return dict(rank=rank,artifact=str(rank),binary=binary,fixed=fixed,affected=True,
                        deps=deps or {},authorized=True,compatible=True,stream=True,bytes=10)
        return {'app':[candidate(1,fixed=False),candidate(2,deps={'lib':2}),candidate(3,False,deps={'lib':3})],
                'lib':[candidate(1,fixed=False),candidate(2),candidate(3,False)]}

    def test_update_policy_before_cost_and_minimal_dependency_solution(self):
        catalog = self.catalog()
        for policy in ('install','upgrade','security'):
            result = solve(catalog,policy)
            self.assertEqual([result[n]['rank'] for n in ('app','lib')], [3,3])
        result = solve(catalog,'security-minimal')
        self.assertEqual([result[n]['rank'] for n in ('app','lib')], [2,2])
        catalog['app'][1]['deps']['lib'] = 3
        self.assertEqual(solve(catalog,'security-minimal')['lib']['rank'],3)
        self.assertIsNone(solve(catalog,'security',holds={'app':1}))
        self.assertEqual(solve(catalog,'exact-replay',exact={'app':'1','lib':'1'})['app']['rank'],1)
        self.assertIsNone(solve(catalog,'exact-replay',exact={'app':'absent'}))

    def test_authority_compatibility_and_stream_precede_version(self):
        for field in ('authorized','compatible','stream'):
            catalog = self.catalog();catalog['app'][2][field] = False
            self.assertEqual(solve(catalog,'upgrade')['app']['rank'],2)

    def test_build_consent_is_not_serialized_authority(self):
        p = fixture('plan')
        p['build_work'] = [dict(package='core:app',recipe_digest='sha256:'+'a'*64,
                                inputs=[dict(digest='sha256:'+'b'*64,size=10)],reason='New eligible version',
                                dependency_path=['core:app'],estimated_seconds=None)]
        with self.assertRaises(ValidationError):validate('plan',p)
        p['required_consents'] = ['source-builds'];validate('plan',p)
        self.assertFalse(consent(p['build_work'],interactive=False))
        self.assertFalse(consent(p['build_work'],interactive=True,answer=False))
        self.assertTrue(consent(p['build_work'],interactive=True,answer=True))
        self.assertTrue(consent(p['build_work'],interactive=False,allow=True))
        request=fixture('operation-request');request['allow_source_builds']=True
        validate('operation-request',request)

    def test_security_outcome_retains_all_unresolved_and_retained_generation(self):
        p=fixture('operation-outcome');p.update(status='incomplete-remediation',exit_code=3)
        p['security_findings']=[dict(advisory_id='A-'+str(i),repository_identity='repo',
            artifact_id='sha256:'+'a'*64,component=None,vulnerability=status,remediation=remediation,
            reason=reason,dependency_path=['core:lib','lab:app'],retained_generation=generation)
            for i,(status,remediation,reason,generation) in enumerate([
                ('vulnerable','held','pin',None),('vulnerable','unavailable','platform',None),
                ('unknown','unavailable','stale',None),('vulnerable','unavailable','cross-orchard',None),
                ('vulnerable','fix-available','retained','sha256:'+'b'*64)])]
        validate('operation-outcome',p)
        self.assertTrue(p['data']['committed'])
        self.assertEqual(len(p['security_findings']),5)
        report,code=security_report(p['security_findings'])
        self.assertEqual(code,3);self.assertEqual(report,p['security_findings'])
        self.assertEqual(security_report(report[-1:])[1],0)
        p['exit_code']=0
        with self.assertRaises(ValidationError):validate('operation-outcome',p)

    def test_virtual_provider_alias_replacement_and_namespace_reuse(self):
        for kind in ('provider','alias','replacement'):
            choice=dict(kind=kind,requested='core:tls',selected='lab:tls',repository_identity='original')
            p=fixture('plan');p['selections']=[choice];validate('plan',p)
            self.assertFalse(select_origin('core:tls','lab:tls','original',[],True))
            self.assertTrue(select_origin('core:tls','lab:tls','original',[choice],True))
            self.assertFalse(select_origin('core:tls','lab:tls','replacement-repo',[choice],True))
            self.assertFalse(select_origin('core:tls','lab:tls','original',[choice],False))

    def mirror_fixture(self):
        old,new,compressed=b'{"old":1}',b'{"new":1}',b'compressed-new'
        patch=(ROOT/'tests/fixtures/index-patch.json').read_bytes()
        record=fixture('index-diff')
        record.update(base=reference(old),result=reference(new),
                      patches=[dict(codec='byte-splice-v1',object=reference(patch),result=reference(new))],
                      full=dict(object=reference(compressed),expanded=reference(new)))
        validate('index-diff',record)
        return old,new,record,{digest(patch):patch,'full':new,'compressed':compressed}

    def test_index_staging_bad_base_limits_corruption_and_full_fallback(self):
        old,new,r,mirror=self.mirror_fixture()
        self.assertEqual(refresh(old,r,[mirror])[0],new)
        self.assertEqual(refresh(old,r,[mirror],ready=False)[0],old)
        for kw in ({'patch_limit':0},{'transfer_limit':0},{'elapsed':31}):
            self.assertEqual(refresh(old,r,[mirror],**kw)[0],new)
        self.assertEqual(refresh(b'wrong base',r,[mirror])[0],new)
        self.assertEqual(refresh(old,r,[mirror],expanded_limit=2)[0],old)
        self.assertEqual(refresh(old,r,[mirror],memory_limit=2)[0],old)
        corrupt={**mirror,r['patches'][0]['object']['digest']:b'corrupt'}
        result,errors=refresh(old,r,[corrupt]);self.assertEqual(result,new);self.assertIn('bad-diff',errors)
        result,errors=refresh(old,r,[{},mirror]);self.assertEqual(result,new);self.assertIn('bad-full',errors)
        self.assertEqual(refresh(old,r,[{},{},{},mirror])[0],old)
        self.assertEqual(refresh(old,r,[mirror],authenticated=False)[0],old)
        self.assertTrue(transaction_repositories({'core'},{'core'},{'core'}))
        self.assertFalse(transaction_repositories({'core','lab'},{'core'},{'core','lab'}))

    def test_patch_chain_ranges_duplicate_keys_and_resource_bounds(self):
        old,new,r,mirror=self.mirror_fixture()
        payload=mirror[r['patches'][0]['object']['digest']]
        self.assertEqual(apply_patch_model(old,payload,256*1024**2,512*1024**2),new)
        for key,value in [('offset',100),('length',100)]:
            bad=fixture('index-patch');bad['operations'][0][key]=value
            with self.assertRaises(ValueError):apply_patch_model(old,json.dumps(bad).encode(),1000,10000)
        with self.assertRaises(ValueError):apply_patch_model(old,payload,1000,10)
        with self.assertRaises(ValueError):apply_patch_model(old,b'{"format":1,"format":1}',1000,10000)
        bad=fixture('index-patch');bad['base']['digest']='sha256:'+'f'*64
        encoded=json.dumps(bad).encode();r['patches'][0]['object']=reference(encoded)
        result,errors=refresh(old,r,[{**mirror,digest(encoded):encoded}])
        self.assertEqual(result,new);self.assertIn('bad-diff',errors)

    def job(self, ident, priority, ready=0, **kw):
        return dict(id=ident,priority=priority,ready=ready,state='queued',authorized=True,requirements={'v1'},**kw)

    def workers(self):
        return [dict(id='pro',physical='pro',capabilities={'v1','v2'},qualified=True,busy=False),
                dict(id='laptop',physical='laptop',capabilities={'v1','v2','v3'},qualified=True,busy=False)]

    def test_dispatch_aging_fifo_security_and_scarce_capacity(self):
        jobs=[self.job('backfill','backfill'),self.job('fresh','freshness',10),self.job('release','approved-release',100)]
        self.assertEqual(dispatch(jobs,self.workers(),86399)[0],('release','pro'))
        self.assertEqual(dispatch(jobs,self.workers(),86400)[0],('backfill','pro'))
        jobs.append(self.job('security','security',86400))
        self.assertEqual(dispatch(jobs,self.workers(),86400)[0],('security','pro'))
        jobs[-1]['authorized']=False
        self.assertEqual(dispatch(jobs,self.workers(),86400)[0],('backfill','pro'))
        jobs[0]['ready']=None
        self.assertEqual(dispatch(jobs,self.workers(),86400)[0],('release','pro'))

    def test_waiting_vs_no_capable_and_independent_physical_builders(self):
        job=self.job('v3','security');job['requirements']={'v3'}
        workers=self.workers();workers[1]['busy']=True
        self.assertEqual(dispatch([job],workers,0)[1],{'v3':'waiting-worker'})
        workers[1]['qualified']=False
        self.assertEqual(dispatch([job],workers,0)[1],{'v3':'no-capable-worker'})
        workers=self.workers();job['independent_of']='laptop'
        workers.append({**workers[1],'id':'second-guest'})
        self.assertEqual(dispatch([job],workers,0)[1],{'v3':'no-capable-worker'})

    def test_supersession_cancellation_and_late_results(self):
        job=self.job('old','backfill')
        self.assertEqual(supersede(job,'new')['state'],'superseded')
        job['state']='leased'
        self.assertEqual(supersede(job,'new'),job)
        cancelled=supersede(job,'new',cancel=True)
        self.assertTrue(cancelled['destroyed'] and cancelled['evidence_retained'] and cancelled['lease_revoked'])
        self.assertIsNone(dispatch([cancelled],self.workers(),0)[0])

    def test_maintenance_identical_artifacts_baseline_branches_and_gates(self):
        r=fixture('maintenance-promotion');required={g['gate'] for g in r['gates']}
        self.assertTrue(promote(r,r['production_baseline'],required))
        for field in ('source_inventory','production_baseline'):
            bad=deepcopy(r);bad[field]='sha256:'+'f'*64
            self.assertFalse(promote(bad,r['production_baseline'],required))
        for branch in ('master','maintenance/other/master','maintenance/incident-1/beta'):
            bad=deepcopy(r);bad['to_branch']=branch
            self.assertFalse(promote(bad,r['production_baseline'],required))
        bad=deepcopy(r);bad['gates'][0]['verdict']='not-applicable'
        self.assertFalse(promote(bad,r['production_baseline'],required))
        bad['gates'].pop()
        with self.assertRaises(ValidationError):promote(bad,r['production_baseline'],required)
        self.assertFalse(promote(r,r['production_baseline'],required,authorized=False))
        self.assertFalse(promote(r,r['production_baseline'],required,staging_bound=False))

    def test_restart_rebuild_reboot_and_unknown_are_distinct(self):
        self.assertEqual(restart_actions(),([],0))
        self.assertEqual(restart_actions(static_vulnerable=True),(['consumer-rebuild'],3))
        self.assertEqual(restart_actions(old_mapping=True,boot_effect=True,complete=False),(['restart','reboot','unknown'],3))
        outcome=fixture('operation-outcome');outcome.update(command='needs-restarting',status='needs-attention',exit_code=3,data=None,inspection_coverage='partial')
        outcome['restart_findings']=[dict(action='unknown',process_id=None,service=None,artifact_id=None,advisory_ids=[],reason='Process inaccessible')]
        validate('operation-outcome',outcome)

    def test_pending_worker_fixture_is_not_qualified(self):
        worker=fixture('worker-capabilities')
        self.assertIsNone(worker['enrollment']);self.assertEqual(worker['capabilities'],[])
        laptop=json.loads((ROOT/'tests/fixtures/security/worker-laptop.json').read_text())
        validate('worker-capabilities',laptop)
        self.assertNotEqual(worker['physical_builder_id'],laptop['physical_builder_id'])
        self.assertEqual(laptop['capabilities'],[])
        worker['capabilities']=[dict(os='12',flavor='v3',cpu_features=[],os_register_state_verified=False,
            image_digest='sha256:'+'a'*64,hypervisor='fixture',ram_bytes=0,disk_bytes=0,build_seconds=None,
            test_seconds=None,vm_prepare_seconds=None,qualification='qualified',evidence=[])]
        with self.assertRaises(ValidationError):validate('worker-capabilities',worker)

    def test_database_versions_reconstruction_and_projection_constraints(self):
        for role in ('coordinator','client-cache'):
            with self.subTest(role=role), sqlite3.connect(':memory:') as db:
                db.executescript((ROOT/'docs/sqlite'/f'{role}.sql').read_text())
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],3)
                for version in (1,2,4):
                    with self.assertRaises(sqlite3.IntegrityError):
                        db.execute('INSERT INTO database_identity VALUES(1,?,?,?,?)',(role,'a'*32,'owner',version))
                db.execute('INSERT INTO database_identity VALUES(1,?,?,?,3)',(role,'a'*32,'owner'))
                for n in range(1,5):db.execute('INSERT INTO objects VALUES(?,10,?)',('sha256:'+str(n)*64,'fixture'))
                db.execute("INSERT INTO scopes VALUES('core','prod')")
                if role=='coordinator':
                    db.execute("INSERT INTO job_kinds VALUES('build')")
                    with self.assertRaises(sqlite3.IntegrityError):db.execute("INSERT INTO job_kinds VALUES('security')")
                    db.execute("INSERT INTO plans VALUES(?,'core','prod','commit',?)",('sha256:'+'1'*64,'sha256:'+'2'*64))
                    db.execute("INSERT INTO jobs VALUES(?,'core','prod',?,'build','queued')",('sha256:'+'3'*64,'sha256:'+'1'*64))
                    # Reconstructed job without priority evidence is not dispatchable.
                    self.assertEqual(db.execute('SELECT * FROM jobs JOIN scheduling USING(job_digest)').fetchall(),[])
                    with self.assertRaises(sqlite3.IntegrityError):
                        db.execute('INSERT INTO scheduling VALUES(?,?,?,?,NULL,NULL)',('sha256:'+'3'*64,'build',0,'sha256:'+'2'*64))
                    db.execute('INSERT INTO scheduling VALUES(?,?,?,?,NULL,NULL)',('sha256:'+'3'*64,'security',0,'sha256:'+'2'*64))
                    self.assertEqual(db.execute('SELECT kind,priority FROM jobs JOIN scheduling USING(job_digest)').fetchone(),('build','security'))
                else:
                    self.assertEqual(db.execute('SELECT count(*) FROM advisory_assessments').fetchone()[0],0)
                    db.execute("INSERT INTO snapshots VALUES('core','prod',?,?,200,0,0,0)",('sha256:'+'1'*64,'sha256:'+'2'*64))
                    row=('core','prod','sha256:'+'1'*64,'repo','A','sha256:'+'2'*64,'','sha256:'+'3'*64,200,'vulnerable')
                    db.execute('INSERT INTO advisory_assessments VALUES('+','.join('?'*10)+')',row)
                    with self.assertRaises(sqlite3.IntegrityError):db.execute("UPDATE advisory_assessments SET vulnerability='safe'")
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])


if __name__ == '__main__':
    unittest.main()
