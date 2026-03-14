import json
import tempfile
import os

from weather_aware_dispatcher.io.input_loader import load_input


def _write_json(data: dict) -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    return path


VALID_INPUT = {
    "grid_width": 20,
    "grid_height": 20,
    "manifest": [
        {"id": "pkg_1", "destination": [5, 5], "weight_lbs": 3},
    ],
    "weather_forecast": [
        {"direction": "EAST", "start_tick": 0, "end_tick": None},
    ],
    "obstacles": [],
}


def test_valid_input_loads_correctly():
    path = _write_json(VALID_INPUT)
    result = load_input(path)
    os.unlink(path)
    assert result.ok
    assert len(result.data.packages) == 1
    assert result.data.packages[0].id == "pkg_1"


def test_missing_required_field():
    data = {k: v for k, v in VALID_INPUT.items() if k != "manifest"}
    path = _write_json(data)
    result = load_input(path)
    os.unlink(path)
    assert not result.ok
    assert any("manifest" in e for e in result.errors)


def test_destination_on_obstacle():
    data = {
        **VALID_INPUT,
        "manifest": [{"id": "pkg_1", "destination": [5, 5], "weight_lbs": 3}],
        "obstacles": [[5, 5]],
    }
    path = _write_json(data)
    result = load_input(path)
    os.unlink(path)
    assert not result.ok
    assert any("obstacle" in e.lower() for e in result.errors)


def test_negative_weight():
    data = {
        **VALID_INPUT,
        "manifest": [{"id": "pkg_1", "destination": [5, 5], "weight_lbs": -1}],
    }
    path = _write_json(data)
    result = load_input(path)
    os.unlink(path)
    assert not result.ok
    assert any("negative" in e.lower() for e in result.errors)


def test_unreachable_destination():
    # Surround (5, 5) with obstacles
    data = {
        **VALID_INPUT,
        "manifest": [{"id": "pkg_1", "destination": [5, 5], "weight_lbs": 3}],
        "obstacles": [[5, 6], [5, 4], [4, 5], [6, 5]],
    }
    path = _write_json(data)
    result = load_input(path)
    os.unlink(path)
    assert not result.ok
    assert any("unreachable" in e.lower() for e in result.errors)


def test_duplicate_package_ids():
    data = {
        **VALID_INPUT,
        "manifest": [
            {"id": "pkg_1", "destination": [5, 5], "weight_lbs": 3},
            {"id": "pkg_1", "destination": [6, 6], "weight_lbs": 2},
        ],
    }
    path = _write_json(data)
    result = load_input(path)
    os.unlink(path)
    assert not result.ok
    assert any("duplicate" in e.lower() for e in result.errors)
