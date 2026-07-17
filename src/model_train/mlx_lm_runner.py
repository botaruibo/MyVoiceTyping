"""Run selected mlx_lm commands with broken optional sklearn disabled.

Transformers may import sklearn when it merely detects the package. MyVoiceTyping
does not need sklearn for MLX LoRA training, and some slim local environments keep
an incomplete scipy/sklearn pair. This wrapper hides sklearn from transformers
before mlx_lm is imported.
"""

from __future__ import annotations

import importlib.util
import sys


def _disable_optional_sklearn_probe() -> None:
    original_find_spec = importlib.util.find_spec

    def _find_spec(name, package=None):
        if name == "sklearn" or str(name).startswith("sklearn."):
            return None
        return original_find_spec(name, package)

    importlib.util.find_spec = _find_spec


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m src.model_train.mlx_lm_runner <lora|fuse> [args...]", file=sys.stderr)
        return 2

    command = sys.argv[1]
    sys.argv = [f"mlx_lm.{command}", *sys.argv[2:]]
    _disable_optional_sklearn_probe()

    if command == "lora":
        from mlx_lm.lora import main as lora_main

        lora_main()
        return 0
    if command == "fuse":
        from mlx_lm.fuse import main as fuse_main

        fuse_main()
        return 0

    print(f"Unsupported mlx_lm command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
