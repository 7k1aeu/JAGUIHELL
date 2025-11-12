JAGUIHELL
概要
JAGUIHELL　文字通信方式であるヘルシュライバーの送信ソフトウェアである。またいくつかの関連ソフトウェアを含んでいる。
特徴としては日本語(漢字およびかなとASCII)の送信が可能である。ヘルシュライバーは画像通信であり、フォーマットは＊＊に設定されているため任意のHELL受信ソフトウェアで受信が可能である。


はフォント／グリフデータを扱うユーティリティ群と関連ファイルを収めたリポジトリです。主に BDF フォントの変換、フォントデータの生成（Python / TypeScript 向け）、およびグリフデータの格納を目的としています。

インストール
リポジトリをクローン：
bash
git clone https://github.com/7k1aeu/JAGUIHELL.git
Python 仮想環境（任意）：
bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
依存パッケージをインストール：
bash
pip install -r requirements.txt
※ requirements.txt の内容を確認し、必要に応じて追加のパッケージ（例: Pillow 等）を導入してください。

使い方（基本例）
メインスクリプトを実行：

bash
python JAGUIHELL.py
各スクリプトは内部にヘルプやコメントを備えている場合があります。--help 等で使用方法を確認してください。

BDF フォントを変換する（例）：

bash
python BDFconv.py k8x12.bdf
上記は BDF ファイルをリポジトリ内で利用可能な形式に変換する想定の例です。実際の引数や出力はスクリプト内の説明を参照してください。

TypeScript 用データへの変換（補助スクリプト）：

bash
python convert_to_ts.py
ファイル一覧（主なファイル）
JAGUIHELL.py — メインまたはユーティリティ群の統括スクリプト。
BDFconv.py — BDF フォント（.bdf）をJAGUIHELL.pyで使用するグリフ辞書(glyphs.py)に変換するスクリプト。
glyphs.py — 日本語フォントを持つグリフデータ（Python 形式）。
glyphs.ts — TypeScript 形式のグリフデータ。
k8x12.bdf — BDF 形式フォントファイル。
convert_to_ts.py — Python から TypeScript へ変換する補助スクリプト。
JAHELLTX.ico, 無料の設定歯車アイコン.png — アイコン／画像ファイル。
requirements.txt — 依存パッケージ一覧。
LICENSE.txt — ライセンス文書。
.gitignore, .gitattributes — リポジトリ管理用設定ファイル。
注意事項
glyphs.py, glyphs.ts, k8x12.bdf はサイズが大きいファイルです。編集や再生成時は処理時間とメモリに注意してください。
各スクリプトの具体的な引数や出力形式は、スクリプト内の冒頭コメントや --help で確認してください。README に記載のない詳細はソースを参照してください。
開発者向けメモ
新しいフォントを追加する手順（想定）:
.bdf ファイルを追加
BDFconv.py などで変換し、feld_hell_fontx2_font_data.py や glyphs.py に統合
必要に応じて convert_to_ts.py を実行して glyphs.ts を更新
貢献方法
バグ報告や機能要望は GitHub の Issues へ記載してください。
変更提案は Fork → ブランチ作成 → Pull Request の流れでお願いします。PR には変更点と動作確認方法を明記してください。
ライセンス
LICENSE.txt を参照してください。本リポジトリのソースは該当のライセンスに従って使用・配布してください。
ご希望のブランチ名があればご指示ください。もしくはこの内容を取得してご自身でREADME.mdに貼り付けてご利用いただけます。
