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
送信電文の前後にドット3個　反核スペース　本文　半角スペース　ドット3個がつきます
送信されるに合わせて順序文字に色が赤色に変わっていきます

歯車マークを押すと設定画面に入れます。
出力するサウンドカードの選択及びレベルに調整、０dBで出力するとひずみますので―20dB程度に設定してください
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

## 注意事項
- `glyphs.py` や `k8x12.bdf` はファイルサイズが大きいです。編集・再生成時は処理時間とメモリに注意してください。
- 実行環境の Python と依存パッケージは一致させてください（仮想環境推奨）。
- PTT（シリアル制御）を利用する場合、`pyserial` が必要です。実行中の Python で以下を実行してインストールしてください:
- `k8x12.bdf`  はここから使用しています <https://littlelimit.net/k8x12.htm> ライセンス条件に付いてはフリーライセンスです <https://littlelimit.net/font.htm#license>
