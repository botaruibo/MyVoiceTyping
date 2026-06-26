#!/usr/bin/env python3
"""
Benchmark self-hosted rewrite backends used by my voice typing.

对比对象：
- ollama: 通过 LocalLlamaRewrite 调用本机 Ollama/OpenAI-compatible HTTP 服务。
- llama.cpp: 通过 LocalLlamaCppRewrite 直接加载本地 GGUF 模型。

运行：
    .venv/bin/python test_selfhost_rewrite_perf.py
    .venv/bin/python test_selfhost_rewrite_perf.py --backend llama_cpp
"""

from __future__ import annotations

import argparse
import statistics
import time
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from src.components.config_manager import get_config_manager
from src.core.text_rewrite import LocalLlamaCppRewrite, LocalLlamaRewrite


CORRECTION_SYSTEM_PROMPT = (
    "你是一个中文文本纠错助手。请根据用户提供的原始文本生成纠正后的文本，"
    "保持原意，不扩写，不解释，只输出纠正后的文本。"
)

SAMPLES = [
    "少先队员因该为老人让坐。",
    "机七学习是人工智能领遇最能体现智能的一个分知。",
    "这个功能的转录速渡有点慢 prompt 好像没有起做用。",
]


@dataclass
class RewritePerfResult:
    name: str
    ok: bool
    error: str = ""
    init_sec: float = 0.0
    warmup_sec: float = 0.0
    rewrite_times: list[float] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)

    @property
    def avg_rewrite_sec(self) -> float:
        return statistics.mean(self.rewrite_times) if self.rewrite_times else 0.0

    @property
    def p95_rewrite_sec(self) -> float:
        if not self.rewrite_times:
            return 0.0
        if len(self.rewrite_times) == 1:
            return self.rewrite_times[0]
        return statistics.quantiles(self.rewrite_times, n=20)[-1]

    @property
    def startup_cost_sec(self) -> float:
        return self.init_sec + self.warmup_sec


class SelfHostRewritePerformanceTest(unittest.TestCase):
    """性能对比测试类：统计自托管 rewrite 后端的初始化、预热和热调用耗时。"""

    max_tokens = 96

    def make_llama_cpp(self) -> LocalLlamaCppRewrite:
        rewriter = LocalLlamaCppRewrite(main_prompt=CORRECTION_SYSTEM_PROMPT)
        rewriter.temperature = 0.0
        rewriter.max_tokens = self.max_tokens
        return rewriter

    def make_ollama(self) -> LocalLlamaRewrite:
        config = get_config_manager()
        model_name = config.get("llama_cpp_ollama_tag") or config.get("ollama_model")
        rewriter = LocalLlamaRewrite(
            model_name=model_name,
            main_prompt=CORRECTION_SYSTEM_PROMPT,
        )
        rewriter.temperature = 0.0
        rewriter.num_predict = self.max_tokens
        return rewriter

    @staticmethod
    def _elapsed(fn: Callable[[], object]) -> tuple[object, float]:
        start = time.perf_counter()
        value = fn()
        return value, time.perf_counter() - start

    def benchmark_backend(self, name: str, factory: Callable[[], object]) -> RewritePerfResult:
        result = RewritePerfResult(name=name, ok=False)
        try:
            rewriter, construct_sec = self._elapsed(factory)
            if hasattr(rewriter, "ensure_loaded"):
                _, init_sec = self._elapsed(rewriter.ensure_loaded)
            else:
                _, init_sec = self._elapsed(rewriter.test_local_llama)
            if hasattr(rewriter, "warm_up"):
                _, warmup_sec = self._elapsed(rewriter.warm_up)
            else:
                _, warmup_sec = self._elapsed(lambda: rewriter.rewrite("少先队员因该为老人让坐。"))

            result.init_sec = construct_sec + init_sec
            result.warmup_sec = warmup_sec

            for sample in SAMPLES:
                output, rewrite_sec = self._elapsed(lambda s=sample: rewriter.rewrite(s))
                result.rewrite_times.append(rewrite_sec)
                result.outputs.append(str(output))

            result.ok = True
            return result
        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"
            return result

    def run_selected(self, backends: list[str]) -> list[RewritePerfResult]:
        factories: dict[str, Callable[[], object]] = {
            "ollama": self.make_ollama,
            "llama_cpp": self.make_llama_cpp,
        }
        return [
            self.benchmark_backend(name, factories[name])
            for name in backends
        ]

    def test_selfhost_rewrite_backends(self) -> None:
        results = self.run_selected(["ollama", "llama_cpp"])
        self.print_report(results)
        self.assertTrue(any(r.ok for r in results), "至少需要一个本地 rewrite 后端可用")

    @staticmethod
    def print_report(results: list[RewritePerfResult]) -> None:
        print("\n===== Self-host Rewrite Performance =====")
        for result in results:
            print(f"\n[{result.name}]")
            if not result.ok:
                print(f"不可用: {result.error}")
                continue
            print(f"初始化耗时: {result.init_sec:.2f}s")
            print(f"预热耗时: {result.warmup_sec:.2f}s")
            print(f"启动期总成本(init+warmup): {result.startup_cost_sec:.2f}s")
            print(f"热调用平均耗时: {result.avg_rewrite_sec:.2f}s")
            print(f"热调用P95耗时: {result.p95_rewrite_sec:.2f}s")
            for sample, output, spent in zip(SAMPLES, result.outputs, result.rewrite_times):
                print(f"- {spent:.2f}s | {sample} => {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark local self-host rewrite backends.")
    parser.add_argument(
        "--backend",
        choices=["all", "ollama", "llama_cpp"],
        default="all",
        help="选择要测试的后端。默认同时测试 ollama 和 llama_cpp。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = ["ollama", "llama_cpp"] if args.backend == "all" else [args.backend]
    test = SelfHostRewritePerformanceTest(methodName="test_selfhost_rewrite_backends")
    results = test.run_selected(selected)
    test.print_report(results)
    return 0 if any(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
