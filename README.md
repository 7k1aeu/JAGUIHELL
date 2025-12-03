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

BDF フォントを変換する（例）：
```bash
python BDFconv.py k8x12.bdf
```
上記は BDF ファイルをリポジトリ内で利用可能な形式に変換する想定の例です。実際の引数や出力はスクリプト内の説明を参照してください。

## ファイル一覧（主要）
- `JAGUIHELL.py` — メインスクリプト
- `BDFconv.py` — BDF フォント（`.bdf`）を `glyphs.py` 形式に変換するツール
- `glyphs.py` — 日本語グリフデータ（Python）
- `k8x12.bdf` — BDF 形式フォントファイル（変換用）
- `requirements.txt` — 依存パッケージ一覧
- `LICENSE.txt` — ライセンス文書
- `JAHELLTX.ico`, `無料の設定歯車アイコン.png` — アイコン／画像ファイル
- `JAGUIHELL.wav` -変調された音声のサンプル（漢字を含む）　キャリア周波数1000Hzで変調されています。

## 注意事項
- `glyphs.py`  はファイルサイズが大きいです。編集・再生成時は処理時間とメモリに注意してください。
- 実行環境の Python と依存パッケージは一致させてください（仮想環境推奨）。
- PTT（シリアル制御）を利用する場合、`pyserial` が必要です。実行中の Python で以下を実行してインストールしてください:

- 受信機能は組み込んでいないので、他ソフトを使用してください、有名どころではFLdigiやMixWなどがります。
  * [FLdigi] (https://sourceforge.net/projects/fldigi/)
  * [MixW] (https://mixw.net/)
- 英語で開発されているソフトでは音声入出力の名称（日本語Windowsでは標準で「スピーカー」や「マイク」になる）がASCIIで表示できないと動作できなくなることがあります。
FLdigi、VARAモデムなどでも動作に支障が出ますので、使用の際は音声州出力の名前をASCIIで表示できるもの（SPとか）に変更してください。
[Win11での音声入出力の名称変更の方法](https://pc-karuma.net/how-to-rename-speaker-windows-11/)

変更履歴
Version 1.0.0  2025/11/15 初版公開
Version 1.0.1  　2025/12/3 修正
- 音声出力のデフォルト値を0dBFS→-20dBFSに変更
- 視認性向上のためフォントの変更　ASCII文字列についてはFldigiプロジェクトで作成されたCXXファイルから生成されたフォントに変更　日本語についてはk8x12.bdfからk12-2000-1.bdfに変更しま全角相当になりました。
- READMEの修正
- フォントを変換するためのツールの変更（Toolフォルダ内）

---

# English Translation

## Overview
`JAGUIHELL` is a software for character transmission using the Hellschreiber method.  
It supports sending Japanese (kanji, kana) as well as ASCII characters.  
Transmission format is compatible with general-purpose HELL receiving software.

## Features
- Supports sending Japanese (kanji, kana) and ASCII
- Glyph-based character conversion (font conversion script included)
- Supports PTT (RTS/DTR) control
- Standalone Windows executable provided (includes Python environment)

## Installation

### Windows (Distributed Executable)
- Download and run [`JAGUIHELL.exe`](https://github.com/7k1aeu/JAGUIHELL/releases/latest/download/JAGUIHELL.exe). (File size is large because it includes Python.)

### Running from Source (Other Environments)
1. Clone the repository:
bash
git clone https://github.com/7k1aeu/JAGUIHELL.git
2. Python virtual environment (optional):
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```
3. Install required packages:
    ```bash
    pip install -r requirements.txt
    ```
    *Check the contents of `requirements.txt` and install additional packages as necessary (e.g., Pillow).*

### Usage
Run the main script:
```bash
python JAGUIHELL.py
```
## How to Use
Type characters to be sent into the upper window, and press "Send" in the middle to output audio via the sound card.  
Three dots, a space, the main text, a space, and three dots will be added before and after the message.  
As the transmission progresses, the corresponding characters change to red.

Click the gear icon to access the settings.  
You can select and adjust the output sound card and level. Do not output at 0dB as it will cause distortion; set to around -20dB.  
The COM port number for PTT output can be set. You can choose either RTS or DTR for PTT output.

To convert BDF fonts (example):
```bash
python BDFconv.py k8x12.bdf
```
The above is an example for converting a BDF file into a format usable in the repository. Please refer to instructions in the script for actual arguments and outputs.

## Main Files
- `JAGUIHELL.py` — Main script
- `BDFconv.py` — Tool to convert BDF font (`.bdf`) to `glyphs.py` format
- `glyphs.py` — Japanese glyph data (Python)
- `k8x12.bdf` — BDF font file (for conversion)
- `requirements.txt` — List of required packages
- `LICENSE.txt` — License documentation
- `JAHELLTX.ico`, `無料の設定歯車アイコン.png` — Icon/image files
- `JAGUIHELL.wav` — Sample of modulated audio (includes kanji), modulated at a 1000Hz carrier frequency

## Notes
- `glyphs.py` and `k8x12.bdf` are large files. Please be mindful of processing time and memory when editing or regenerating.
- Ensure the Python environment and required packages are matched (virtual environment recommended).
- If using PTT (serial control), `pyserial` is required. Install it with the following command in your current Python environment:
- `k8x12.bdf` is taken from here: <https://littlelimit.net/k8x12.htm>. License is free: <https://littlelimit.net/font.htm#license>

- Reception functionality is not built-in. Use other software for reception. Well-known examples include FLdigi and MixW:
  * [FLdigi](https://sourceforge.net/projects/fldigi/)
  * [MixW](https://mixw.net/)
- For software developed in English, if the name of the audio input/output (typically "Speaker" or "Microphone" on Japanese Windows) cannot be displayed in ASCII, it may not work.  
  Even in FLdigi or VARA modem, such issues may occur. When using, change the name of the audio input/output device to something that can be displayed in ASCII (like "SP").
[How to change the name of speakers/microphones on Windows 11](https://pc-karuma.net/how-to-rename-speaker-windows-11/)
