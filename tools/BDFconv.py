# -*- coding: utf-8 -*-
"""
BDFconv.py — BDF → ヘルシュライバー用グリフ変換ツール

使用例:
  1) スクリプトをインポートして使う（推奨、ファイル名を指定可）
     from tools.BDFconv import convert_bdf_to_hell, save_hell_glyphs
     glyphs = convert_bdf_to_hell('k12-2000-1.bdf')
     save_hell_glyphs(glyphs, 'glyphs.py')

  2) コマンドラインからグリフを表示する（対話モード）
     python tools/BDFconv.py --show -o glyphs.py
     （表示行数を指定: python tools/BDFconv.py --show -o glyphs.py --rows 14）

  3) 変換モード（入力/出力はオプションで指定可）
     python BDFconv.py -i k12-2000-1.bdf -o glyphs.py
     デフォルト: 入力 'k12-2000-1.bdf', 出力 'glyphs.py'
"""
from pathlib import Path
import sys
from typing import Dict, List, Optional
import argparse

def parse_bdf_glyph(lines, start_index):
    """BDFファイルの1文字分のビットマップデータを解析"""
    bitmap = []
    encoding = None
    i = start_index

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('ENCODING'):
            try:
                encoding = int(line.split()[1])
            except Exception:
                encoding = None
        elif line.startswith('BITMAP'):
            # ビットマップデータの開始
            i += 1
            # 12行分のビットマップデータを読み込む
            for _ in range(12):
                if i >= len(lines) or lines[i].startswith('ENDCHAR'):
                    break
                # 16進数文字列を2進数ビットパターンに変換
                hex_str = lines[i].strip()
                if hex_str:  # 空行チェックを追加
                    try:
                        bin_str = bin(int(hex_str, 16))[2:].zfill(8)
                        bitmap.append([1 if bit == '1' else 0 for bit in bin_str])
                    except ValueError:
                        print(f"警告: 無効な16進数データ: {hex_str}")
                        bitmap.append([0] * 8)  # エラー時は空行を追加
                i += 1
            break
        i += 1

    # ビットマップが12行になるように調整
    while len(bitmap) < 12:
        bitmap.append([0] * 8)

    return encoding, bitmap, i

def convert_to_hell_format(bitmap):
    """8×12ビットマップをヘルシュライバー形式（14×8）に変換"""
    hell_columns = [0] * 8  # 8列に変更

    # 各列について処理
    for x in range(8):  # 8列すべてを処理
        column_bits = 0
        # 12ビットを14ビットの中央に配置（上下1ビットずつマージン）
        for y in range(12):  # 12行分のデータ
            # ビットマップは上から下なので、下から上へと配置するように順序を反転
            if bitmap[11 - y][x]:  # インデックスを反転
                column_bits |= (1 << (y + 1))  # 1ビット目をマージンとして空ける
        hell_columns[x] = column_bits

    return hell_columns

def _decode_jis_encoding_to_char(encoding):
    """
    JIS 形式の数値エンコーディング（例: 0x2121）を Unicode 文字に変換する。
    試行順序:
      1) 0..0xFF は chr()
      2) JIS (2バイト) として EUC-JP に変換して decode('euc_jp')
      3) Shift_JIS として decode('shift_jis')
      4) 最終フォールバックで chr(encoding)
    成功時は文字列（通常長さ1）を返す。失敗時は None を返す。
    """
    if encoding is None:
        return None
    try:
        # 1バイト領域はそのまま
        if 0 <= encoding <= 0xFF:
            return chr(encoding)
    except Exception:
        pass

    hi = (encoding >> 8) & 0xFF
    lo = encoding & 0xFF

    # 2バイト JIS -> EUC-JP: 各バイトに 0x80 を加える（JIS 0x21..0x7E -> EUC 0xA1..0xFE）
    try:
        euc_bytes = bytes([(hi | 0x80) & 0xFF, (lo | 0x80) & 0xFF])
        s = euc_bytes.decode('euc_jp')
        if s:
            return s
    except Exception:
        pass

    # Shift_JIS として解釈してみる（BDF が shift_jis ベースであるケースに対応）
    try:
        sjis_bytes = bytes([hi, lo])
        s2 = sjis_bytes.decode('shift_jis')
        if s2:
            return s2
    except Exception:
        pass

    # 最終フォールバック: 値を Unicode codepoint として扱う
    try:
        if 0 <= encoding <= 0x10FFFF:
            return chr(encoding)
    except Exception:
        pass

    return None

def parse_bdf(path: Path) -> Dict[int, List[str]]:
    """BDF を読み、各グリフの ENCODING -> bitmap hex lines を返す"""
    glyphs = {}
    current_encoding: Optional[int] = None
    bitmap_lines: List[str] = []
    in_bitmap = False
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if line.startswith("STARTCHAR"):
                current_encoding = None
                bitmap_lines = []
                in_bitmap = False
            elif line.startswith("ENCODING"):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        current_encoding = int(parts[1])
                    except Exception:
                        current_encoding = None
            elif line == "BITMAP":
                in_bitmap = True
            elif line == "ENDCHAR":
                if current_encoding is not None and bitmap_lines:
                    if current_encoding >= 0:
                        glyphs[current_encoding] = bitmap_lines.copy()
                current_encoding = None
                bitmap_lines = []
                in_bitmap = False
            else:
                if in_bitmap:
                    s = line.strip()
                    if s and all(c in "0123456789ABCDEFabcdef" for c in s):
                        bitmap_lines.append(s)
    return glyphs

def hexrow_to_bits(hexstr: str, width: int) -> List[int]:
    """hex string -> bits list (MSB first) with given width"""
    try:
        val = int(hexstr, 16)
    except Exception:
        val = 0
    bits: List[int] = []
    for i in range(width):
        shift = (width - 1 - i)
        bits.append((val >> shift) & 1)
    return bits

def infer_bdf_width_from_hex(hexstr: str) -> int:
    """hex 表記から幅を推測（hex桁 * 4）。BDF の行は通常行ごとに同じ幅."""
    return len(hexstr) * 4

def build_14x14_from_12x12(bitmap_lines: List[str], expected_w: int = 12, expected_h: int = 12) -> List[int]:
    """
    12x12 (または BDF 行から推測したサイズ) の bitmap hex lines から
    14x14 の列リスト（各列は下位ビットが上行）を生成する。
    bit 0 = top row (Y=0)、bit 13 = bottom row (Y=13)
    """
    rows = 14
    cols = 14
    # マトリクス初期化
    mat = [[0 for _ in range(cols)] for _ in range(rows)]
    # 12x12 を (1,1) に置く
    row_offset = 1
    col_offset = 1

    # BDF の各行の幅を推測（最初の行を使う）
    bdf_width = expected_w
    if bitmap_lines:
        try:
            bdf_width = infer_bdf_width_from_hex(bitmap_lines[0])
        except Exception:
            bdf_width = expected_w

    # BDF 行数が expected_h でない場合も、上寄せで配置する（行 0 -> row_offset）
    for r_idx, hexrow in enumerate(bitmap_lines[:expected_h]):
        bits = hexrow_to_bits(hexrow, bdf_width)
        # BDF のビット列は左が MSB -> canvas の左から配置
        for c_idx in range(min(bdf_width, expected_w)):
            # 列が 12 を超える場合は切り捨て
            mat[row_offset + r_idx][col_offset + c_idx] = bits[c_idx]

    # ここで垂直方向の向きを修正する。グリフではフォントの下が上になるため
    # mat を上下反転してからビットパックすることで表示の上下逆転を解消する。
    mat = list(reversed(mat))

    # 列ごとに整数化（bit 0 = top）
    cols_ints: List[int] = []
    for c in range(cols):
        v = 0
        for y in range(rows):
            if mat[y][c]:
                v |= (1 << y)
        cols_ints.append(v)
    return cols_ints

def _is_japanese_char(s: Optional[str]) -> bool:
    """文字列に日本語（ひらがな・カタカナ・CJK統合漢字など）が含まれるか簡易判定"""
    if not s:
        return False
    for ch in s:
        o = ord(ch)
        if (0x3040 <= o <= 0x30FF) or (0x4E00 <= o <= 0x9FFF) or (0xFF65 <= o <= 0xFF9F) or (0x3000 <= o <= 0x303F):
            return True
    return False

def convert_bdf_to_hell(bdf_file):
    """BDFファイルをヘルシュライバーグリフ辞書に変換"""
    bdf_path = Path(bdf_file)
    bdf_glyphs = parse_bdf(bdf_path)
    out_map = {}
    for code, rows in bdf_glyphs.items():
        cols = build_14x14_from_12x12(rows, expected_w=12, expected_h=12)
        out_map[code] = cols

    # encoding -> Unicode 変換: JIS形式のエンコーディングを想定するBDFもあるため
    # 既存の _decode_jis_encoding_to_char を活用し、判定が怪しいときは chr() にフォールバックする
    final_map = {}
    for code, cols in out_map.items():
        if code is None:
            continue
        ch = None
        try:
            if code <= 0xFF:
                ch = chr(code)
            else:
                # まず JIS/SHIFT_JIS 等を試す
                try:
                    dec = _decode_jis_encoding_to_char(code)
                except Exception:
                    dec = None
                # dec が有効な単一文字なら採用
                if dec and isinstance(dec, str) and len(dec) >= 1:
                    # 複数文字になってしまった場合は先頭文字を考慮する（必要なら振り分けロジックを拡張）
                    ch = dec[0]
                else:
                    # フォールバック: code を Unicode コードポイントとして解釈
                    try:
                        ch = chr(code)
                    except Exception:
                        ch = None
        except Exception:
            ch = None

        if ch is not None:
            final_map[ch] = cols
        else:
            # 最終手段として、キーに U+XXXX 形式の文字列を使って保存（ファイル化やデバッグ用）
            final_map[f"U+{code:04X}"] = cols
    return final_map

def save_hell_glyphs(glyphs, output_file):
    """グリフデータをPythonファイルとして保存"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('# ヘルシュライバー用グリフデータ\n')
        f.write('GLYPHS = {\n')
        for char, data in sorted(glyphs.items()):
            # repr を使って適切にエスケープ（char が Unicode であれば UTF-8 で正しく保存される）
            char_repr = repr(char)
            f.write(f'    {char_repr}: {data},\n')
        f.write('}\n')

def print_glyph_bitmap(glyph_data, rows: int = 14):
    """ヘルシュライバーグリフデータをビットマップとして表示（任意列数 × 指定行数）"""
    # glyph_data は列リスト（各列が整数ビットマップ）と想定
    if not isinstance(glyph_data, (list, tuple)) or len(glyph_data) == 0:
        print("グリフデータが不正です")
        return

    cols = len(glyph_data)

    # カラムインデックス表示（上段：10の位、下段：1の位）— 幅が大きくても見やすく
    tens = []
    units = []
    for idx in range(cols):
        tens.append(str((idx // 10) % 10) if cols > 10 else ' ')
        units.append(str(idx % 10))
    print("   " + ''.join(tens))
    print("   " + ''.join(units))
    # ビットマップ行を表示（行0を上に）
    for y in range(rows):
        row = []
        for x in range(cols):
            bit = (glyph_data[x] >> y) & 1
            row.append('■' if bit else '□')
        print(f"{y:2d} " + ''.join(row))

def load_and_show_glyphs(glyph_file, rows: int = 14):
    """グリフファイルを読み込んで表示（行数を指定可能）"""
    try:
        # グリフファイルをインポート
        import importlib.util
        spec = importlib.util.spec_from_file_location("glyphs", glyph_file)
        glyphs_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(glyphs_module)

        while True:
            char = input("表示する文字を入力（終了は空行）: ")
            if not char:
                break
            if char in glyphs_module.GLYPHS:
                print(f"\n文字 '{char}' のビットマップ:")
                print_glyph_bitmap(glyphs_module.GLYPHS[char], rows=rows)
            else:
                # 見つからない場合は候補の一部を表示してデバッグしやすくする
                print(f"文字 '{char}' は定義されていません")
                print("定義済みの先頭キーの例:", list(glyphs_module.GLYPHS.keys())[:20])
    except Exception as e:
        print(f"エラー: グリフファイルの読み込みに失敗しました: {e}")

def main(argv: Optional[List[str]] = None) -> None:
    """コマンドラインインターフェイス:
       -i/--input 入力BDFファイル（デフォルト k12-2000-1.bdf）
       -o/--output 出力glyphs.py（デフォルト glyphs.py）
       --show 表示モード（生成済み glyphs.py を表示）、表示時は -o を指定して読み込む
       --rows 表示行数（デフォルト 14）
    """
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description="BDF -> Hell glyphs converter")
    parser.add_argument('-i', '--input', default='k12-2000-1.bdf', help='入力 BDF ファイルパス (default: k12-2000-1.bdf)')
    parser.add_argument('-o', '--output', default='glyphs.py', help='出力 Python ファイルパス (default: glyphs.py)')
    parser.add_argument('--show', action='store_true', help='表示モード: 出力ファイルを読み込み対話表示する')
    parser.add_argument('--rows', type=int, default=14, help='表示モードの行数 (default: 14)')
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_path = Path(args.output)

    if args.show:
        # 表示モード: 出力ファイル（glyphs.py）を読み込んで表示
        if not output_path.exists():
            print(f"表示するグリフファイルが見つかりません: {output_path}", file=sys.stderr)
            sys.exit(1)
        load_and_show_glyphs(str(output_path), rows=args.rows)
        return

    # 変換モード
    if not input_path.exists():
        print(f"入力 BDF が見つかりません: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        glyphs = convert_bdf_to_hell(str(input_path))
        if not glyphs:
            print("変換結果が空です。", file=sys.stderr)
            sys.exit(2)
        save_hell_glyphs(glyphs, str(output_path))
        print(f"Wrote {output_path} ({len(glyphs)} glyphs)")
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(3)

if __name__ == '__main__':
    main()