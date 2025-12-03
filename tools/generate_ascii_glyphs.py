#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
*.cxxからascii_glyphs.py (GLYPHS) を生成するスクリプト。

使い方:
  python tools/generate_ascii_glyphs.py "src/*.cxx" -o ascii_glyphs.py --start 32

前提:
  - 入力は各グリフごとに 14 行（横走査）を持つ配列が含まれる想定。
  - 出力は各グリフを長さ14の列ビットマップ整数リスト（GLYPHS）として出力します。
  - 各列は下->上にビットを詰め、bit0 が下端となります（左列から右列へ）。
"""
from pathlib import Path
import re
import argparse
import ast
import glob
from typing import List

HEX_RE = re.compile(r'0x[0-9A-Fa-f]+')
DEC_RE = re.compile(r'\b\d+\b')

def extract_numbers_from_text(text: str) -> List[int]:
    # まず hex を全部抽出
    nums = [int(m.group(0), 16) for m in HEX_RE.finditer(text)]
    if nums:
        return nums
    # hex が無ければ decimal を抽出（フォールバック）
    nums = [int(m.group(0)) for m in DEC_RE.finditer(text)]
    return nums

def try_import_python_data(path: Path) -> List[int]:
    # Python ファイルに配列変数がある場合の簡易抽出: list リテラルの数字を検索
    text = path.read_text(encoding='utf-8', errors='ignore')
    # 典型的な変数名を探す
    candidates = ['FONT_DATA', 'FELD_DATA', 'font_data', 'FELD_FONT_DATA', 'GLYPH_DATA']
    for name in candidates:
        m = re.search(rf'{name}\s*=\s*(\[[^\]]+\])', text, flags=re.S)
        if m:
            try:
                arr = ast.literal_eval(m.group(1))
                return [int(x) for x in arr]
            except Exception:
                pass
    # フルテキストから数値列を抽出（フォールバック）
    return extract_numbers_from_text(text)

def parse_cxx_file(path: Path) -> List[int]:
    text = path.read_text(encoding='utf-8', errors='ignore')
    nums: List[int] = []
    # 全ての初期化子ブロックを抽出して順に処理する
    blocks = re.findall(r'\{([^}]*)\}', text, flags=re.S)
    if blocks:
        for block in blocks:
            found = extract_numbers_from_text(block)
            if found:
                nums.extend(found)
    # ブロックが見つからなかった場合や追加不足ならファイル全体から抽出
    if not nums:
        nums = extract_numbers_from_text(text)
    return nums

def chunkify(nums: List[int], size: int) -> List[List[int]]:
    return [nums[i:i+size] for i in range(0, len(nums), size)]

def normalize_glyph_rows(glyph_rows: List[int], cols: int = 14, rows: int = 14) -> List[int]:
    """
    行ベースのデータ (長さ rows) -> 列ベースのデータ (長さ cols) に変換。
    入力: glyph_rows[r] は各行のビットパターン（横走査）。
    出力: cols 個の整数。各整数はその列の下->上ビット列（bit0 = 下端）。
    """
    # 行数が不足している場合は下側をゼロで埋める（上寄せ）
    rlist = list(glyph_rows)
    if len(rlist) < rows:
        rlist.extend([0] * (rows - len(rlist)))
    else:
        rlist = rlist[:rows]

    # 行ごとの有効幅（最も高いビット位置）を推定
    max_bitlen = 0
    for v in rlist:
        if v:
            max_bitlen = max(max_bitlen, v.bit_length())
    # 最低でも cols として扱う（古いデータでは16bitで左寄せされていることがある）
    effective_width = max(max_bitlen, cols)

    cols_out: List[int] = []
    # 左から右へ col_index が進む。左most は effective_width-1 に対応すると仮定
    for col_index in range(cols):
        col_val = 0
        # bit position in source row word (左most -> high bit)
        src_bitpos = effective_width - 1 - col_index
        for row_index in range(rows):
            row_word = rlist[row_index]
            # row_index: 0 = top, rows-1 = bottom
            bit = 0
            if src_bitpos >= 0:
                bit = (row_word >> src_bitpos) & 1
            # 出力は下->上を bit0..bit(rows-1) に詰めるので位置は (rows-1 - row_index)
            if bit:
                out_bitpos = (rows - 1 - row_index)
                col_val |= (1 << out_bitpos)
        cols_out.append(col_val)
    return cols_out

def normalize_glyph(glyph: List[int], cols: int = 14) -> List[int]:
    g = list(glyph)
    if len(g) >= cols:
        return g[:cols]
    g.extend([0] * (cols - len(g)))
    return g

def gather_input_files(pattern: str) -> List[Path]:
    p = Path(pattern)
    # ワイルドカードを含むか、ディレクトリパスか、単一ファイルかを判定
    if any(ch in pattern for ch in ['*', '?', '[']):
        files = [Path(x) for x in glob.glob(pattern, recursive=True)]
    elif p.is_dir():
        # ディレクトリなら拡張子 .cxx/.CXX を再帰的に収集
        files = list(p.rglob('*.cxx')) + list(p.rglob('*.CXX'))
    else:
        files = [p]
    # 存在するファイルに限定
    return [f for f in files if f.exists()]

def main():
    p = argparse.ArgumentParser(description='Generate ascii_glyphs.py from FeldFat C++/py data')
    p.add_argument('input', type=str, help='input file, glob pattern, or directory')
    p.add_argument('-o', '--output', type=str, default='ascii_glyphs.py', help='output filename (default: ascii_glyphs.py)')
    p.add_argument('--start', type=int, default=32, help='first codepoint to map (default 32 = space)')
    p.add_argument('--cols', type=int, default=14, help='columns per glyph (default 14)')
    args = p.parse_args()

    files = gather_input_files(args.input)
    if not files:
        print(f'入力ファイルが見つかりません: {args.input}')
        return

    nums: List[int] = []
    # Collect raw numeric stream across files (we will chunk into rows of 14)
    for f in files:
        if f.suffix.lower() == '.py':
            part = try_import_python_data(f)
        else:
            part = parse_cxx_file(f)
        if part:
            nums.extend(part)

    if not nums:
        print('数値データが抽出できませんでした。入力フォーマットを確認してください。')
        return

    # glyph 単位 (行ベース) に分割: 1 glyph = rows (default 14) 値（横走査行）
    rows_per_glyph = args.cols  # 入力が 14 行ずつ並んでいる想定
    glyph_rows_list = chunkify(nums, rows_per_glyph)
    # 最後が足りない場合は補完
    if glyph_rows_list and len(glyph_rows_list[-1]) < rows_per_glyph:
        glyph_rows_list[-1] = normalize_glyph(glyph_rows_list[-1], rows_per_glyph)

    # 出力辞書を作成（ASCII 連続にマップするのがデフォルト）
    out_lines = []
    out_lines.append('# -*- coding: utf-8 -*-')
    out_lines.append('"""ascii_glyphs.py — generated by tools/generate_ascii_glyphs.py"""')
    out_lines.append('')
    out_lines.append('GLYPHS = {')

    start = args.start
    for i, rows in enumerate(glyph_rows_list):
        code = start + i
        try:
            ch = chr(code)
        except Exception:
            ch = f'U+{code:04X}'
        key = repr(ch)
        # 行ベース -> 列ベースに変換（下->上ビット詰め）
        cols_vals = normalize_glyph_rows(rows, cols=args.cols, rows=args.cols)
        vals = ', '.join(f'0x{v:04X}' for v in cols_vals)
        out_lines.append(f'    {key}: [{vals}],')

    out_lines.append('}')
    out_text = '\n'.join(out_lines) + '\n'
    out_path = Path(args.output)
    out_path.write_text(out_text, encoding='utf-8')
    print(f'書き出しました: {out_path} (files={len(files)}, glyphs={len(glyph_rows_list)}, start={start})')

if __name__ == '__main__':
    main()