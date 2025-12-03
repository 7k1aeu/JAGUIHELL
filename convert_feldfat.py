#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FlDigiグリフ辞書（*.CXX) -> Python モジュール変換ツール

使い方:
    python tools/convert_feldfat.py /path/to/FeldFat-14.cxx
    python tools/convert_feldfat.py "FeldFat-14.cxx"   # ワイルドカード等で複数見つかる場合はエラーになります

注意:
    - 入力ファイルは必ず1つである必要があります（ワイルドカードを使っても、結果が1つでなければエラー）。
    - 出力ファイル名は固定で `fldigi_ascii_glyphs.py`（入力ファイルと同じディレクトリ）になります。
"""
import sys
import re
import ast
from glob import glob
from pathlib import Path
from typing import Dict, List, Optional


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def parse_feldfat(path: Path) -> Optional[Dict[str, List[int]]]:
    """
    手続き的パーサに置き換え、正規表現で取りこぼすケースを回避します。
    - 各エントリをブレース単位でスキャンし、キー（'x' または 数字）と内側の配列を抽出します。
    - 抽出失敗時に詳細診断を _err() で出力します。
    """
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        raise OSError(f"Failed to read '{path}': {e}") from e

    glyphs: Dict[str, List[int]] = {}
    i = 0
    length = len(text)
    matches_total = 0
    skipped = 0

    # quick hint if expected marker not present
    if "fntchr" not in text and "feldfat" not in text:
        _err("[parse_feldfat] Hint: 'fntchr' or 'feldfat' not found in file content.")

    while True:
        # find next opening brace that might start an entry
        start = text.find("{", i)
        if start == -1:
            break
        # attempt to parse an entry of form { key, { ... } , }
        j = start + 1
        # skip whitespace
        while j < length and text[j].isspace():
            j += 1
        if j >= length:
            break

        # parse key: either quoted char (single quote) possibly escaped, or number
        key_raw = None
        try:
            if text[j] == "'":
                # parse single-quoted char handling escapes
                k = j + 1
                sb = []
                escaped = False
                while k < length:
                    ch = text[k]
                    if escaped:
                        sb.append(ch)
                        escaped = False
                        k += 1
                        continue
                    if ch == "\\":
                        escaped = True
                        k += 1
                        continue
                    if ch == "'":
                        # end of quoted
                        break
                    sb.append(ch)
                    k += 1
                else:
                    # unterminated quote
                    i = start + 1
                    skipped += 1
                    _err(f"[parse_feldfat] Skipped unterminated quoted key starting at {start}")
                    continue
                inner = "".join(sb)
                # escape backslash and single-quote so ast.literal_eval can evaluate a safe Python literal
                escaped_inner = inner.replace("\\", "\\\\").replace("'", "\\'")
                key_raw = "'" + escaped_inner + "'"  # make a python literal
                k += 1  # position after closing quote
                pos_after_key = k
            else:
                # parse number token (may have leading spaces)
                k = j
                # accept optional sign? but file uses digits only
                num_m = re.match(r"\s*([0-9]+)", text[j:])
                if num_m:
                    num_str = num_m.group(1)
                    key_raw = num_str
                    pos_after_key = j + num_m.end(1)
                else:
                    # not a key we recognize; advance and continue
                    i = start + 1
                    skipped += 1
                    _err(f"[parse_feldfat] Skipped unrecognized key at pos {start}: next chars {text[j:j+20]!r}")
                    continue

            # after key expect comma
            # skip whitespace
            k = pos_after_key
            while k < length and text[k].isspace():
                k += 1
            if k >= length or text[k] != ",":
                i = start + 1
                skipped += 1
                _err(f"[parse_feldfat] Expected ',' after key at pos {pos_after_key}, found {text[k:k+1]!r}")
                continue
            k += 1
            # skip whitespace until inner '{'
            while k < length and text[k].isspace():
                k += 1
            if k >= length or text[k] != "{":
                i = start + 1
                skipped += 1
                _err(f"[parse_feldfat] Expected '{{' for values after key at pos {k}, found {text[k:k+1]!r}")
                continue

            # parse inner brace-balanced block
            inner_start = k
            depth = 0
            m = k
            while m < length:
                ch = text[m]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        # include closing brace position m
                        inner_end = m
                        break
                m += 1
            else:
                i = start + 1
                skipped += 1
                _err(f"[parse_feldfat] Unterminated inner '{{' starting at {inner_start}")
                continue

            vals_text = text[inner_start + 1:inner_end]  # between braces
            matches_total += 1

            # extract numeric tokens 0x... or decimal
            tokens = re.findall(r"0x[0-9A-Fa-f]+|\d+", vals_text)
            if not tokens:
                skipped += 1
                _err(f"[parse_feldfat] #{matches_total}: no numeric tokens for key_raw={key_raw!r}. vals preview: {vals_text[:120]!r}")
                # advance past this entry
                i = inner_end + 1
                continue
            try:
                values = [int(t, 0) for t in tokens]
            except Exception as e:
                skipped += 1
                _err(f"[parse_feldfat] #{matches_total}: failed numeric parse for key_raw={key_raw!r}: {e}")
                i = inner_end + 1
                continue

            # finalize key value
            if key_raw is None:
                skipped += 1
                i = inner_end + 1
                continue
            try:
                if key_raw.isdigit():
                    key = chr(int(key_raw))
                else:
                    key = ast.literal_eval(key_raw)
            except Exception as e:
                skipped += 1
                _err(f"[parse_feldfat] #{matches_total}: failed to evaluate key {key_raw!r}: {e}")
                i = inner_end + 1
                continue

            # store if non-empty
            if values:
                glyphs[key] = values

            # advance i past the entry's closing braces and any trailing commas/brackets
            i = inner_end + 1
        except Exception as ex:
            skipped += 1
            _err(f"[parse_feldfat] Exception while parsing at {start}: {ex}")
            i = start + 1
            continue

    # diagnostics
    parsed = len(glyphs)
    if parsed == 0:
        _err(f"[parse_feldfat] No glyphs parsed. matches_total={matches_total}, parsed=0, skipped={skipped}")
        # show head for debugging
        head = text[:800].replace("\n", "\\n")
        _err(f"[parse_feldfat] File head (first 800 chars): {head!s}")
        return None

    _err(f"[parse_feldfat] Parsed glyphs: {parsed} (scanned entries={matches_total}, skipped={skipped})")
    return glyphs


def write_module(glyphs: Dict[str, List[int]], out_path: Path) -> None:
    header = (
        "# Auto-generated by tools/convert_feldfat.py\n"
        "# Source: FeldFat-14.cxx\n"
        "# Format: ASCII_GLYPHS : dict mapping 1-char string -> list of integers\n\n"
    )
    try:
        with out_path.open("w", encoding="utf-8") as f:
            f.write(header)
            f.write("ASCII_GLYPHS = {\n")
            for ch in sorted(glyphs.keys()):
                vals = glyphs[ch]
                # represent character key safely
                key = repr(ch)
                vals_str = ", ".join(f"0x{v:04x}" for v in vals)
                f.write(f"    {key}: [{vals_str}],\n")
            f.write("}\n")
    except OSError as e:
        raise OSError(f"Failed to write '{out_path}': {e}") from e

    print(f"Wrote {out_path} ({len(glyphs)} glyphs)")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: convert_feldfat.py /path/to/FeldFat-14.cxx", file=sys.stderr)
        sys.exit(1)

    arg = sys.argv[1]
    candidates: List[Path] = []

    # ワイルドカード指定をサポート（例: *.CXX） — ただし必ず1つに絞る
    if "*" in arg or "?" in arg:
        for p in glob(arg):
            candidates.append(Path(p))
    else:
        p = Path(arg)
        if p.is_dir():
            for f in p.iterdir():
                if f.is_file() and f.suffix.lower() == ".cxx":
                    candidates.append(f)
        elif p.exists():
            candidates.append(p)
        else:
            parent = p.parent if p.parent.exists() else Path(".")
            for f in parent.iterdir():
                if f.name.lower() == p.name.lower():
                    candidates.append(f)

    if not candidates:
        print(f"Source not found or no matches for: {arg}", file=sys.stderr)
        sys.exit(1)

    # 入力は必ず1つであることを要求
    if len(candidates) != 1:
        print(f"Expected exactly one input file, but found {len(candidates)}. Please specify a single file.", file=sys.stderr)
        for c in candidates:
            _err(f"  match: {c}")
        sys.exit(1)

    src = candidates[0]
    if src.suffix.lower() != ".cxx":
        _err(f"[main] Warning: input file does not have '.cxx' extension: {src}")

    try:
        glyphs = parse_feldfat(src)
    except OSError as e:
        _err(str(e))
        sys.exit(3)
    except Exception as e:
        _err(f"Error while parsing '{src}': {e}")
        sys.exit(4)

    if not glyphs:
        _err("Parsing failed or no glyphs found. See diagnostics above.")
        sys.exit(2)

    # 出力ファイル名を固定
    out = src.parent / "fldigi_ascii_glyphs.py"
    try:
        write_module(glyphs, out)
    except OSError as e:
        _err(str(e))
        sys.exit(5)
    except Exception as e:
        _err(f"Error while writing '{out}': {e}")
        sys.exit(6)


if __name__ == "__main__":
    main()