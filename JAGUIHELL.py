#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
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

# local glyphs
try:
    from glyphs import GLYPHS
except Exception:
    GLYPHS = {}

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
            self.serial_port = serial.Serial(port=port_name, baudrate=9600, timeout=1, write_timeout=1, exclusive=True)
            if not self.serial_port.is_open:
                self.serial_port.open()
            self.update_lines()
        except serial.SerialException as e:
            raise Exception(f"シリアルポート {port_name} のオープンに失敗しました: {str(e)}")

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
            # set defaults (PTT OFF)
            if self.use_rts:
                self.serial_port.rts = False
            else:
                self.serial_port.rts = False
            time.sleep(0.1)
            if self.use_dtr:
                self.serial_port.dtr = False
            else:
                self.serial_port.dtr = False
        except Exception:
            pass

    def set_ptt(self, state: bool) -> None:
        if self.serial_port:
            if self.use_rts:
                self.serial_port.rts = state
            if self.use_dtr:
                self.serial_port.dtr = state

# ---- サウンド設定 ----
FREQ = 1000
SAMPLE_RATE = 48000
PIXELS_PER_COLUMN = 14
COLUMNS_PER_CHAR = 13   # default for CJK etc
ASCII_COLUMNS = 9       # ascii layout: 1 pad + 7 core + 1 pad (ユーザ要望)
SAMPLES_PER_PIXEL = int(SAMPLE_RATE * 0.004045)
SAMPLES_PER_CHAR = SAMPLES_PER_PIXEL * PIXELS_PER_COLUMN * COLUMNS_PER_CHAR

def _samples_for_columns(cols: int) -> int:
    return SAMPLES_PER_PIXEL * PIXELS_PER_COLUMN * int(cols)

BUFFER_SAMPLES = SAMPLES_PER_CHAR * 2
LATENCY = 0.2
# inter-character gap in milliseconds (can be tuned to correct vertical sync drift)
INTER_CHAR_GAP_MS = 3.2

class DeviceInfo:
    def __init__(self, device_dict: Dict[str, Any]) -> None:
        self.name: str = str(device_dict.get('name', ''))
        self.max_output_channels: int = int(device_dict.get('max_output_channels', 0))


def generate_tone(on: bool) -> np.ndarray:
    if on:
        t = np.linspace(0, SAMPLES_PER_PIXEL / SAMPLE_RATE, SAMPLES_PER_PIXEL, False)
        wave = 0.5 * np.sin(2 * np.pi * FREQ * t)
    else:
        wave = np.zeros(SAMPLES_PER_PIXEL)
    return wave.astype(np.float32)


def generate_silence(duration: float) -> np.ndarray:
    samples = int(SAMPLE_RATE * duration)
    return np.zeros(samples, dtype=np.float32)


def load_glyphs() -> Dict[str, List[int]]:
    # GLYPHS imported at top; normalize to default columns for CJK
    def _norm(g):
        if not isinstance(g, (list, tuple)):
            return [0] * COLUMNS_PER_CHAR
        lst = list(g)
        if len(lst) >= COLUMNS_PER_CHAR:
            return lst[:COLUMNS_PER_CHAR]
        lst.extend([0] * (COLUMNS_PER_CHAR - len(lst)))
        return lst
    try:
        return {k: _norm(v) for k, v in GLYPHS.items()}
    except Exception:
        return {}

GLYPHS = load_glyphs()


def _ensure_columns(glyph_data: List[int], cols: int = COLUMNS_PER_CHAR) -> List[int]:
    try:
        desired = int(cols)
    except Exception:
        desired = COLUMNS_PER_CHAR
    if not isinstance(glyph_data, (list, tuple)):
        return [0] * desired
    out = list(glyph_data)
    if len(out) >= desired:
        return out[:desired]
    out.extend([0] * (desired - len(out)))
    return out

# ASCII glyphs: try import, normalize to ASCII_COLUMNS
ASCII_GLYPHS = {' ': [0x0000] * ASCII_COLUMNS}
try:
    from ascii_glyphs import GLYPHS as ASCII_SOURCE
    def _ensure_ascii_cols(cols: List[int]) -> List[int]:
        # Accept regenerated ascii_glyphs as-is; just pad/truncate to ASCII_COLUMNS if needed
        if not isinstance(cols, (list, tuple)):
            return [0] * ASCII_COLUMNS
        lst = list(cols)
        if len(lst) >= ASCII_COLUMNS:
            return lst[:ASCII_COLUMNS]
        lst.extend([0] * (ASCII_COLUMNS - len(lst)))
        return lst

    ASCII_GLYPHS = {k: _ensure_ascii_cols(v) for k, v in ASCII_SOURCE.items()}
    _ASCII_AVAILABLE = True
except Exception:
    _ASCII_AVAILABLE = False


def _rows_to_cols(rows_list: List[int], cols: int = 14, rows: int = 14) -> List[int]:
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
                out_bitpos = (rows - 1 - row_index)
                col_val |= (1 << out_bitpos)
        cols_out.append(col_val)
    return cols_out


def _count_nonzero(items: List[int]) -> int:
    return sum(1 for v in items if v != 0)


def send_char(ch: str) -> np.ndarray:
    try:
        glyph_data = None
        if ord(ch) <= 0x7F:
            candidates = [ch, ch.upper(), ch.lower()]
            for c in candidates:
                if c in ASCII_GLYPHS:
                    glyph_data = ASCII_GLYPHS[c]
                    break
            if glyph_data is None:
                for c in candidates:
                    if c in GLYPHS:
                        glyph_data = GLYPHS[c]
                        break
        else:
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
        # If ascii and ascii glyphs were normalized to ASCII_COLUMNS, glyph_data length will reflect that.
        if isinstance(glyph_data, (list, tuple)):
            glyph_cols = list(glyph_data)
        else:
            glyph_cols = _ensure_columns(glyph_data, cols=COLUMNS_PER_CHAR)
        columns = max(1, len(glyph_cols))
        total_samples = _samples_for_columns(columns)
        buffer = np.zeros(total_samples, dtype=np.float32)
        sample_index = 0
        for col in range(columns):
            data = int(glyph_cols[col])
            for y in range(PIXELS_PER_COLUMN):
                bit = (data >> y) & 1
                wave = generate_tone(bit == 1)
                end = sample_index + SAMPLES_PER_PIXEL
                if end <= total_samples:
                    buffer[sample_index:end] = wave
                sample_index = end
        # optional trailing silence
        silence_samples = int(SAMPLE_RATE * 0.001)
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
        self.window.geometry("520x420")
        try:
            self.window.minsize(420, 320)
        except Exception:
            pass
        self.window.transient(parent)
        self.window.grab_set()
        self.app = app
        default_font = ('Yu Gothic UI', 12)
        device_frame = ttk.LabelFrame(self.window, text="出力デバイス", padding=10)
        device_frame.pack(fill='x', padx=10, pady=5)
        self.device_var = tk.StringVar(value=self.app.device_var.get())
        self.device_combo = ttk.Combobox(device_frame, textvariable=self.device_var, font=default_font, state='readonly', values=self.app.device_combo['values'])
        self.device_combo.pack(fill='x', padx=5, pady=5)
        try:
            self.device_combo.current(self.app.device_combo.current())
        except Exception:
            if self.app.device_combo['values']:
                self.device_combo.current(0)
        volume_frame = ttk.LabelFrame(self.window, text="出力レベル", padding=10)
        volume_frame.pack(fill='x', padx=10, pady=5)
        self.volume_var = tk.DoubleVar(value=self.app.volume_level)
        self.volume_scale = ttk.Scale(volume_frame, from_=-60, to=0, orient='horizontal', variable=self.volume_var)
        self.volume_scale.pack(fill='x', padx=5, pady=5)
        self.db_label = ttk.Label(volume_frame, font=default_font)
        self.db_label.pack(pady=5)
        def on_volume_changed(event=None):
            self.db_label.configure(text=f"{self.volume_var.get():.1f} dB")
        self.volume_scale.configure(command=on_volume_changed)
        on_volume_changed()
        ptt_frame = ttk.LabelFrame(self.window, text="PTT制御", padding=10)
        ptt_frame.pack(fill='x', padx=10, pady=5)
        ports = ['なし'] + [port.device for port in serial.tools.list_ports.comports()]
        self.port_var = tk.StringVar(value=(self.app.ptt.port_name if self.app.ptt.port_name else 'なし'))
        port_frame = ttk.Frame(ptt_frame)
        port_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(port_frame, text="COMポート:", font=default_font).pack(side='left')
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.port_var, values=ports, font=default_font, state='readonly')
        self.port_combo.pack(side='left', padx=5, fill='x', expand=True)
        try:
            self.port_combo.current(ports.index(self.port_var.get()))
        except ValueError:
            self.port_combo.current(0)
        control_frame = ttk.Frame(ptt_frame)
        control_frame.pack(fill='x', padx=5, pady=5)
        self.rts_var = tk.BooleanVar(value=self.app.ptt.use_rts)
        ttk.Checkbutton(control_frame, text="RTS", variable=self.rts_var, style='Switch.TCheckbutton').pack(side='left', padx=10)
        self.dtr_var = tk.BooleanVar(value=self.app.ptt.use_dtr)
        ttk.Checkbutton(control_frame, text="DTR", variable=self.dtr_var, style='Switch.TCheckbutton').pack(side='left', padx=10)
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill='x', padx=10, pady=10)
        ttk.Button(button_frame, text="保存", command=self.save_settings).pack(side='right', padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.window.destroy).pack(side='right')

    def save_settings(self) -> None:
        try:
            current = self.device_combo.current()
            self.app.device_combo.current(current)
            self.app.device_var.set(self.device_var.get())
        except Exception:
            pass
        self.app.volume_level = self.volume_var.get()
        port_name = self.port_var.get()
        try:
            self.app.ptt.close()
        except Exception:
            pass
        if port_name and port_name != 'なし':
            try:
                self.app.ptt.use_rts = self.rts_var.get()
                self.app.ptt.use_dtr = self.dtr_var.get()
                self.app.ptt.open(port_name)
            except Exception as e:
                messagebox.showerror("エラー", f"PTTポートのオープンに失敗しました: {e}")
        else:
            self.app.ptt.port_name = None
            self.app.ptt.use_rts = False
            self.app.ptt.use_dtr = False
        config = configparser.ConfigParser()
        config['Sound'] = {'device_name': self.device_var.get(), 'volume_level': str(self.volume_var.get())}
        config['PTT'] = {'port_name': (port_name if port_name and port_name != 'なし' else ''), 'use_rts': str(self.rts_var.get()), 'use_dtr': str(self.dtr_var.get())}
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
        self.window.destroy()


class HellschreiberGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("ヘルシュライバー送信機")
        self.volume_level = -20
        toolbar_frame = tk.Frame(root)
        toolbar_frame.pack(fill='x')
        icon_path = Path(os.path.dirname(os.path.abspath(__file__))) / '歯車アイコン.png'
        try:
            self.settings_icon = tk.PhotoImage(file=str(icon_path))
            self.settings_icon = self.settings_icon.subsample(max(1, self.settings_icon.width() // 24), max(1, self.settings_icon.height() // 24))
        except Exception:
            self.settings_icon = None
        self.settings_button = tk.Button(toolbar_frame, image=self.settings_icon, command=self.show_settings, relief='flat', background=root.cget('background'))
        self.settings_button.pack(side='right', padx=5, pady=5)
        try:
            devices = sd.query_devices()
            self.audio_available = True
        except Exception:
            devices = []
            self.audio_available = False
        try:
            hostapis = sd.query_hostapis()
        except Exception:
            hostapis = []
        self.output_devices: List[Tuple[int, DeviceInfo, str]] = []
        for i, device in enumerate(devices):
            try:
                max_out = int(device.get('max_output_channels', 0)) if isinstance(device, dict) else 0
            except Exception:
                max_out = 0
            if max_out > 0 and isinstance(device, dict):
                hostidx = device.get('hostapi') if isinstance(device, dict) else None
                hostname = None
                try:
                    if hostidx is not None and 0 <= int(hostidx) < len(hostapis):
                        hostname = hostapis[int(hostidx)]['name']
                except Exception:
                    hostname = None
                self.output_devices.append((i, DeviceInfo(device), hostname or ""))
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(root, textvariable=self.device_var)
        device_names = [f"{dev[1].name} ({dev[2]})" if dev[2] else f"{dev[1].name}" for dev in self.output_devices]
        self.device_combo['values'] = device_names
        config = configparser.ConfigParser()
        saved_device_name = None
        self.ptt = PTTControl()
        if CONFIG_FILE.exists():
            try:
                config.read(CONFIG_FILE, encoding='utf-8')
                saved_device_name = config.get('Sound', 'device_name', fallback=None)
                self.volume_level = float(config.get('Sound', 'volume_level', fallback='-20'))
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
        if saved_device_name:
            for i, name in enumerate(device_names):
                if name == saved_device_name or name.startswith(saved_device_name):
                    self.device_combo.current(i)
                    break
            else:
                if device_names:
                    self.device_combo.current(0)
        else:
            try:
                if self.audio_available:
                    default_device = sd.default.device[1]
                else:
                    default_device = None
            except Exception:
                default_device = None
            if default_device is not None:
                for i, dev in enumerate(self.output_devices):
                    dev_id = dev[0]
                    if dev_id == default_device:
                        self.device_combo.current(i)
                        break
                else:
                    if device_names:
                        self.device_combo.current(0)
            else:
                if device_names:
                    self.device_combo.current(0)
        default_font = ('Yu Gothic UI', 12)
        tk.Label(root, text="送信テキスト:", font=default_font).pack(anchor='w', padx=10)
        self.input_entry = tk.Entry(root, font=default_font)
        self.input_entry.pack(padx=10, pady=5, fill='x')
        self.send_button = tk.Button(root, text="送信開始", font=default_font, command=self.start_transmission)
        self.send_button.pack(pady=5)
        tk.Label(root, text="送信状況:", font=default_font).pack(anchor='w', padx=10)
        self.output_display = tk.Text(root, height=2, font=default_font, state='disabled', wrap='none')
        self.output_display.pack(padx=10, pady=5, fill='x')
        self.output_display.tag_configure("pending", foreground="gray")
        self.output_display.tag_configure("sent", foreground="red")
        self.audio_stream = None
        self.stream_lock = threading.Lock()
        self.stream_samplerate = SAMPLE_RATE

    def show_settings(self) -> None:
        SettingsWindow(self.root, self)

    def start_transmission(self) -> None:
        text = self.input_entry.get()
        if not text:
            self.send_button.config(state='normal')
            return
        if not getattr(self, 'audio_available', True):
            messagebox.showerror("エラー", "音声デバイスが利用できません。設定を確認してください。")
            return
        device_id = self.get_selected_device_id()
        if device_id is None:
            messagebox.showerror("エラー", "出力デバイスが選択されていません。設定を確認してください。")
            return
        try:
            self._initialize_audio_stream(device_id)
        except Exception as e:
            messagebox.showerror("エラー", f"オーディオストリームの初期化に失敗しました: {e}")
            self.audio_available = False
            return
        self.send_button.config(state='disabled')
        text_with_markers = "...   " + text + "   ..."
        self.output_display.config(state='normal')
        self.output_display.delete("1.0", tk.END)
        self.output_display.insert("1.0", text_with_markers, "pending")
        self.output_display.config(state='disabled')
        threading.Thread(target=self.transmit_text, args=(text_with_markers,), daemon=True).start()

    def get_selected_device_id(self) -> Optional[int]:
        current = self.device_combo.current()
        if current >= 0:
            return self.output_devices[current][0]
        return None

    def _initialize_audio_stream(self, device_id: int) -> None:
        with self.stream_lock:
            try:
                if self.audio_stream is not None:
                    try:
                        self.audio_stream.close()
                    except Exception:
                        pass
                    self.audio_stream = None
                blocksize = SAMPLES_PER_PIXEL
                hostapi_name = None
                try:
                    for dev in getattr(self, 'output_devices', []):
                        if dev[0] == device_id:
                            hostapi_name = dev[2]
                            break
                except Exception:
                    hostapi_name = None
                if hostapi_name and 'DirectSound' in hostapi_name:
                    try:
                        if self.audio_stream is not None:
                            try:
                                self.audio_stream.close()
                            except Exception:
                                pass
                        self.audio_stream = None
                        self.use_sd_play = True
                        self.audio_stream_dtype = 'int16'
                        self.stream_samplerate = SAMPLE_RATE
                        self.audio_available = True
                        return
                    except Exception:
                        self.use_sd_play = False
                self.use_sd_play = False
                try:
                    self.audio_stream = sd.OutputStream(samplerate=SAMPLE_RATE, device=device_id, channels=1, blocksize=blocksize, latency='low', dtype=np.float32)
                    self.audio_stream.start()
                    self.audio_stream_dtype = 'float32'
                except Exception:
                    self.audio_stream = sd.OutputStream(samplerate=SAMPLE_RATE, device=device_id, channels=1, blocksize=blocksize, latency='low', dtype='int16')
                    self.audio_stream.start()
                    self.audio_stream_dtype = 'int16'
                try:
                    self.stream_samplerate = int(getattr(self.audio_stream, 'samplerate', SAMPLE_RATE))
                except Exception:
                    self.stream_samplerate = SAMPLE_RATE
                self.audio_available = True
            except Exception as ex:
                try:
                    if self.audio_stream is not None:
                        self.audio_stream.close()
                except Exception:
                    pass
                self.audio_stream = None
                self.audio_available = False
                raise

    def _prepare_frames_for_stream(self, arr: np.ndarray) -> np.ndarray:
        if arr is None or arr.size == 0:
            return np.zeros((0,1), dtype=np.float32)
        a = arr.astype(np.float32, copy=False)
        np.clip(a, -1.0, 1.0, out=a)
        dtype = getattr(self, 'audio_stream_dtype', 'float32')
        if dtype == 'int16':
            out = (a * 32767.0).astype(np.int16)
        else:
            out = a.astype(np.float32)
        try:
            frames = out.reshape(-1, 1)
        except Exception:
            frames = out.astype(np.float32).reshape(-1, 1)
        return frames

    def _play_via_sd_play(self, arr: np.ndarray) -> None:
        if arr is None or arr.size == 0:
            return
        a = arr.astype(np.float32, copy=False)
        volume_factor = 10 ** (self.volume_level / 20)
        a = a * volume_factor
        try:
            sd.play(a, samplerate=SAMPLE_RATE, device=self.get_selected_device_id())
            sd.wait()
        except Exception as e:
            print(f"sd.play 再生エラー: {e}")
            raise

    def _play_waves(self, waves: List[np.ndarray]) -> None:
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
            frames_all = self._prepare_frames_for_stream(adjusted_wave)
            chunk_size = max(1, SAMPLES_PER_PIXEL * 8)
            with self.stream_lock:
                for i in range(0, frames_all.shape[0], chunk_size):
                    chunk = frames_all[i:i + chunk_size]
                    try:
                        self.audio_stream.write(chunk)
                    except Exception as e:
                        print(f"再生中エラー(write): {e}")
                        self.audio_available = False
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

    def _play_wave(self, wave: np.ndarray) -> None:
        if wave is None or wave.size == 0:
            return
        if not getattr(self, 'audio_available', True):
            raise Exception("音声デバイスが利用できません")
        device_id = self.get_selected_device_id()
        if device_id is None:
            raise Exception("出力デバイスが選択されていません")
        if self.audio_stream is None:
            self._initialize_audio_stream(device_id)
        if self.audio_stream is None:
            raise Exception("音声ストリームの初期化に失敗しました")
        volume_factor = 10 ** (self.volume_level / 20)
        adjusted = wave * volume_factor
        frames_all = self._prepare_frames_for_stream(adjusted)
        chunk_size = max(1, SAMPLES_PER_PIXEL * 8)
        with self.stream_lock:
            for i in range(0, frames_all.shape[0], chunk_size):
                chunk = frames_all[i:i + chunk_size]
                try:
                    self.audio_stream.write(chunk)
                except Exception as e:
                    print(f"再生中エラー(write): {e}")
                    self.audio_available = False
                    messagebox.showerror("エラー", f"再生中にエラーが発生しました: {e}")
                    raise

    def transmit_text(self, text: str) -> None:
        try:
            self.ptt.set_ptt(True)
            time.sleep(LATENCY)
            waves: List[np.ndarray] = []
            durations_samples: List[int] = []
            # まず全文字分の波形を生成（再生中の都度生成コストを削減）
            # ここで文字間ギャップ（無音）を挿入できるようにする
            gap_samples = int(SAMPLE_RATE * (INTER_CHAR_GAP_MS / 1000.0)) if INTER_CHAR_GAP_MS and INTER_CHAR_GAP_MS > 0 else 0
            silence_gap = np.zeros(gap_samples, dtype=np.float32) if gap_samples > 0 else None
            for idx_ch, ch in enumerate(text):
                try:
                    w = send_char(ch)
                except Exception as e:
                    print(f"send_char エラー: {e}")
                    w = np.zeros(SAMPLES_PER_CHAR, dtype=np.float32)
                waves.append(w)
                # duration for marking includes trailing inter-character gap (except after last char)
                dur = w.shape[0]
                if idx_ch != len(text) - 1 and gap_samples > 0:
                    waves.append(silence_gap)
                    dur += gap_samples
                durations_samples.append(dur)
            if not waves:
                return
            # 各文字を送信完了としてマークするタイミングを事前にスケジュール
            cumulative = 0
            for idx, samples in enumerate(durations_samples):
                cumulative += samples
                # 少し余裕を持たせてスケジュール（5ms余裕）
                delay_ms = int((cumulative / float(SAMPLE_RATE)) * 1000.0) + 5
                try:
                    self.root.after(delay_ms, lambda i=idx: self.mark_sent(i))
                except Exception:
                    try:
                        self.mark_sent(idx)
                    except Exception:
                        pass
            try:
                if getattr(self, 'use_sd_play', False):
                    combined = np.concatenate(waves)
                    self._play_via_sd_play(combined)
                else:
                    self._play_waves(waves)
            except Exception as e:
                print(f"再生エラー: {e}")
                messagebox.showerror("エラー", f"再生中にエラーが発生しました: {e}")
        except Exception as e:
            print(f"送信エラー: {e}")
            messagebox.showerror("エラー", f"送信中にエラーが発生しました: {e}")
        finally:
            time.sleep(LATENCY)
            self.ptt.set_ptt(False)
            self.send_button.config(state='normal')

    def mark_sent(self, index: int) -> None:
        try:
            self.output_display.config(state='normal')
            try:
                self.output_display.tag_remove("pending", f"1.{index}", f"1.{index+1}")
                self.output_display.tag_add("sent", f"1.{index}", f"1.{index+1}")
            except tk.TclError:
                pass
            self.output_display.config(state='disabled')
        except Exception:
            pass

    def __del__(self):
        if hasattr(self, 'audio_stream') and self.audio_stream is not None:
            try:
                self.audio_stream.close()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = HellschreiberGUI(root)
        root.mainloop()
    except Exception as e:
        print(f"アプリケーションエラー: {e}")
        try:
            messagebox.showerror("エラー", f"アプリケーションエラー: {e}")
        except Exception:
            pass
