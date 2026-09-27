"""Small solver cases checked by exhaustive assignments, independent of C++ search.

The oracle covers exact constraints and wildcard dependencies, target filtering,
missing names and cycles. It is intentionally not a second package client.
"""
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

BINARY = Path(sys.argv.pop(1)).resolve() if __name__ == "__main__" else None


def feasible_assignments(packages, roots):
    names = sorted({package["name"] for package in packages})
    domains = [[None] + [package for package in packages if package["name"] == name and
                         package["min_os"] == "10.11" and package["flavor"] == "v1"] for name in names]
    feasible = set()
    for assignment in itertools.product(*domains):
        chosen = {name: package for name, package in zip(names, assignment) if package is not None}
        if not set(roots) <= chosen.keys():
            continue
        if any(dependency not in chosen or (constraint != "*" and chosen[dependency]["version"] != constraint[1:])
               for package in chosen.values() for dependency, constraint in package["dependencies"].items()):
            continue
        # Compute transitive closure as a Boolean matrix. A diagonal edge is a
        # cycle; this uses no candidate ordering or recursive backtracking.
        reachable = {(name, dependency) for name, package in chosen.items() for dependency in package["dependencies"]}
        for intermediate in names:
            reachable |= {(left, right) for left in names for right in names
                          if (left, intermediate) in reachable and (intermediate, right) in reachable}
        if any((name, name) in reachable for name in chosen):
            continue
        required = set(roots) | {right for left, right in reachable if left in roots}
        if required != chosen.keys():
            continue
        feasible.add(tuple(sorted((name, package["version"]) for name, package in chosen.items())))
    return feasible


def package(name, version, dependencies=None, **kwargs):
    return {"name": "core:" + name, "version": f"{version}.0.0", "min_os": "10.11", "flavor": "v1",
            "dependencies": dependencies or {}, "files": {}, **kwargs}


@unittest.skipUnless(BINARY, "run through CTest")
class SolverOracleTests(unittest.TestCase):
    def test_bounded_catalogs_against_every_assignment(self):
        randomizer = random.Random(170927)
        cases = [
            ([package("a", 1)], ["core:a"]),
            ([package("a", 1, {"core:a": "*"})], ["core:a"]),
            ([package("a", 1, {"core:missing": "*"})], ["core:a"]),
            ([package("a", 1), package("a", 2, {"core:b": "=2.0.0"}), package("b", 1)], ["core:a"]),
        ]
        for _ in range(96):
            packages = []
            for name in ("a", "b", "c"):
                for version in (1, 2):
                    dependencies = {"core:" + other: randomizer.choice(("*", "=1.0.0", "=2.0.0"))
                                    for other in ("a", "b", "c", "missing") if randomizer.randrange(5) == 0}
                    packages.append(package(name, version, dependencies,
                        min_os=randomizer.choice(("10.11", "10.11", "10.12")),
                        flavor=randomizer.choice(("v1", "v1", "v2"))))
            roots = randomizer.choice((["core:a"], ["core:a", "core:b"], ["core:a", "core:b", "core:c"]))
            cases.append((packages, roots))
        with tempfile.TemporaryDirectory(prefix="aslice-solver-oracle-") as directory:
            catalog = Path(directory) / "catalog.json"
            satisfiable = unsatisfiable = 0
            for number, (packages, roots) in enumerate(cases):
                with self.subTest(case=number):
                    expected = feasible_assignments(packages, roots)
                    catalog.write_text(json.dumps({"format": "aslice-prototype-1", "packages": packages}))
                    actual = subprocess.run([str(BINARY), "dev", "fixture", "resolve", "--catalog", str(catalog), *roots],
                                            capture_output=True, timeout=10)
                    if expected:
                        satisfiable += 1
                        self.assertEqual(actual.returncode, 0, actual.stderr)
                        selected = tuple(sorted((item["name"], item["version"]) for item in json.loads(actual.stdout)["packages"]))
                        self.assertIn(selected, expected)
                    else:
                        unsatisfiable += 1
                        self.assertEqual(actual.returncode, 2, actual.stdout)
                        self.assertEqual(actual.stdout, b"")
                        self.assertTrue(actual.stderr)
            self.assertGreater(satisfiable, 10)
            self.assertGreater(unsatisfiable, 10)


if __name__ == "__main__":
    unittest.main()
