#!/usr/bin/env python3
"""Convert Sogou .scel dictionaries to MyVoiceTyping hotword text files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PINYIN_TABLE_OFFSET = 0x1540
WORD_TABLE_OFFSETS = (0x2628, 0x26C4)


def _read_uint16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 2], "little", signed=False)


def _decode_utf16le(data: bytes) -> str:
    return data.decode("utf-16le", errors="ignore").strip("\x00").strip()


def _parse_pinyin_table(data: bytes, word_offset: int) -> dict[int, str]:
    pinyin: dict[int, str] = {}
    offset = PINYIN_TABLE_OFFSET
    while offset + 4 <= min(word_offset, len(data)):
        index = _read_uint16(data, offset)
        size = _read_uint16(data, offset + 2)
        offset += 4
        if index == 0 and size == 0:
            break
        if size <= 0 or offset + size > len(data):
            break
        pinyin[index] = _decode_utf16le(data[offset:offset + size])
        offset += size
    return pinyin


def _parse_words_at(data: bytes, word_offset: int) -> list[str]:
    pinyin_table = _parse_pinyin_table(data, word_offset)
    words: list[str] = []
    offset = word_offset
    data_len = len(data)

    while offset + 4 <= data_len:
        same_count = _read_uint16(data, offset)
        pinyin_size = _read_uint16(data, offset + 2)
        offset += 4
        if same_count <= 0 or pinyin_size <= 0:
            break
        offset += pinyin_size
        if offset > data_len:
            break

        for _ in range(same_count):
            if offset + 2 > data_len:
                return words
            word_size = _read_uint16(data, offset)
            offset += 2
            if word_size <= 0 or offset + word_size > data_len:
                return words
            word = _decode_utf16le(data[offset:offset + word_size])
            offset += word_size
            if word:
                words.append(word)

            if offset + 2 > data_len:
                return words
            ext_size = _read_uint16(data, offset)
            offset += 2 + ext_size
            if offset > data_len:
                return words

    return words


def parse_scel(path: Path) -> list[str]:
    data = path.read_bytes()
    candidates = []
    for offset in WORD_TABLE_OFFSETS:
        if offset < len(data):
            words = _parse_words_at(data, offset)
            candidates.append(words)
    return max(candidates, key=len) if candidates else []


def normalize_word(word: str) -> str:
    return re.sub(r"\s+", "", str(word or "").strip())


def filter_words(words: list[str], max_len: int) -> tuple[list[str], dict[str, object]]:
    seen: set[str] = set()
    kept: list[str] = []
    duplicate_count = 0
    too_long: list[str] = []
    empty_count = 0

    for raw_word in words:
        word = normalize_word(raw_word)
        if not word:
            empty_count += 1
            continue
        if max_len > 0 and len(word) > max_len:
            too_long.append(word)
            continue
        if word in seen:
            duplicate_count += 1
            continue
        seen.add(word)
        kept.append(word)

    kept.sort(key=lambda item: (len(item), item))
    stats = {
        "raw_count": len(words),
        "kept_count": len(kept),
        "duplicate_removed_count": duplicate_count,
        "empty_removed_count": empty_count,
        "too_long_removed_count": len(too_long),
        "too_long_removed_samples": too_long[:30],
    }
    return kept, stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Sogou .scel files to hotword txt dictionaries.")
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--max-len",
        type=int,
        default=0,
        help="Maximum word length to keep. Use 0 to disable length filtering.",
    )
    args = parser.parse_args()

    all_words: list[str] = []
    per_file: list[dict[str, object]] = []
    for input_path in args.inputs:
        words = parse_scel(input_path)
        all_words.extend(words)
        _kept, file_stats = filter_words(words, args.max_len)
        per_file.append({"file": str(input_path), **file_stats})

    kept, total_stats = filter_words(all_words, args.max_len)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")

    report = {
        "output": str(args.output),
        "max_len": args.max_len,
        "source_files": per_file,
        "merged": total_stats,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
