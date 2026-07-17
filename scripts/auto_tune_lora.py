#!/usr/bin/env python3
"""Build personal voice-history dataset and run MLX LoRA auto-tuning."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model_train.auto_tune import (  # noqa: E402
    build_auto_tune_dataset,
    calculate_mlx_lora_params,
    ensure_auto_tune_models,
    run_mlx_lora_auto_tune,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MyVoiceTyping automatic MLX LoRA tuning.")
    parser.add_argument("--prepare-only", action="store_true", help="Only build dataset and download models.")
    parser.add_argument("--dataset-only", action="store_true", help="Only build train/valid/test dataset.")
    parser.add_argument("--no-upgrade", action="store_true", help="Only train LoRA adapters; do not replace the active GGUF model.")
    args = parser.parse_args()

    dataset = build_auto_tune_dataset()
    print(json.dumps({
        "dataset_dir": str(dataset.dataset_dir),
        "train_path": str(dataset.train_path),
        "valid_path": str(dataset.valid_path),
        "total_count": dataset.total_count,
        "train_count": dataset.train_count,
        "valid_count": dataset.valid_count,
        "params": calculate_mlx_lora_params(dataset.total_count),
    }, ensure_ascii=False, indent=2))

    if args.dataset_only:
        return 0

    base_model, resume_adapter = ensure_auto_tune_models()
    print(json.dumps({
        "base_model": str(base_model),
        "resume_adapter_file": str(resume_adapter or ""),
    }, ensure_ascii=False, indent=2))

    if args.prepare_only:
        return 0

    result = run_mlx_lora_auto_tune(upgrade_model=not args.no_upgrade)
    print(json.dumps({
        "run_dir": str(result.run_dir),
        "adapter_dir": str(result.adapter_dir),
        "upgraded_model_path": str(result.upgraded_model_path or ""),
        "params": result.params,
        "command": result.command,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
