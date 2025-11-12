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
PIXELS_PER_COLUMN = 14  # 1列あたりのピクセル数
COLUMNS_PER_CHAR = 7    # 1文字あたりの列数
# 1ピクセルあたりの正確なサンプル数を計算（整数に丸める）
SAMPLES_PER_PIXEL = int(SAMPLE_RATE * 0.004045)  # 約4.045ミリ秒
# 1文字分の合計サンプル数
SAMPLES_PER_CHAR = SAMPLES_PER_PIXEL * PIXELS_PER_COLUMN * COLUMNS_PER_CHAR
# 音声出力の設定
BUFFER_SAMPLES = SAMPLES_PER_CHAR * 2  # バッファサイズを文字サイズの倍数に
LATENCY = 0.2  # 出力レイテンシー（秒）

class DeviceInfo:
    """サウンドデバイス情報を保持するクラス"""
    def __init__(self, device_dict: Dict[str, Any]) -> None:
        self.name: str = str(device_dict.get('name', ''))
        self.max_output_channels: int = int(device_dict.get('max_output_channels', 0))

# ASCII文字のグリフデータ (ArduinoHellと同じ：各列14ビット)
ASCII_GLYPHS = {
    ' ': [0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000],
    'A': [0x07fc, 0x0e60, 0x0c60, 0x0e60, 0x07fc, 0x0000, 0x0000],
    'B': [0x0c0c, 0x0ffc, 0x0ccc, 0x0ccc, 0x0738, 0x0000, 0x0000],
    'C': [0x0ffc, 0x0c0c, 0x0c0c, 0x0c0c, 0x0c0c, 0x0000, 0x0000],
    'D': [0x0c0c, 0x0ffc, 0x0c0c, 0x0c0c, 0x07f8, 0x0000, 0x0000],
    'E': [0x0ffc, 0x0ccc, 0x0ccc, 0x0c0c, 0x0c0c, 0x0000, 0x0000],
    'F': [0x0ffc, 0x0cc0, 0x0cc0, 0x0c00, 0x0c00, 0x0000, 0x0000],
    'G': [0x0ffc, 0x0c0c, 0x0c0c, 0x0ccc, 0x0cfc, 0x0000, 0x0000],
    'H': [0x0ffc, 0x00c0, 0x00c0, 0x00c0, 0x0ffc, 0x0000, 0x0000],
    'I': [0x0ffc, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000],
    'J': [0x003c, 0x000c, 0x000c, 0x000c, 0x0ffc, 0x0000, 0x0000],
    'K': [0x0ffc, 0x00c0, 0x00e0, 0x0330, 0x0e1c, 0x0000, 0x0000],
    'L': [0x0ffc, 0x000c, 0x000c, 0x000c, 0x000c, 0x0000, 0x0000],
    'M': [0x0ffc, 0x0600, 0x0300, 0x0600, 0x0ffc, 0x0000, 0x0000],
    'N': [0x0ffc, 0x0700, 0x01c0, 0x0070, 0x0ffc, 0x0000, 0x0000],
    'O': [0x0ffc, 0x0c0c, 0x0c0c, 0x0c0c, 0x0ffc, 0x0000, 0x0000],
    'P': [0x0c0c, 0x0ffc, 0x0ccc, 0x0cc0, 0x0780, 0x0000, 0x0000],
    'Q': [0x0ffc, 0x0c0c, 0x0c3c, 0x0ffc, 0x000f, 0x0000, 0x0000],
    'R': [0x0ffc, 0x0cc0, 0x0cc0, 0x0cf0, 0x079c, 0x0000, 0x0000],
    'S': [0x078c, 0x0ccc, 0x0ccc, 0x0ccc, 0x0c78, 0x0000, 0x0000],
    'T': [0x0c00, 0x0c00, 0x0ffc, 0x0c00, 0x0c00, 0x0000, 0x0000],
    'U': [0x0ff8, 0x000c, 0x000c, 0x000c, 0x0ff8, 0x0000, 0x0000],
    'V': [0x0ffc, 0x0038, 0x00e0, 0x0380, 0x0e00, 0x0000, 0x0000],
    'W': [0x0ff8, 0x000c, 0x00f8, 0x000c, 0x0ff8, 0x0000, 0x0000],
    'X': [0x0e1c, 0x0330, 0x01e0, 0x0330, 0x0e1c, 0x0000, 0x0000],
    'Y': [0x0e00, 0x0380, 0x00fc, 0x0380, 0x0e00, 0x0000, 0x0000],
    'Z': [0x0c1c, 0x0c7c, 0x0ccc, 0x0f8c, 0x0e0c, 0x0000, 0x0000],
    '0': [0x07f8, 0x0c0c, 0x0c0c, 0x0c0c, 0x07f8, 0x0000, 0x0000],
    '1': [0x0300, 0x0600, 0x0ffc, 0x0000, 0x0000, 0x0000, 0x0000],
    '2': [0x061c, 0x0c3c, 0x0ccc, 0x078c, 0x000c, 0x0000, 0x0000],
    '3': [0x0006, 0x1806, 0x198c, 0x1f98, 0x00f0, 0x0000, 0x0000],
    '4': [0x1fe0, 0x0060, 0x0060, 0x0ffc, 0x0060, 0x0000, 0x0000],
    '5': [0x000c, 0x000c, 0x1f8c, 0x1998, 0x18f0, 0x0000, 0x0000],
    '6': [0x07fc, 0x0c66, 0x18c6, 0x00c6, 0x007c, 0x0000, 0x0000],
    '7': [0x181c, 0x1870, 0x19c0, 0x1f00, 0x1c00, 0x0000, 0x0000],
    '8': [0x0f3c, 0x19e6, 0x18c6, 0x19e6, 0x0f3c, 0x0000, 0x0000],
    '9': [0x0f80, 0x18c6, 0x18cc, 0x1818, 0x0ff0, 0x0000, 0x0000],
    '*': [0x018c, 0x0198, 0x0ff0, 0x0198, 0x018c, 0x0000, 0x0000],
    '.': [0x001c, 0x001c, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000],
    '?': [0x1800, 0x1800, 0x19ce, 0x1f00, 0x0000, 0x0000, 0x0000],
    '!': [0x1f9c, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000],
    '(': [0x01e0, 0x0738, 0x1c0e, 0x0000, 0x0000, 0x0000, 0x0000],
    ')': [0x1c0e, 0x0738, 0x01e0, 0x0000, 0x0000, 0x0000, 0x0000],
    '#': [0x0330, 0x0ffc, 0x0330, 0x0ffc, 0x0330, 0x0000, 0x0000],
    '$': [0x078c, 0x0ccc, 0x1ffe, 0x0ccc, 0x0c78, 0x0000, 0x0000],
    '/': [0x001c, 0x0070, 0x01c0, 0x0700, 0x1c00, 0x0000, 0x0000],
}

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
        return GLYPHS
    except ImportError:
        print("警告: グリフファイル (glyphs.py) が見つかりません。")
        print("ASCII文字のみ使用可能です。")
        return {}

GLYPHS = load_glyphs()

def send_char(ch: str) -> np.ndarray:
    """1文字分の波形を生成（サンプル数を正確に保つ）"""
    try:
        # 文字間の同期を保つため、厳密なサンプル数で計算
        total_samples = SAMPLES_PER_CHAR
        buffer = np.zeros(total_samples, dtype=np.float32)
        sample_index = 0
        
        if ord(ch) > 0x7F:  # 日本語文字
            if ch not in GLYPHS:
                print(f"未定義の文字: {ch}")
                return buffer
            glyph_data = GLYPHS[ch]
            
            # 日本語グリフのエンコード
            for col in range(COLUMNS_PER_CHAR):
                data = glyph_data[col]
                for y in range(PIXELS_PER_COLUMN):
                    bit = (data >> y) & 1
                    wave = generate_tone(bit == 1)
                    if sample_index + SAMPLES_PER_PIXEL <= total_samples:
                        buffer[sample_index:sample_index + SAMPLES_PER_PIXEL] = wave
                    sample_index += SAMPLES_PER_PIXEL
                    
        else:  # ASCII文字
            ch = ch.upper()
            if ch not in ASCII_GLYPHS:
                print(f"未定義の文字: {ch}")
                return buffer
            glyph_data = ASCII_GLYPHS[ch]
            
            # ASCII文字のエンコード
            for col in range(COLUMNS_PER_CHAR):
                data = glyph_data[col]
                for y in range(PIXELS_PER_COLUMN):
                    bit = (data >> y) & 1
                    wave = generate_tone(bit == 1)
                    if sample_index + SAMPLES_PER_PIXEL <= total_samples:
                        buffer[sample_index:sample_index + SAMPLES_PER_PIXEL] = wave
                    sample_index += SAMPLES_PER_PIXEL
        
        # 文字の最後に短い無音区間を追加して同期を保つ
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
        self.device_combo.current(self.app.device_combo.current())

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

        # COMポート選択
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_var = tk.StringVar(value=self.app.ptt.port_name if self.app.ptt.port_name else '')
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
        current = self.device_combo.current()
        self.app.device_combo.current(current)
        self.app.device_var.set(self.device_var.get())
        
        # 音量レベルを更新
        self.app.volume_level = self.volume_var.get()        # PTT設定を更新
        port_name = self.port_var.get()
        if port_name:
            try:
                self.app.ptt.close()  # 既存の接続を閉じる
                # まずフラグを設定
                self.app.ptt.use_rts = self.rts_var.get()
                self.app.ptt.use_dtr = self.dtr_var.get()
                # その後でポートを開く
                self.app.ptt.open(port_name)  # 新しいポートで接続
            except Exception as e:
                messagebox.showerror("エラー", f"PTTポートのオープンに失敗しました: {e}")

        # 設定をINIファイルに保存
        config = configparser.ConfigParser()
        config['Sound'] = {
            'device_name': self.device_var.get(),
            'volume_level': str(self.volume_var.get())
        }
        config['PTT'] = {
            'port_name': port_name,
            'use_rts': str(self.rts_var.get()),
            'use_dtr': str(self.dtr_var.get())
        }
        
        # ファイルに書き込み
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
        
        self.window.destroy()

class HellschreiberGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("ヘルシュライバー送信機")
        
        # 音量レベルの初期化
        self.volume_level = 0  # デフォルトは0dB（最大）

        # ツールバーフレーム
        toolbar_frame = tk.Frame(root)
        toolbar_frame.pack(fill='x')
        
        # 設定アイコンの読み込み（インスタンス変数として保持）
        icon_path = Path(os.path.dirname(os.path.abspath(__file__))) / '無料の設定歯車アイコン.png'
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
        devices = sd.query_devices()
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
                self.volume_level = float(config.get('Sound', 'volume_level', fallback='0'))

                # PTT設定の読み込み
                ptt_port = config.get('PTT', 'port_name', fallback=None)
                if ptt_port:
                    try:
                        self.ptt.open(ptt_port)
                        self.ptt.use_rts = config.getboolean('PTT', 'use_rts', fallback=False)
                        self.ptt.use_dtr = config.getboolean('PTT', 'use_dtr', fallback=False)
                        self.ptt.update_lines()
                    except:
                        pass
            except:
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
            default_device = sd.default.device[1]
            for i, (dev_id, _) in enumerate(self.output_devices):
                if dev_id == default_device:
                    self.device_combo.current(i)
                    break
            else:
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
            except Exception:
                try:
                    if self.audio_stream is not None:
                        self.audio_stream.close()
                except Exception:
                    pass
                self.audio_stream = None
                raise

    def _play_waves(self, waves: List[np.ndarray]) -> None:
        """波形データのリストを再生する（余分なパディングをせずチャンク単位で書き込む）"""
        if not waves:
            return

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
                    self.audio_stream.write(chunk)

        except sd.PortAudioError as e:
            print(f"音声出力エラー: {e}")
            # 再初期化を試みる
            self._initialize_audio_stream(device_id)
            raise

    def _play_wave(self, wave: np.ndarray) -> None:
        """1文字分の波形を再生（音量適用、パディングは行わない）"""
        if wave is None or wave.size == 0:
            return
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
                self.audio_stream.write(chunk)

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
