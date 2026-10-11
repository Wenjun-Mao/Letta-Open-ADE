import asyncio
import copy
import hashlib
import json

import httpx
import pytest

from workflows.evals.hindsight_memory_probe import bank_profile, replay
from workflows.evals.hindsight_memory_probe.driver_support import HindsightHTTP


def _returned_config(contract):
    return {
        "enable_auto_consolidation": contract["enable_auto_consolidation"],
        **bank_profile.create_payload(contract),
        "entity_labels": contract["entity_labels"],
    }


def test_configure_bank_captures_versioned_prompts_and_exact_readback(monkeypatch, tmp_path):
    contract = bank_profile.load_config()
    requests = []

    def handler(request):
        body = json.loads(request.content) if request.content else None
        requests.append((request.method, request.url.path, body))
        if request.method == "GET" and request.url.path.endswith("/config"):
            return httpx.Response(200, json={"config": _returned_config(contract)})
        return httpx.Response(200, json={"ok": True})

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            api = HindsightHTTP(client, "http://hindsight", "synthetic-key")
            campaign = replay.Campaign({"workspace_id": "offline", "sources": []}, tmp_path, api)
            await campaign.configure_bank("subject_a", "root_xiaotang")

    monkeypatch.setattr(replay, "feature_scope", lambda workspace, subject, root: {"bank_id": "bank-one"})
    asyncio.run(exercise())

    put = next(body for method, path, body in requests if method == "PUT" and path.endswith("/banks/bank-one"))
    patch = next(body for method, path, body in requests if method == "PATCH" and path.endswith("/config"))
    assert put == bank_profile.create_payload(contract)
    assert patch == {"updates": bank_profile.update_payload(contract)}

    mission = put["retain_mission"]
    description = patch["updates"]["entity_labels"][0]["description"]
    profile_text = f"{mission} {description}"
    for instruction in (
        "current preference", "clearly time-bounded former preference",
        "explicitly corrected value", "explicit preference change",
        "A former value or correction is not private solely because it is historical",
        "Preserve who said or did each thing", "the speaker's role", "time information",
        "hypothetical or unverified claims from completed events", "solo events from shared events",
        "whether the user participated", "Preserve explicit uncertainty",
        "Distinguish a factual correction", "from a preference change",
    ):
        assert instruction in mission
    for exclusion in (
        "private origin", "who participated", "relationship-specific events",
        "assistant actions or confirmations", "Never profile-tag a whole source",
    ):
        assert exclusion in profile_text
    label = patch["updates"]["entity_labels"][0]
    assert label["key"] == "kind" and label["optional"] is True and label["tag"] is True
    assert len(label["values"]) == 1 and label["values"][0]["value"] == "profile"

    readback_files = list(tmp_path.glob("*-config-readback.json"))
    assert len(readback_files) == 1
    readback = json.loads(readback_files[0].read_text())
    assert readback["profile_config_version"] == contract["version"]
    assert readback["profile_config_sha256"] == hashlib.sha256(bank_profile.CONFIG_PATH.read_bytes()).hexdigest()
    assert {key: value for key, value in readback.items()
            if key in _returned_config(contract)} == _returned_config(contract)


@pytest.mark.parametrize(
    "mutate,error",
    [
        (lambda config: config.pop("enable_observations"), "bank_profile_config_flags_invalid"),
        (lambda config: config.update(enable_observations=False), "bank_profile_config_flags_invalid"),
        (lambda config: config.update(enable_observations=1), "bank_profile_config_flags_invalid"),
        (lambda config: config.pop("enable_auto_consolidation"), "bank_profile_config_flags_invalid"),
        (lambda config: config.update(enable_auto_consolidation=True), "bank_profile_config_flags_invalid"),
        (lambda config: config.update(enable_auto_consolidation=0), "bank_profile_config_flags_invalid"),
        (lambda config: config.pop("retain_mission"), "bank_profile_config_invalid"),
        (lambda config: config.update(retain_mission="  "), "bank_profile_config_invalid"),
        (lambda config: config.pop("observations_mission"), "bank_profile_config_invalid"),
        (lambda config: config.update(observations_mission=None), "bank_profile_config_invalid"),
        (lambda config: config["entity_labels"][0].pop("description"), "bank_profile_label_config_invalid"),
        (lambda config: config["entity_labels"][0].update(description=" "), "bank_profile_label_config_invalid"),
        (lambda config: config["entity_labels"][0]["values"][0].pop("description"), "bank_profile_label_config_invalid"),
        (lambda config: config["entity_labels"][0]["values"][0].update(description=""), "bank_profile_label_config_invalid"),
        (lambda config: config["entity_labels"][0].update(optional=False), "bank_profile_label_config_invalid"),
        (lambda config: config["entity_labels"][0].update(tag=False), "bank_profile_label_config_invalid"),
        (lambda config: config["entity_labels"][0].update(values=[]), "bank_profile_label_config_invalid"),
        (lambda config: config["entity_labels"][0]["values"][0].update(value="other"), "bank_profile_label_config_invalid"),
        (lambda config: config["entity_labels"].append(copy.deepcopy(config["entity_labels"][0])), "bank_profile_label_config_invalid"),
    ],
)
def test_load_config_rejects_missing_or_malformed_contract_fields(monkeypatch, tmp_path, mutate, error):
    config = copy.deepcopy(bank_profile.load_config())
    mutate(config)
    path = tmp_path / "bank-profile.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(bank_profile, "CONFIG_PATH", path)
    with pytest.raises(ValueError, match=error):
        bank_profile.load_config()


@pytest.mark.parametrize(
    "field,mutate",
    [
        ("retain_mission", lambda config: config.update(retain_mission="changed")),
        ("observations_mission", lambda config: config.update(observations_mission="changed")),
        ("entity_labels", lambda config: config["entity_labels"][0].update(description="changed")),
        ("enable_observations", lambda config: config.update(enable_observations=False)),
        ("enable_auto_consolidation", lambda config: config.update(enable_auto_consolidation=True)),
    ],
)
def test_bank_config_readback_rejects_any_owned_setting_drift(field, mutate):
    contract = bank_profile.load_config()
    actual = copy.deepcopy(_returned_config(contract))
    mutate(actual)
    expected = {"enable_auto_consolidation": contract["enable_auto_consolidation"],
                **bank_profile.create_payload(contract), "entity_labels": contract["entity_labels"]}
    with pytest.raises(RuntimeError, match="bank_config_readback_mismatch"):
        bank_profile.verify_readback(actual, expected)
