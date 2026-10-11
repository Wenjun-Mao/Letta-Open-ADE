"""Exercise the runner's declared Docker COPY surface without building an image."""

import importlib.util
import json
import shlex
import shutil

from workflows.evals.hindsight_memory_probe.validate import ROOT

WORKFLOW = ROOT
REPOSITORY = ROOT.parents[2]
DOCKERFILE = WORKFLOW / "docker/python.Dockerfile"
REQUIRED_FIXTURES = {
    "workflows/evals/hindsight_memory_probe/fixtures/campaign.json",
    "workflows/evals/hindsight_memory_probe/fixtures/semantic-diagnostic-controls-v1.json",
}


def test_runner_image_copy_surface_contains_loadable_diagnostic_inputs(tmp_path):
    instructions = []
    runner_stage = False
    for line in DOCKERFILE.read_text().splitlines():
        if line.startswith("FROM "):
            runner_stage = line == "FROM base AS runner"
        elif runner_stage and line.startswith("COPY "):
            tokens = shlex.split(line)
            instructions.append((tokens[1:-1], tokens[-1]))

    sources = {
        source
        for copied_sources, _destination in instructions
        for source in copied_sources
    }
    assert REQUIRED_FIXTURES <= sources

    image_root = tmp_path / "app"
    image_root.mkdir()
    for copied_sources, destination in instructions:
        for source in copied_sources:
            source_path = REPOSITORY / source
            if "*" in source:
                for match in REPOSITORY.glob(source):
                    target = image_root / destination / match.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(match, target)
            elif source in REQUIRED_FIXTURES or source.endswith("/diagnostic_controls.py"):
                target = image_root / destination
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target)

    fixture_root = image_root / "workflows/evals/hindsight_memory_probe/fixtures"
    campaign_path = fixture_root / "campaign.json"
    controls_path = fixture_root / "semantic-diagnostic-controls-v1.json"
    module_path = image_root / "workflows/evals/hindsight_memory_probe/diagnostic_controls.py"
    assert campaign_path.is_file() and controls_path.is_file() and module_path.is_file()

    spec = importlib.util.spec_from_file_location("runner_image_diagnostic_controls", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    controls = module.load(json.loads(campaign_path.read_text()))
    assert set(controls["cases"]) == {"q01", "q06", "q07"}
