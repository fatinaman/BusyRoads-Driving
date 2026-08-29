import json
from pathlib import Path


WORLD_FILE = Path(__file__).with_name("world_seed.json")


def record_world(seed, tunnels):
    """Keep the latest generated layout seed and hazards for inspection or replay."""
    WORLD_FILE.write_text(json.dumps({
        "seed": seed,
        "tunnels": tunnels,
    }, indent=2), encoding="utf-8")
