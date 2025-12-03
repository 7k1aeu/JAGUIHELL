# JAGUIHELL

## 概要
`JAGUIHELL` はヘルシュライバー方式の文字送信ソフトウェアです。  
日本語（漢字・かな）および ASCII の送信に対応しています。  
送信フォーマットは汎用的な HELL 受信ソフトで受信可能な形式です。

## 特徴
- 日本語（漢字・かな）と ASCII の送信対応
- グリフベースの文字変換（フォント変換スクリプト付き）
- PTT（RTS/DTR）制御対応
- 単体実行可能な Windows 実行ファイルを提供（Python 環境を含む）

## インストール

### Windows （配布実行ファイル）
-[`JAGUIHELL.exe`](https://github.com/7k1aeu/JAGUIHELL/releases/latest/download/JAGUIHELL.exe)  をダウンロードして実行してください（Python を含むためファイルサイズが大きくなります）。

### ソースから実行（その他の環境）
1. リポジトリをクローン:
bash
git clone https://github.com/7k1aeu/JAGUIHELL.git
2. Python 仮想環境（任意）:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```
3. 依存パッケージをインストール:
    ```bash
    pip install -r requirements.txt
    ```
    ※ `requirements.txt` の内容を確認し、必要に応じて追加のパッケージ（例: Pillow 等）を導入してください。

### 使い方
メインスクリプトを実行：
```bash
python JAGUIHELL.py
```
## 使用方法
上のWindowに送信する文字データを打ち込んで、真ん中の送信を押すとサウンドカードから音声出力が出ます。
送信電文の前後にドット3個　半角スペース　本文　半角スペース　ドット3個がつきます
送信されるに合わせて順序文字に色が赤色に変わっていきます

歯車マークを押すと設定画面に入れます。
出力するサウンドカードの選択及びレベルに調整、0dBで出力するとひずみますので-20dB程度に設定してください
PTTを出力するComポート番号に設定が可能です。PTT出力はRTS出力、DTR出力いずれかが選べます。



## 主要ファイル
- `JAGUIHELL.py` — メインスクリプト
- `glyphs.py` — 日本語グリフデータ（Python）
- `ascii_glyphs.py` — ASCII グリフデータ（生成済み）
- `requirements.txt` — 依存パッケージ一覧
- `LICENSE.txt` — ライセンス文書
- `JAHELLTX.ico`, `歯車アイコン.png` — アイコン／画像ファイル
- `JAGUIHELL.wav` — サンプル（1000Hz キャリアで変調）

### tools ディレクトリ（主なツール）
- `BDFconv.py` — BDF フォント（`.bdf`）を `glyphs.py` 形式に変換（グリフ確認機能あり）
- `generate_ascii_glyphs.py` — FLdigi の CXX フォント（*.CXX）から ASCII グリフを生成
- `FeldFat-14.cxx` — FLdigi 用の ASCII フォント（GPL）  
  (https://sourceforge.net/p/fldigi/fldigi/ci/master/tree/src/feld/)
- `k12-2000-1.bdf` — 日本語フォント（パブリックドメイン）  
  (http://jikasei.me/font/jf-dotfont/)

## 注意事項
- `glyphs.py` は大きなファイルです。編集・再生成時は処理時間とメモリに注意してください。  
- 実行環境の Python と依存パッケージは一致させてください（仮想環境推奨）。  
- PTT を利用する場合は `pyserial` が必要です。  
- 受信機能は組み込まれていません。受信には FLdigi、MixW などを利用してください。

参考:
- [FLdigi](https://sourceforge.net/projects/fldigi/)
- [MixW](https://mixw.net/)

※ 英語版ソフトではオーディオデバイス名が ASCII 表示できないと問題を起こす場合があります。Windows のデバイス名は必要に応じて変更してください（例: 「SP」など）。  
[Windows 11: Rename speaker/microphone](https://pc-karuma.net/how-to-rename-speaker-windows-11/)

## 変更履歴 (Changelog)
- **Version 1.0.0** — 2025/11/15 — Initial release

- **Version 1.0.1** — 2025/12/03 — Updates
  - Default audio output level changed from 0 dBFS to -20 dBFS.
  - UI font changed to improve readability.
  - ASCII glyphs replaced with a font generated from FLdigi project CXX files.
  - Japanese glyph source switched from `k8x12.bdf` to `k12-2000-1.bdf`, providing full-width character coverage.
  - README updated.
  - Font conversion tooling revised (see `tools/`).

---

# English Translation (summary)

`JAGUIHELL` is a Hellschreiber sender supporting Japanese (kanji/kana) and ASCII.  
Run `python JAGUIHELL.py` to start the GUI. Tools for converting BDF and FLdigi CXX fonts are provided in the `tools/` directory.

For full details, refer to the Japanese section above.
