"""Versioned, memory-side bank prompts for the offline Hindsight campaign."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config/bank-profile.json"
CONTRACT = "hindsight-bank-profile-config-v1"


def load_config() -> dict:
    """Read and validate the tracked bank prompt/configuration contract."""
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if (not isinstance(config, dict) or config.get("contract") != CONTRACT
            or not isinstance(config.get("version"), str) or not config["version"]
            or not isinstance(config.get("retain_mission"), str) or not config["retain_mission"]
            or not isinstance(config.get("observations_mission"), str) or not config["observations_mission"]
            or not isinstance(config.get("entity_labels"), list) or len(config["entity_labels"]) != 1):
        raise ValueError("bank_profile_config_invalid")
    label = config["entity_labels"][0]
    if (not isinstance(label, dict) or label.get("key") != "kind"
            or label.get("type") != "value" or label.get("optional") is not True
            or label.get("tag") is not True or len(label.get("values", [])) != 1
            or label["values"][0].get("value") != "profile"):
        raise ValueError("bank_profile_label_config_invalid")
    return config


def create_payload(config: dict) -> dict:
    return {
        "retain_mission": config["retain_mission"],
        "enable_observations": config["enable_observations"],
        "observations_mission": config["observations_mission"],
    }


def update_payload(config: dict) -> dict:
    return {
        "enable_auto_consolidation": config["enable_auto_consolidation"],
        "entity_labels": config["entity_labels"],
    }


def verify_readback(config: dict, expected: dict) -> dict:
    """Require exact agreement for every bank setting this workflow owns."""
    labels = config.get("entity_labels")
    if isinstance(labels, dict):
        labels = labels.get("attributes")
    projection = {
        "enable_auto_consolidation": config.get("enable_auto_consolidation"),
        "enable_observations": config.get("enable_observations"),
        "retain_mission": config.get("retain_mission"),
        "observations_mission": config.get("observations_mission"),
        "entity_labels": labels,
    }
    required = {
        "enable_auto_consolidation": expected["enable_auto_consolidation"],
        "enable_observations": expected["enable_observations"],
        "retain_mission": expected["retain_mission"],
        "observations_mission": expected["observations_mission"],
        "entity_labels": expected["entity_labels"],
    }
    if projection != required:
        raise RuntimeError("bank_config_readback_mismatch")
    return projection
