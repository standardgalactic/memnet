"""Run the view logic under Node, so the audit sees what the page would draw."""

import json
import shutil
import subprocess
from pathlib import Path

CLI = Path(__file__).with_name("view_cli.js")


def available():
    return shutil.which("node") is not None


def run_view(scene, show_provisional=False, trail=None, inspect=None):
    req = {"scene": scene, "options": {"showProvisional": show_provisional, "trail": trail or []},
           "inspect": inspect or []}
    out = subprocess.run(["node", str(CLI)], input=json.dumps(req), capture_output=True,
                         text=True, check=True)
    return json.loads(out.stdout)
