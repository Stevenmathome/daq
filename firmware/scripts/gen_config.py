"""Build hook. PlatformIO runs this, and so can you:

    python3 scripts/gen_config.py config.yaml include/config_gen.h
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _delegate_to_system_python(env) -> None:
    # PlatformIO executes this file with its own interpreter, which does not
    # have PyYAML. The system python3 is the one the tests and the README use.
    python = shutil.which("python3")
    if python is None:
        print("config error: python3 was not found on PATH", file=sys.stderr)
        env.Exit(1)
    root = Path(env.subst("$PROJECT_DIR"))
    # SCons exec's this file, so __file__ does not exist here.
    script = root / "scripts" / "gen_config.py"
    result = subprocess.run(
        [python, str(script), str(root / "config.yaml"), str(root / "include" / "config_gen.h")],
        check=False,
    )
    if result.returncode != 0:
        env.Exit(result.returncode)


def _run_cli(src: Path, dst: Path) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from configtool import ConfigError, generate
    except ImportError:
        print(
            "config error: PyYAML is not installed. Run: python3 -m pip install pyyaml",
            file=sys.stderr,
        )
        return 1
    try:
        generate(src, dst)
    except ConfigError as exc:
        print(f"config error: {src}", file=sys.stderr)
        for line in exc.errors:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"generated {dst}")
    return 0


try:
    Import("env")  # type: ignore[name-defined]  # noqa: F821
except Exception:
    env = None

if env is not None:
    _delegate_to_system_python(env)
elif __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: gen_config.py <config.yaml> <out.h>", file=sys.stderr)
        sys.exit(2)
    sys.exit(_run_cli(Path(sys.argv[1]), Path(sys.argv[2])))
