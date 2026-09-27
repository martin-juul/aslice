"""Assertions over real executable output; no implementation of client decisions."""
import json

from .fixtures import seed_catalogs
from .model import Model


def fixture_lifecycle(workspace, executable, seed, launch):
    model = Model(workspace, seed)
    if "/work/prefix" in model.state["paths"]:
        raise ValueError("fixture suite requires a fresh /work/prefix")
    seed_catalogs(model)
    results = []

    def invoke(verb, arguments=(), version=1, expect=lambda _: True, expected_code=0):
        command = ["dev", "fixture", verb, "--prefix", "/work/prefix"]
        if verb in ("plan", "install", "upgrade"):
            command += ["--catalog", f"/inputs/catalog-v{version}.json"]
        code, stdout, stderr, trace = launch(workspace, executable, command + list(arguments), seed)
        try:
            output = json.loads(stdout) if expected_code == 0 else None
            passed = code == expected_code and (bool(stderr) if expected_code else not stderr) and expect(output)
        except (ValueError, KeyError, TypeError):
            output, passed = None, False
        results.append({"command": verb, "passed": bool(passed), "trace": trace.name})
        if not passed:
            raise AssertionError(f"fixture scenario failed: {verb}; see {trace}")
        return output

    try:
        invoke("init")
        invoke("plan", ["hello"], expect=lambda value: len(value["packages"]) == 2 and value["dry_run"])
        first = invoke("install", ["hello"])["generation"]
        invoke("verify", expect=lambda value: value["verified"])
        invoke("install", ["hello"], expect=lambda value: not value["changed"])
        second = invoke("upgrade", version=2)["generation"]
        Model(workspace).power_loss()
        invoke("verify", expect=lambda value: value["verified"])
        invoke("list", expect=lambda value: value["generation"] == second and
               all(item["version"] == "2.0.0" for item in value["packages"]))
        invoke("rollback", [first])
        invoke("list", expect=lambda value: value["generation"] == first and
               all(item["version"] == "1.0.0" for item in value["packages"]))
        invoke("uninstall", ["greeting"], expected_code=2)
        invoke("uninstall", ["hello"])
        invoke("autoremove")
        invoke("list", expect=lambda value: value["packages"] == [])
    except AssertionError as error:
        return {"passed": False, "error": str(error), "steps": results}
    return {"passed": True, "steps": results, "modeled_power_loss": True,
            "executes_installed_payload": False}
