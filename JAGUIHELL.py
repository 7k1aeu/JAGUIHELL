#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import threading
import time
from typing import Dict, Any, List, Tuple, Optional
import sounddevice as sd
import numpy as np
import os
import configparser
from pathlib import Path
import serial
import serial.tools.list_ports
from glyphs import GLYPHS

# 設定ファイルのパス
CONFIG_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / 'JAGUIHELL.ini'

# PTT制御クラス
class PTTControl:
    def __init__(self) -> None:
        self.serial_port = None
        self.port_name = None
        self.use_rts = False
        self.use_dtr = False
        
    def open(self, port_name: str) -> None:
        if self.serial_port:
            self.close()
        
        self.port_name = port_name
        try:
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=9600,
                timeout=1,
                write_timeout=1,
                exclusive=True
            )
            
            if not self.serial_port.is_open:
                self.serial_port.open()
            
            self.update_lines()
            
        except serial.SerialException as e:
            raise Exception(f"シリアルポート {port_name} のオープンに失敗しました: {str(e)}")
        except Exception as e:
            raise

    def close(self) -> None:
        if self.serial_port:
            try:
                if self.serial_port.is_open:
                    self.serial_port.close()
            except Exception:
                pass
            finally:
                self.serial_port = None
                self.port_name = None
        
    def update_lines(self) -> None:
        if not self.serial_port or not self.serial_port.is_open:
            return
            
        try:
            if self.use_rts:
                self.serial_port.rts = False  # False = High = PTT OFF
            else:
                self.serial_port.rts = False
                
            time.sleep(0.1)  # 制御線の安定化のため
            if self.use_dtr:
                self.serial_port.dtr = False  # False = Low = PTT OFF
            else:
                self.serial_port.dtr = False
                
        except Exception as e:
            raise

    def set_ptt(self, state: bool) -> None:
        if self.serial_port:
            if self.use_rts:
                self.serial_port.rts = state  # True = Low = PTT ON, False = High = PTT OFF
            if self.use_dtr:
                self.serial_port.dtr = state  # False = Low = PTT OFF, True = High = PTT ON

# ---- サウンド設定 ----
FREQ = 1000        # トーン周波数（Hz）
SAMPLE_RATE = 48000 # サンプルレート（Hz）
PIXELS_PER_COLUMN = 14  # 1列あたりのピクセル数（14行）
COLUMNS_PER_CHAR = 14   # 1文字あたりの列数を固定で14にする（ASCIIも日本語も14列）
# 1ピクセルあたりの正確なサンプル数を計算（整数に丸める）
SAMPLES_PER_PIXEL = int(SAMPLE_RATE * 0.004045)  # 約4.045ミリ秒
# 1文字分の合計サンプル数（固定14列で計算）
SAMPLES_PER_CHAR = SAMPLES_PER_PIXEL * PIXELS_PER_COLUMN * COLUMNS_PER_CHAR
# 音声出力の設定
BUFFER_SAMPLES = SAMPLES_PER_CHAR * 2  # バッファサイズを文字サイズの倍数に
LATENCY = 0.2  # 出力レイテンシー（秒）

class DeviceInfo:
    """サウンドデバイス情報を保持するクラス"""
    def __init__(self, device_dict: Dict[str, Any]) -> None:
        self.name: str = str(device_dict.get('name', ''))
        self.max_output_channels: int = int(device_dict.get('max_output_channels', 0))


def generate_tone(on: bool) -> np.ndarray:
    """1ピクセル分の波形を生成（サンプル数を正確に保つ）"""
    if on:
        t = np.linspace(0, SAMPLES_PER_PIXEL / SAMPLE_RATE, SAMPLES_PER_PIXEL, False)
        wave = 0.5 * np.sin(2 * np.pi * FREQ * t)
    else:
        wave = np.zeros(SAMPLES_PER_PIXEL)
    return wave.astype(np.float32)

def generate_silence(duration: float) -> np.ndarray:
    """無音区間を生成"""
    samples = int(SAMPLE_RATE * duration)
    return np.zeros(samples, dtype=np.float32)

def load_glyphs() -> Dict[str, List[int]]:
    try:
        from glyphs import GLYPHS
        # GLYPHS は BDF 変換ツールで 14 列化されている前提
        # 万が一列数が12なら右側に 0 を追加して 14 にする
        def _norm(g):
            if not isinstance(g, (list,tuple)):
                return [0]*14
            lst = list(g)
            if len(lst) >= 14:
                return lst[:14]
            lst.extend([0]*(14 - len(lst)))
            return lst
        return {k: _norm(v) for k,v in GLYPHS.items()}
    except ImportError:
        print("警告: グリフファイル (glyphs.py) が見つかりません。")
        print("日本語グリフは利用できません。")
        return {}

GLYPHS = load_glyphs()

def _ensure_14_columns(glyph_data: List[int]) -> List[int]:
    """受け取ったグリフ列リストを必ず長さ14にする（不足は右パディング、超過は切り詰め）"""
    if not isinstance(glyph_data, (list, tuple)):
        return [0] * 14
    cols = list(glyph_data)
    if len(cols) >= 14:
        return cols[:14]
    cols.extend([0] * (14 - len(cols)))
    return cols

# ASCII文字のグリフデータ（デフォルトは空白中心の14列）
# NOTE: 実行時に生成済みの `ascii_glyphs.py` があればそれを優先して読み込みます
ASCII_GLYPHS = {
    ' ': [0x0000] * 14,
}

# generated ascii_glyphs.py を優先して読み込み、なければ最小フォールバックを用意
try:
    from ascii_glyphs import GLYPHS as ASCII_SOURCE
    def _normalize_to_14(cols: List[int]) -> List[int]:
        if not isinstance(cols, (list, tuple)):
            return [0] * 14
        lst = list(cols)
        if len(lst) >= 14:
            return lst[:14]
        lst.extend([0] * (14 - len(lst)))
        return lst
    ASCII_GLYPHS = {k: _normalize_to_14(v) for k, v in ASCII_SOURCE.items()}
    _ASCII_AVAILABLE = True
except Exception as _ascii_ex:
    # ascii_glyphs.py が見つからない場合は空白のみ定義した安全なフォールバックを使用
    ASCII_GLYPHS = {' ': [0x0000] * 14}
    _ASCII_AVAILABLE = False
    _ASCII_IMPORT_ERROR = _ascii_ex


def _rows_to_cols(rows_list: List[int], cols: int = 14, rows: int = 14) -> List[int]:
    """
    行ベースのビットパターン (rows_list: 各要素が1行のビットパターン) を
    列ベース (cols 個の整数、各整数は下→上にビットが詰められる) に変換する。
    - rows_list[0] は上行、rows_list[rows-1] は下行と仮定する。
    - 入力行のビットは左が MSB と仮定する（CXX の出力に合わせる）。
    """
    rlist = list(rows_list)
    if len(rlist) < rows:
        rlist.extend([0] * (rows - len(rlist)))
    else:
        rlist = rlist[:rows]

    max_bitlen = 0
    for v in rlist:
        if v:
            max_bitlen = max(max_bitlen, v.bit_length())
    effective_width = max(max_bitlen, cols)

    cols_out: List[int] = []
    for col_index in range(cols):
        col_val = 0
        src_bitpos = effective_width - 1 - col_index
        for row_index in range(rows):
            row_word = rlist[row_index]
            bit = (row_word >> src_bitpos) & 1 if src_bitpos >= 0 else 0
            if bit:
                out_bitpos = (rows - 1 - row_index)  # 下->上に詰める
                col_val |= (1 << out_bitpos)
        cols_out.append(col_val)
    return cols_out

def _count_nonzero(items: List[int]) -> int:
    return sum(1 for v in items if v != 0)

def send_char(ch: str) -> np.ndarray:
    """1文字分の波形を生成（14x14固定の仕様に合わせる）
    - ASCII は `ASCII_GLYPHS` を最優先で使用（大文字/小文字を順に試す）。
    - 見つからなければ `GLYPHS` を参照する（日本語など）。
    - グリフは与えられたまま信じて変換は行わない（行→列自動変換は行わない）。
    """
    try:
        glyph_data = None

        # ASCII 優先（大文字→小文字→そのままの順）
        if ord(ch) <= 0x7F:
            candidates = [ch, ch.upper(), ch.lower()]
            for c in candidates:
                if c in ASCII_GLYPHS:
                    glyph_data = ASCII_GLYPHS[c]
                    break
            # ASCII_GLYPHS に見つからなければ GLYPHS を参照（互換性のため）
            if glyph_data is None:
                for c in candidates:
                    if c in GLYPHS:
                        glyph_data = GLYPHS[c]
                        break
        else:
            # 非ASCII: まず GLYPHS を直接参照
            if ch in GLYPHS:
                glyph_data = GLYPHS[ch]
            else:
                for c in (ch, ch.upper(), ch.lower()):
                    if c in GLYPHS:
                        glyph_data = GLYPHS[c]
                        break

        if glyph_data is None:
            print(f"未定義の文字: {ch}")
            return np.zeros(SAMPLES_PER_CHAR, dtype=np.float32)

        # グリフは与えられた形式をそのまま使う（信頼）。列数を14に整形するのみ。
        glyph_cols = _ensure_14_columns(glyph_data)

        # 固定14列でバッファ長を計算
        columns = COLUMNS_PER_CHAR
        total_samples = SAMPLES_PER_PIXEL * PIXELS_PER_COLUMN * columns
        buffer = np.zeros(total_samples, dtype=np.float32)
        sample_index = 0

        # 列単位でエンコード（各列は PIXELS_PER_COLUMN ビット）
        for col in range(columns):
            data = int(glyph_cols[col])
            for y in range(PIXELS_PER_COLUMN):
                bit = (data >> y) & 1
                wave = generate_tone(bit == 1)
                end = sample_index + SAMPLES_PER_PIXEL
                if end <= total_samples:
                    buffer[sample_index:end] = wave
                sample_index = end

        # 文字の最後に短い無音区間を追加して同期を保つ（可能なら）
        silence_samples = int(SAMPLE_RATE * 0.001)  # 1ms
        if sample_index + silence_samples <= total_samples:
            buffer[sample_index:sample_index + silence_samples] = 0

        return buffer

    except Exception as e:
        print(f"Error processing character '{ch}': {e}")
        return np.zeros(SAMPLES_PER_CHAR, dtype=np.float32)

class SettingsWindow:
    def __init__(self, parent: tk.Tk, app) -> None:
        self.window = tk.Toplevel(parent)
        self.window.title("設定")
        self.window.geometry("300x400")  # ウィンドウを大きくする
        self.window.transient(parent)
        self.window.grab_set()
        self.app = app

        # フォント設定
        default_font = ('Yu Gothic UI', 12)

        # サウンドデバイス設定
        device_frame = ttk.LabelFrame(self.window, text="出力デバイス", padding=10)
        device_frame.pack(fill='x', padx=10, pady=5)

        # デバイス選択
        self.device_var = tk.StringVar(value=self.app.device_var.get())
        self.device_combo = ttk.Combobox(
            device_frame,
            textvariable=self.device_var,
            font=default_font,
            state='readonly',
            values=self.app.device_combo['values']
        )
        self.device_combo.pack(fill='x', padx=5, pady=5)
        try:
            self.device_combo.current(self.app.device_combo.current())
        except Exception:
            if self.app.device_combo['values']:
                self.device_combo.current(0)

        # 音量設定フレーム
        volume_frame = ttk.LabelFrame(self.window, text="出力レベル", padding=10)
        volume_frame.pack(fill='x', padx=10, pady=5)

        # 音量スケール
        self.volume_var = tk.DoubleVar(value=self.app.volume_level)
        self.volume_scale = ttk.Scale(
            volume_frame,
            from_=-60,  # -60dB
            to=0,      # 0dB (MAX)
            orient='horizontal',
            variable=self.volume_var
        )
        self.volume_scale.pack(fill='x', padx=5, pady=5)

        # dB値表示ラベル
        self.db_label = ttk.Label(volume_frame, font=default_font)
        self.db_label.pack(pady=5)

        # 音量値が変更されたときのコールバック
        def on_volume_changed(event=None):
            self.db_label.configure(text=f"{self.volume_var.get():.1f} dB")

        self.volume_scale.configure(command=on_volume_changed)
        on_volume_changed()  # 初期値を表示

        # PTT設定フレーム
        ptt_frame = ttk.LabelFrame(self.window, text="PTT制御", padding=10)
        ptt_frame.pack(fill='x', padx=10, pady=5)

        # COMポート選択 — 先頭に "なし" を追加
        ports = ['なし'] + [port.device for port in serial.tools.list_ports.comports()]
        self.port_var = tk.StringVar(value=(self.app.ptt.port_name if self.app.ptt.port_name else 'なし'))
        port_frame = ttk.Frame(ptt_frame)
        port_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(port_frame, text="COMポート:", font=default_font).pack(side='left')
        self.port_combo = ttk.Combobox(
            port_frame,
            textvariable=self.port_var,
            values=ports,
            font=default_font,
            state='readonly'
        )
        self.port_combo.pack(side='left', padx=5, fill='x', expand=True)
        try:
            self.port_combo.current(ports.index(self.port_var.get()))
        except ValueError:
            self.port_combo.current(0)

        # 制御線選択
        control_frame = ttk.Frame(ptt_frame)
        control_frame.pack(fill='x', padx=5, pady=5)

        # RTS選択
        self.rts_var = tk.BooleanVar(value=self.app.ptt.use_rts)
        ttk.Checkbutton(
            control_frame,
            text="RTS",
            variable=self.rts_var,
            style='Switch.TCheckbutton'
        ).pack(side='left', padx=10)

        # DTR選択
        self.dtr_var = tk.BooleanVar(value=self.app.ptt.use_dtr)
        ttk.Checkbutton(
            control_frame,
            text="DTR",
            variable=self.dtr_var,
            style='Switch.TCheckbutton'
        ).pack(side='left', padx=10)

        # ボタンフレーム
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill='x', padx=10, pady=10)
        ttk.Button(button_frame, text="保存", command=self.save_settings).pack(side='right', padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.window.destroy).pack(side='right')

    def save_settings(self) -> None:
        # デバイス選択を更新
        try:
            current = self.device_combo.current()
            self.app.device_combo.current(current)
            self.app.device_var.set(self.device_var.get())
        except Exception:
            pass

        # 音量レベルを更新
        self.app.volume_level = self.volume_var.get()

        # PTT設定を更新
        port_name = self.port_var.get()

        # 既存の接続は閉じる
        try:
            self.app.ptt.close()
        except Exception:
            pass

        if port_name and port_name != 'なし':
            try:
                # フラグを設定してポートを開く
                self.app.ptt.use_rts = self.rts_var.get()
                self.app.ptt.use_dtr = self.dtr_var.get()
                self.app.ptt.open(port_name)
            except Exception as e:
                messagebox.showerror("エラー", f"PTTポートのオープンに失敗しました: {e}")
        else:
            # 'なし' が選択された場合はポート情報をクリア
            self.app.ptt.port_name = None
            self.app.ptt.use_rts = False
            self.app.ptt.use_dtr = False

        # 設定をINIファイルに保存
        config = configparser.ConfigParser()
        config['Sound'] = {
            'device_name': self.device_var.get(),
            'volume_level': str(self.volume_var.get())
        }
        config['PTT'] = {
            'port_name': (port_name if port_name and port_name != 'なし' else ''),
            'use_rts': str(self.rts_var.get()),
            'use_dtr': str(self.dtr_var.get())
        }

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)

        self.window.destroy()

class HellschreiberGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("ヘルシュライバー送信機")
        
        # 音量レベルの初期化
        self.volume_level = -20  # デフォルトは-20dB（-20dBFS）

        # ツールバーフレーム
        toolbar_frame = tk.Frame(root)
        toolbar_frame.pack(fill='x')
        
        # 設定アイコンの読み込み（インスタンス変数として保持）
        icon_path = Path(os.path.dirname(os.path.abspath(__file__))) / '歯車アイコン.png'
        self.settings_icon = tk.PhotoImage(file=str(icon_path))
        # アイコンのサイズを24x24に調整
        self.settings_icon = self.settings_icon.subsample(
            max(1, self.settings_icon.width() // 24),
            max(1, self.settings_icon.height() // 24)
        )
        
        # 設定ボタン（右寄せ）
        self.settings_button = tk.Button(
            toolbar_frame,
            image=self.settings_icon,
            command=self.show_settings,
            relief='flat',
            background=root.cget('background')
        )
        self.settings_button.pack(side='right', padx=5, pady=5)


        # サウンドデバイスの取得とセットアップ
        try:
            devices = sd.query_devices()
            self.audio_available = True
        except Exception as e:
            print(f"音声デバイス取得エラー: {e}")
            devices = []
            self.audio_available = False

        self.output_devices: List[Tuple[int, DeviceInfo]] = [
            (i, DeviceInfo(device)) for i, device in enumerate(devices) 
            if isinstance(device, dict) and int(device.get('max_output_channels', 0)) > 0
        ]
        
        # デバイス選択の初期化
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(root, textvariable=self.device_var)  # 非表示のコンボボックス
          # デバイスリストの設定
        device_names = [dev[1].name for dev in self.output_devices]
        self.device_combo['values'] = device_names
        
        # INIファイルから設定を読み込み
        config = configparser.ConfigParser()
        saved_device_name = None
          # PTTコントロールの初期化
        self.ptt = PTTControl()

        if CONFIG_FILE.exists():
            try:
                config.read(CONFIG_FILE, encoding='utf-8')
                saved_device_name = config.get('Sound', 'device_name', fallback=None)
                self.volume_level = float(config.get('Sound', 'volume_level', fallback='-20'))

                # PTT設定の読み込み
                ptt_port = config.get('PTT', 'port_name', fallback=None)
                if ptt_port:
                    try:
                        self.ptt.open(ptt_port)
                        self.ptt.use_rts = config.getboolean('PTT', 'use_rts', fallback=False)
                        self.ptt.use_dtr = config.getboolean('PTT', 'use_dtr', fallback=False)
                        self.ptt.update_lines()
                    except Exception:
                        pass
            except Exception:
                pass
        
        # 保存されていたデバイスを探す
        if saved_device_name:
            for i, name in enumerate(device_names):
                if name == saved_device_name:
                    self.device_combo.current(i)
                    break
            else:  # 保存されていたデバイスが見つからない場合
                if device_names:
                    self.device_combo.current(0)
        else:  # 保存された設定がない場合はデフォルトデバイスを使用
            try:
                if self.audio_available:
                    default_device = sd.default.device[1]
                else:
                    default_device = None
            except Exception:
                default_device = None

            if default_device is not None:
                for i, (dev_id, _) in enumerate(self.output_devices):
                    if dev_id == default_device:
                        self.device_combo.current(i)
                        break
                else:
                    if device_names:
                        self.device_combo.current(0)
            else:
                # 音声が利用できない場合は空リストにしておく
                if device_names:
                    self.device_combo.current(0)
        
        # フォント設定
        default_font = ('Yu Gothic UI', 12)
        
        # 入力欄
        tk.Label(root, text="送信テキスト:", font=default_font).pack(anchor='w', padx=10)
        self.input_entry = tk.Entry(root, font=default_font)
        self.input_entry.pack(padx=10, pady=5, fill='x')

        # 送信ボタン
        self.send_button = tk.Button(
            root, 
            text="送信開始", 
            font=default_font,
            command=self.start_transmission
        )
        self.send_button.pack(pady=5)

        # 送信欄
        tk.Label(root, text="送信状況:", font=default_font).pack(anchor='w', padx=10)
        self.output_display = tk.Text(            root, 
            height=2, 
            font=default_font, 
            state='disabled',
            wrap='none'
        )
        self.output_display.pack(padx=10, pady=5, fill='x')
        
        # タグ設定
        self.output_display.tag_configure("pending", foreground="gray")
        self.output_display.tag_configure("sent", foreground="red")

        # 音声ストリーム
        self.audio_stream = None
        self.stream_lock = threading.Lock()  # ストリームアクセスの排他制御用

    def show_settings(self) -> None:
        """設定ウィンドウを表示"""
        SettingsWindow(self.root, self)

    def start_transmission(self) -> None:
        text = self.input_entry.get()
        if not text:
            self.send_button.config(state='normal')
            return

        # サウンド機能が利用可能か確認
        if not getattr(self, 'audio_available', True):
            messagebox.showerror("エラー", "音声デバイスが利用できません。設定を確認してください。")
            return

        # 出力デバイスが選択されているか確認
        device_id = self.get_selected_device_id()
        if device_id is None:
            messagebox.showerror("エラー", "出力デバイスが選択されていません。設定を確認してください。")
            return

        # 先にオーディオストリームを初期化しておく（失敗時は通知して中止）
        try:
            self._initialize_audio_stream(device_id)
        except Exception as e:
            message = f"オーディオストリームの初期化に失敗しました: {e}"
            print(message)
            # 初期化に失敗したら音声機能を無効化
            self.audio_available = False
            messagebox.showerror("エラー", message)
            return

        self.send_button.config(state='disabled')

        # プレフィックスとサフィックスを追加したテキストを表示
        text_with_markers = "...   " + text + "   ..."
        
        # 送信欄を更新
        self.output_display.config(state='normal')
        self.output_display.delete("1.0", tk.END)
        self.output_display.insert("1.0", text_with_markers, "pending")
        self.output_display.config(state='disabled')
        
        # 送信スレッドを開始（マーカー付きテキストを渡す）
        threading.Thread(target=self.transmit_text, args=(text_with_markers,), daemon=True).start()

    def get_selected_device_id(self) -> Optional[int]:
        """選択されているデバイスのIDを取得"""
        current = self.device_combo.current()
        if current >= 0:
            return self.output_devices[current][0]
        return None
        
    def _initialize_audio_stream(self, device_id: int) -> None:
        """音声出力ストリームを初期化（例外を上位に伝える）"""
        with self.stream_lock:
            try:
                if self.audio_stream is not None:
                    try:
                        self.audio_stream.close()
                    except Exception:
                        pass
                    self.audio_stream = None

                # ブロックサイズを小さくしてレイテンシーを減らす
                blocksize = SAMPLES_PER_PIXEL
                self.audio_stream = sd.OutputStream(
                    samplerate=SAMPLE_RATE,
                    device=device_id,
                    channels=1,
                    blocksize=blocksize,
                    latency='low',
                    dtype=np.float32
                )
                self.audio_stream.start()
                self.audio_available = True
            except Exception as ex:
                # 音声関連の例外はここでキャッチしてフラグを切る
                print(f"音声ストリーム初期化エラー: {ex}")
                try:
                    if self.audio_stream is not None:
                        self.audio_stream.close()
                except Exception:
                    pass
                self.audio_stream = None
                self.audio_available = False
                # 上位で処理するため例外を投げる
                raise

    def _play_waves(self, waves: List[np.ndarray]) -> None:
        """波形データのリストを再生する（余分なパディングをせずチャンク単位で書き込む）"""
        if not waves:
            return

        if not getattr(self, 'audio_available', True):
            raise Exception("音声デバイスが利用できません")

        device_id = self.get_selected_device_id()
        if device_id is None:
            raise Exception("出力デバイスが選択されていません")

        try:
            if self.audio_stream is None:
                self._initialize_audio_stream(device_id)
            if self.audio_stream is None:
                raise Exception("音声ストリームの初期化に失敗しました")

            combined_wave = np.concatenate(waves)
            volume_factor = 10 ** (self.volume_level / 20)
            adjusted_wave = combined_wave * volume_factor

            # ゼロパディングは行わない。小さなチャンクに分けて順次書き込む。
            chunk_size = max(1, SAMPLES_PER_PIXEL * 8)
            with self.stream_lock:
                for i in range(0, len(adjusted_wave), chunk_size):
                    chunk = adjusted_wave[i:i + chunk_size]
                    try:
                        self.audio_stream.write(chunk)
                    except Exception as e:
                        print(f"再生中エラー(write): {e}")
                        self.audio_available = False
                        # 再初期化を試みる
                        try:
                            self._initialize_audio_stream(device_id)
                        except Exception:
                            pass
                        raise

        except sd.PortAudioError as e:
            print(f"音声出力エラー: {e}")
            self.audio_available = False
            try:
                self._initialize_audio_stream(device_id)
            except Exception:
                pass
            raise
        except Exception:
            # 既にログ出力済みの可能性があるので再送出
            raise

    def _play_wave(self, wave: np.ndarray) -> None:
        """1文字分の波形を再生（音量適用、パディングは行わない）"""
        if wave is None or wave.size == 0:
            return

        if not getattr(self, 'audio_available', True):
            raise Exception("音声デバイスが利用できません")

        device_id = self.get_selected_device_id()
        if device_id is None:
            raise Exception("出力デバイスが選択されていません")

        # ストリームがなければ初期化
        if self.audio_stream is None:
            self._initialize_audio_stream(device_id)
        if self.audio_stream is None:
            raise Exception("音声ストリームの初期化に失敗しました")

        volume_factor = 10 ** (self.volume_level / 20)
        adjusted = wave * volume_factor

        # 余分なゼロ追加はしない。小チャンクで書き込み。
        chunk_size = max(1, SAMPLES_PER_PIXEL * 8)
        with self.stream_lock:
            for i in range(0, len(adjusted), chunk_size):
                chunk = adjusted[i:i + chunk_size]
                try:
                    self.audio_stream.write(chunk)
                except Exception as e:
                    print(f"再生中エラー(write): {e}")
                    self.audio_available = False
                    # ユーザに通知
                    messagebox.showerror("エラー", f"再生中にエラーが発生しました: {e}")
                    raise

    def transmit_text(self, text: str) -> None:
        try:
            # PTTをON
            self.ptt.set_ptt(True)
            time.sleep(LATENCY)

            # 各文字ごとに波形を生成して即時送信、タグ更新は送信前に行う
            for i, ch in enumerate(text):
                try:
                    wave = send_char(ch)
                except Exception as e:
                    print(f"send_char エラー: {e}")
                    wave = np.zeros(SAMPLES_PER_CHAR, dtype=np.float32)

                if wave.size > 0:
                    # タグ更新（送信開始と同時に色を変える）
                    self.output_display.config(state='normal')
                    try:
                        self.output_display.tag_remove("pending", f"1.{i}", f"1.{i+1}")
                        self.output_display.tag_add("sent", f"1.{i}", f"1.{i+1}")
                    except tk.TclError:
                        pass
                    self.output_display.config(state='disabled')
                    self.root.update()

                    # 再生。再生エラーはログに出して中断する
                    try:
                        self._play_wave(wave)
                    except Exception as e:
                        print(f"再生エラー: {e}")
                        messagebox.showerror("エラー", f"再生中にエラーが発生しました: {e}")
                        break

        except Exception as e:
            print(f"送信エラー: {e}")
            messagebox.showerror("エラー", f"送信中にエラーが発生しました: {e}")
        finally:
            time.sleep(LATENCY)
            self.ptt.set_ptt(False)
            self.send_button.config(state='normal')
            
    def __del__(self):
        """デストラクタ：音声ストリームを確実にクローズ"""
        if hasattr(self, 'audio_stream') and self.audio_stream is not None:
            self.audio_stream.close()

# メイン処理
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = HellschreiberGUI(root)
        root.mainloop()
    except Exception as e:
        print(f"アプリケーションエラー: {e}")
        messagebox.showerror("エラー", f"アプリケーションエラー: {e}")
