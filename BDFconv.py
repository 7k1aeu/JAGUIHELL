def parse_bdf_glyph(lines, start_index):
    """BDFファイルの1文字分のビットマップデータを解析"""
    bitmap = []
    encoding = None
    i = start_index
    
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('ENCODING'):
            encoding = int(line.split()[1])
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
            # ビットマップは上から下なので、
            # 下から上へと配置するように順序を反転
            if bitmap[11-y][x]:  # インデックスを反転
                column_bits |= (1 << (y + 1))  # 1ビット目をマージンとして空ける
        hell_columns[x] = column_bits
    
    return hell_columns

def convert_bdf_to_hell(bdf_file):
    """BDFファイルをヘルシュライバーグリフ辞書に変換"""
    hell_glyphs = {}
    
    with open(bdf_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('STARTCHAR'):
            encoding, bitmap, next_i = parse_bdf_glyph(lines, i)
            if encoding and bitmap:
                # Unicode文字に変換
                try:
                    char = chr(encoding)
                    hell_glyphs[char] = convert_to_hell_format(bitmap)
                except ValueError:
                    print(f"警告: 無効なエンコーディング {encoding}")
            i = next_i
        i += 1
    
    return hell_glyphs

def save_hell_glyphs(glyphs, output_file):
    """グリフデータをPythonファイルとして保存"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('# ヘルシュライバー用グリフデータ\n')
        f.write('GLYPHS = {\n')
        for char, data in sorted(glyphs.items()):
            # エスケープが必要な文字を処理
            if ord(char) < 128:
                char_repr = repr(char)
            else:
                char_repr = f"'{char}'"
            f.write(f'    {char_repr}: {data},\n')
        f.write('}\n')

def print_glyph_bitmap(glyph_data):
    """ヘルシュライバーグリフデータをビットマップとして表示"""
    print("  01234567")  # 8列に変更
    for y in range(14):  # 14行
        row = []
        for x in range(8):  # 8列
            bit = (glyph_data[x] >> y) & 1
            row.append('■' if bit else '□')
        print(f"{y:2d} {''.join(row)}")

def load_and_show_glyphs(glyph_file):
    """グリフファイルを読み込んで表示"""
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
                print_glyph_bitmap(glyphs_module.GLYPHS[char])
            else:
                print(f"文字 '{char}' は定義されていません")
    
    except Exception as e:
        print(f"エラー: グリフファイルの読み込みに失敗しました: {e}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--show':
        # グリフ表示モード
        load_and_show_glyphs('glyphs.py')
    else:
        # 通常の変換モード
        try:
            glyphs = convert_bdf_to_hell('k8x12.bdf')
            save_hell_glyphs(glyphs, 'glyphs.py')
            print(f"変換完了: {len(glyphs)} 文字のグリフを生成")
        except Exception as e:
            print(f"エラー: {e}")