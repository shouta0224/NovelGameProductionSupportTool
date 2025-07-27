import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import uuid
import configparser
import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import List, Dict, Type, Optional, Any, Tuple
import math

# UIテーマライブラリ (pip install sv-ttk)
import sv_ttk

# --- ユーティリティクラス ---
class Tooltip:
    # (変更なし)
    def __init__(self, widget, text):
        self.widget = widget; self.text = text; self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip); self.widget.bind("<Leave>", self.hide_tooltip)
    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert"); x += self.widget.winfo_rootx() + 25; y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tk.Toplevel(self.widget); self.tooltip_window.wm_overrideredirect(True); self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.tooltip_window, text=self.text, justify='left', background="#3c3c3c", foreground="white", relief='solid', borderwidth=1, padding=(5, 3)); label.pack(ipadx=1)
    def hide_tooltip(self, event=None):
        if self.tooltip_window: self.tooltip_window.destroy()
        self.tooltip_window = None

class ShortcutEntry(ttk.Entry):
    # (変更なし)
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs); self.bind("<KeyPress>", self._on_key_press); self.bind("<KeyRelease>", self._on_key_release); self.pressed_keys = set()
    def _on_key_press(self, event):
        self.delete(0, tk.END)
        key_name = event.keysym.upper()
        if key_name in self.pressed_keys: return "break"
        self.pressed_keys.add(key_name)
        modifiers = []
        if event.state & 4: modifiers.append("Control")
        if event.state & 1: modifiers.append("Shift")
        if event.keysym in ('Alt_L', 'Alt_R') or (event.state & 8 or event.state & 131072):
            if 'Alt' not in modifiers: modifiers.append("Alt")
        if key_name in ["CONTROL_L", "CONTROL_R", "SHIFT_L", "SHIFT_R", "ALT_L", "ALT_R", "CAPS_LOCK"]: return "break"
        key_map = {"PLUS": "plus", "MINUS": "minus", "EQUAL": "plus"}; key_name = key_map.get(key_name, key_name)
        shortcut_parts = sorted(modifiers) + [key_name]; shortcut_str = "-".join(shortcut_parts)
        self.insert(0, shortcut_str); return "break"
    def _on_key_release(self, event):
        key_name = event.keysym.upper()
        if key_name in self.pressed_keys: self.pressed_keys.remove(key_name)
        return "break"

class TextWithLineNumbers(tk.Frame):
    # (変更なし)
    def __init__(self, master, **kwargs):
        super().__init__(master); self.font = kwargs.get("font") or ("TkDefaultFont", 10)
        self.linenumbers = tk.Canvas(self, width=40, bg='#404040', highlightthickness=0); self.linenumbers.pack(side=tk.LEFT, fill=tk.Y)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL); self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        kwargs['yscrollcommand'] = self._on_text_scroll; self.text = tk.Text(self, relief=tk.FLAT, **kwargs); self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.text.yview); self.text.bind("<<Modified>>", self._schedule_update); self.text.bind("<Configure>", self._schedule_update); self._update_job = None
    def _on_text_scroll(self, first, last): self.scrollbar.set(first, last); self.linenumbers.yview_moveto(first); self._schedule_update()
    def _schedule_update(self, event=None):
        if self._update_job: self.after_cancel(self._update_job)
        self._update_job = self.after(10, self._update_line_numbers)
    def _update_line_numbers(self):
        self._update_job = None
        if not self.winfo_exists(): return
        self.linenumbers.delete("all"); i = self.text.index("@0,0")
        while True:
            dline = self.text.dlineinfo(i)
            if dline is None: break
            y_coord = dline[1]; line_num_str = str(i).split(".")[0]
            self.linenumbers.create_text(38, y_coord, anchor="ne", text=line_num_str, fill="#9E9E9E", font=self.font); i = self.text.index(f"{i}+1line")
    def __getattr__(self, name):
        try: return getattr(self.text, name)
        except AttributeError: raise AttributeError(f"'{type(self).__name__}' object (or its internal Text widget) has no attribute '{name}'")

# --- プラグイン関連 ---
class IPlugin:
    # (変更なし)
    def __init__(self, app: 'NovelGameEditor'): self.app = app
    def setup(self) -> None: pass
    def register(self) -> None: pass
    def teardown(self) -> None: pass
class PluginManager:
    # (変更なし)
    def __init__(self, app: 'NovelGameEditor'):
        self.app = app; self.plugins: Dict[str, IPlugin] = {}
        if getattr(sys, 'frozen', False): script_dir = Path(sys.executable).parent
        else:
            try: script_dir = Path(__file__).resolve().parent
            except NameError: script_dir = Path.cwd()
        if str(script_dir) not in sys.path: sys.path.insert(0, str(script_dir))
        self.plugin_dir = script_dir / "plugins"; print(f"[プラグインマネージャ] プラグインディレクトリ: '{self.plugin_dir}'"); self.plugin_dir.mkdir(exist_ok=True)
    def discover_plugins(self) -> List[str]:
        print(f"[プラグインマネージャ] '{self.plugin_dir}' 内のプラグインを探索中...");
        if not self.plugin_dir.exists(): print(f"[プラグインマネージャ] ディレクトリが見つかりません。"); return []
        plugin_files = list(self.plugin_dir.glob("*.py")); print(f"[プラグインマネージャ] 発見したPythonファイル: {[f.name for f in plugin_files]}")
        found_plugins = [f.stem for f in plugin_files if f.is_file() and not f.name.startswith("_")]; print(f"[プラグインマネージャ] ロード対象プラグイン: {found_plugins}"); return found_plugins
    def load_plugin(self, plugin_name: str) -> bool:
        if not self.app.config_manager.is_plugin_enabled(plugin_name):
            print(f"プラグイン '{plugin_name}' は設定で無効化されています。スキップします。")
            return False
        if plugin_name in self.plugins: return False
        try:
            sys.path.insert(0, str(self.plugin_dir)); module = importlib.import_module(plugin_name); sys.path.pop(0)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, IPlugin) and obj != IPlugin and obj.__module__ == plugin_name:
                    plugin_instance = obj(self.app); plugin_instance.setup(); plugin_instance.register(); self.plugins[plugin_name] = plugin_instance; print(f"プラグイン '{plugin_name}' をロードしました。"); return True
        except Exception as e:
            print(f"プラグイン '{plugin_name}' のロード中にエラーが発生しました: {e}")
            if plugin_name in sys.modules: del sys.modules[plugin_name]
        return False
    def unload_plugin(self, plugin_name: str) -> bool:
        if plugin_name not in self.plugins: return False
        try:
            self.plugins[plugin_name].teardown(); del self.plugins[plugin_name]
            if plugin_name in sys.modules: del sys.modules[plugin_name]
            print(f"プラグイン '{plugin_name}' をアンロードしました。"); return True
        except Exception as e: print(f"プラグイン '{plugin_name}' のアンロード中にエラーが発生しました: {e}"); return False

# --- 設定管理 ---
class ConfigManager:
    # (変更なし)
    def __init__(self):
        self.config = configparser.ConfigParser();self.config_file = Path("config.ini");self._load_config()
    def _load_config(self) -> None:
        self.config.read(self.config_file, encoding='utf-8')
        default_shortcuts = {'new_project': 'Control-N', 'open_project': 'Control-O', 'save_project': 'Control-S', 'save_project_as': 'Control-Shift-S', 'add_scene': 'Control-A', 'add_branch': 'Control-B', 'zoom_in': 'Control-plus','zoom_out': 'Control-minus', 'reset_view': 'Control-0'}
        if not self.config.has_section('SHORTCUTS'): self.config.add_section('SHORTCUTS')
        for key, value in default_shortcuts.items():
            if not self.config.has_option('SHORTCUTS', key): self.config.set('SHORTCUTS', key, value)
        if not self.config.has_section('RECENT_FILES'): self.config.add_section('RECENT_FILES')
        self._save_config()
    def _save_config(self) -> None:
        with open(self.config_file, 'w', encoding='utf-8') as f: self.config.write(f)
    def get_shortcut(self, action: str) -> str: return self.config.get('SHORTCUTS', action, fallback='')
    def set_shortcut(self, action: str, shortcut: str) -> None:
        if not self.config.has_section('SHORTCUTS'): self.config.add_section('SHORTCUTS')
        self.config.set('SHORTCUTS', action, shortcut);self._save_config()
    def get_shortcut_display(self, action: str) -> str: return self.get_shortcut(action).replace('-', '+')
    def get_recent_files(self) -> List[Path]:
        if not self.config.has_section('RECENT_FILES'): return []
        paths = []
        for _, path_str in self.config.items('RECENT_FILES'):
            path = Path(path_str)
            if path.exists(): paths.append(path)
        return paths
    def add_recent_file(self, path: Path):
        if not self.config.has_section('RECENT_FILES'): self.config.add_section('RECENT_FILES')
        recent_files = self.get_recent_files()
        if path in recent_files: recent_files.remove(path)
        recent_files.insert(0, path)
        for key in self.config.options('RECENT_FILES'): self.config.remove_option('RECENT_FILES', key)
        for i, p in enumerate(recent_files[:5]): self.config.set('RECENT_FILES', f'file_{i}', str(p))
        self._save_config()
    def _ensure_plugin_section(self):
        if not self.config.has_section('PLUGINS'): self.config.add_section('PLUGINS')
    def is_plugin_enabled(self, plugin_name: str) -> bool:
        self._ensure_plugin_section()
        return self.config.getboolean('PLUGINS', plugin_name, fallback=True)
    def set_plugin_enabled(self, plugin_name: str, enabled: bool):
        self._ensure_plugin_section()
        self.config.set('PLUGINS', plugin_name, 'true' if enabled else 'false'); self._save_config()

# --- データ構造 ---
class Scene:
    # (変更なし)
    def __init__(self, name: str = "New Scene", content: str = "", x: float = 0.0, y: float = 0.0): self.id = str(uuid.uuid4());self.name = name;self.content = content;self.x = float(x);self.y = float(y);self.branches: List[Dict[str, str]] = []
    def add_branch(self, text: str, target: str, condition: str = "") -> None: self.branches.append({"text": text, "target": target, "condition": condition})
    def to_dict(self) -> Dict[str, Any]: return {"id": self.id, "name": self.name, "content": self.content, "x": self.x, "y": self.y, "branches": self.branches}
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scene':
        scene = cls(data.get("name", "Unnamed Scene"), data.get("content", ""), data.get("x", 0.0), data.get("y", 0.0));scene.id = data.get("id", str(uuid.uuid4()));scene.branches = data.get("branches", []);return scene

# --- UIダイアログ ---
class SettingsDialog(tk.Toplevel):
    # (変更なし)
    def __init__(self, parent, config_manager: ConfigManager):
        super().__init__(parent);self.title("設定");self.config_manager = config_manager;self.transient(parent);self.grab_set();self.shortcut_entry_widgets = {};self._create_widgets();self.resizable(False, False);self.wait_window(self)
    def _create_widgets(self) -> None:
        main_frame = ttk.Frame(self, padding="10");main_frame.pack(fill=tk.BOTH, expand=True);ttk.Label(main_frame, text="ショートカットキー設定", font="-weight bold").grid(row=0, column=0, columnspan=2, pady=10)
        shortcut_actions = {'new_project': "新規プロジェクト", 'open_project': "プロジェクトを開く", 'save_project': "プロジェクトを保存", 'save_project_as': "名前を付けて保存", 'add_scene': "シーンを追加", 'add_branch': "分岐を追加", 'zoom_in': "ズームイン", 'zoom_out': "ズームアウト", 'reset_view': "ビューをリセット"}
        for i, (action_key, action_label) in enumerate(shortcut_actions.items(), 1):
            ttk.Label(main_frame, text=f"{action_label}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2);entry = ShortcutEntry(main_frame, width=30);entry.grid(row=i, column=1, padx=5, pady=2);entry.insert(0, self.config_manager.get_shortcut(action_key));self.shortcut_entry_widgets[action_key] = entry
        button_frame = ttk.Frame(main_frame);button_frame.grid(row=len(shortcut_actions) + 1, column=0, columnspan=2, pady=15);ttk.Button(button_frame, text="保存", command=self._save_settings).pack(side=tk.LEFT, padx=5);ttk.Button(button_frame, text="キャンセル", command=self.destroy).pack(side=tk.LEFT, padx=5)
    def _save_settings(self) -> None:
        for action_key, entry_widget in self.shortcut_entry_widgets.items(): self.config_manager.set_shortcut(action_key, entry_widget.get().strip())
        if hasattr(self.master, 'setup_shortcuts'): self.master.setup_shortcuts()
        messagebox.showinfo("設定完了", "ショートカットキー設定を保存しました。", parent=self); self.destroy()

class SceneSelectionDialog(tk.Toplevel):
    ### BUG FIX 4: シーン名が重複している場合に、意図しないシーンが選択される問題を修正
    def __init__(self, parent, scenes: List[Scene], title="シーンを選択"):
        super().__init__(parent); self.title(title); self.transient(parent); self.grab_set(); self.result: Optional[str] = None; self.scenes = scenes
        self.listbox_scenes: List[Scene] = []  # 表示されているシーンオブジェクトを順番に保持
        self._create_widgets(); self._update_listbox(); self.resizable(False, False); self.wait_window(self)
    
    def _create_widgets(self):
        # (変更なし)
        frame = ttk.Frame(self, padding="10"); frame.pack(fill=tk.BOTH, expand=True)
        self.search_var = tk.StringVar(); self.search_var.trace_add("write", self._on_search)
        search_entry = ttk.Entry(frame, textvariable=self.search_var); search_entry.pack(fill=tk.X, padx=5, pady=5); search_entry.focus_set()
        self.listbox = tk.Listbox(frame, height=15); self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.listbox.bind("<Double-Button-1>", self._on_ok); self.listbox.bind("<Return>", self._on_ok)
        btn_frame = ttk.Frame(frame); btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="キャンセル", command=self.destroy).pack(side=tk.LEFT, expand=True, fill=tk.X)
    
    def _on_search(self, *args): self._update_listbox()
    
    def _update_listbox(self):
        self.listbox.delete(0, tk.END)
        self.listbox_scenes.clear() # リストをクリア
        search_term = self.search_var.get().lower()
        for scene in self.scenes:
            if search_term in scene.name.lower():
                self.listbox.insert(tk.END, scene.name)
                self.listbox_scenes.append(scene) # 表示するシーンオブジェクトをリストに追加
    
    def _on_ok(self, event=None):
        selected_indices = self.listbox.curselection()
        if not selected_indices: return
        
        selected_index = selected_indices[0]
        # 保存しておいたリストからインデックスでシーンを取得することで、同名シーンがあっても正しく選択できる
        if 0 <= selected_index < len(self.listbox_scenes):
            selected_scene = self.listbox_scenes[selected_index]
            self.result = selected_scene.id
            self.destroy()

class BranchDialog(tk.Toplevel):
    ### BUG FIX 3: `app`インスタンスを直接受け取るように修正
    def __init__(self, parent, title, all_scenes, source_scene, app: 'NovelGameEditor', initial_text="", initial_target_id="", initial_condition=""):
        super().__init__(parent);self.title(title);self.transient(parent);self.grab_set();self.result = None
        self.all_scenes = all_scenes; self.source_scene = source_scene; self.target_id = initial_target_id
        self.app = app # appインスタンスを保持
        self._create_widgets(initial_text, initial_condition);self.resizable(False, False);self.wait_window(self)

    def _create_widgets(self, initial_text, initial_condition):
        # (変更なし)
        frame = ttk.Frame(self, padding="15");frame.pack(fill=tk.BOTH, expand=True);frame.columnconfigure(1, weight=1);ttk.Label(frame, text="選択肢テキスト:").grid(row=0, column=0, sticky="w", padx=5, pady=5);self.text_entry = ttk.Entry(frame, width=40);self.text_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=5, pady=5);self.text_entry.insert(0, initial_text);self.text_entry.focus_set()
        ttk.Label(frame, text="遷移先シーン:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.target_scene_var = tk.StringVar()
        target_scene = next((s for s in self.all_scenes if s.id == self.target_id), None)
        if target_scene: self.target_scene_var.set(target_scene.name)
        target_entry = ttk.Entry(frame, textvariable=self.target_scene_var, state="readonly"); target_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(frame, text="選択...", command=self._select_scene).grid(row=1, column=2, padx=5)
        ttk.Label(frame, text="条件 (任意):").grid(row=2, column=0, sticky="w", padx=5, pady=5);self.condition_entry = ttk.Entry(frame, width=40);self.condition_entry.grid(row=2, column=1, columnspan=2, sticky="ew", padx=5, pady=5);self.condition_entry.insert(0, initial_condition)
        btn_frame = ttk.Frame(frame);btn_frame.grid(row=3, column=0, columnspan=3, pady=(15, 0));ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=5);ttk.Button(btn_frame, text="キャンセル", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def _select_scene(self):
        available_scenes = [s for s in self.all_scenes if s.id != self.source_scene.id]
        if not available_scenes:
            if messagebox.askyesno("確認", "遷移可能なシーンがありません。\n新しいシーンを作成して遷移先にしますか？", parent=self):
                # self.master.app ではなく、保持している self.app を使う
                new_scene = self.app.add_scene(return_scene=True)
                if new_scene: self.target_id = new_scene.id; self.target_scene_var.set(new_scene.name)
            return
        dialog = SceneSelectionDialog(self, available_scenes)
        if dialog.result:
            self.target_id = dialog.result
            selected_scene = next((s for s in self.all_scenes if s.id == self.target_id), None)
            if selected_scene: self.target_scene_var.set(selected_scene.name)
    
    def _on_ok(self):
        # (変更なし)
        text = self.text_entry.get().strip()
        if not text: messagebox.showerror("エラー", "選択肢テキストを入力してください。", parent=self); return
        if not self.target_id: messagebox.showerror("エラー", "遷移先シーンを選択してください。", parent=self); return
        self.result = {"text": text, "target": self.target_id, "condition": self.condition_entry.get().strip()}; self.destroy()

class PluginManagementDialog(tk.Toplevel):
    # (変更なし)
    def __init__(self, parent, plugin_manager: PluginManager, config_manager: ConfigManager):
        super().__init__(parent)
        self.plugin_manager = plugin_manager; self.config_manager = config_manager; self.title("プラグイン管理")
        self.transient(parent); self.grab_set(); self.plugin_vars: Dict[str, tk.BooleanVar] = {}; self._create_widgets()
        self.resizable(False, False); self.wait_window(self)
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15"); main_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main_frame, text="インストール済みプラグイン:", font="-weight bold").pack(anchor="w", pady=(0, 10))
        all_plugins = self.plugin_manager.discover_plugins()
        if not all_plugins: ttk.Label(main_frame, text="プラグインが見つかりません。").pack()
        else:
            for plugin_name in sorted(all_plugins):
                is_enabled = self.config_manager.is_plugin_enabled(plugin_name); var = tk.BooleanVar(value=is_enabled)
                self.plugin_vars[plugin_name] = var; cb = ttk.Checkbutton(main_frame, text=plugin_name, variable=var); cb.pack(anchor="w", padx=10)
        info_label = ttk.Label(main_frame, text="変更を反映するには、アプリケーションの再起動が必要です。", foreground="orange"); info_label.pack(pady=(20, 10))
        button_frame = ttk.Frame(main_frame); button_frame.pack(pady=(5, 0))
        ttk.Button(button_frame, text="保存して閉じる", command=self._save_and_close).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.destroy).pack(side=tk.LEFT, padx=5)
    def _save_and_close(self):
        for plugin_name, var in self.plugin_vars.items(): self.config_manager.set_plugin_enabled(plugin_name, var.get())
        messagebox.showinfo("設定保存完了", "プラグイン設定を保存しました。\n変更を完全に反映するには、アプリケーションを再起動してください。", parent=self); self.destroy()

# --- メインアプリケーションクラス ---
class NovelGameEditor:
    NODE_RADIUS = 35
    DRAG_THRESHOLD_SQUARED = 5*5 # 5ピクセル
    def __init__(self, root: tk.Tk):
        self.root = root;self.root.title("ノベルゲーム制作支援ツール");self.root.geometry("1280x800")
        self.config_manager = ConfigManager();self.pluggable_data_keys: Dict[str, Any] = {};self.project_data: Dict[str, Any] = {};self.scenes: List[Scene] = []
        self.plugin_manager = PluginManager(self);self.current_project_path: Optional[Path] = None;self.selected_scene: Optional[Scene] = None
        self.is_dirty = False;self.scale = 1.0;self.view_offset_x = 0.0;self.view_offset_y = 0.0;self.drag_state = {};self.menubar = tk.Menu(self.root);self.plugin_menu: Optional[tk.Menu] = None
        self.recent_files_menu: Optional[tk.Menu] = None
        self.bound_shortcuts: List[str] = [] ### BUG FIX 1: バインドされたショートカットを追跡するリスト
        self._create_widgets();self._bind_events();self.setup_shortcuts();self._load_plugins();self.new_project(startup=True);self._update_status_bar()

    def _show_plugin_management(self):
        PluginManagementDialog(self.root, self.plugin_manager, self.config_manager)
    
    def _create_widgets(self):
        # (変更なし)
        self.root.config(menu=self.menubar);self._create_menu()
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL);main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        canvas_frame = ttk.Frame(main_paned);self.canvas = tk.Canvas(canvas_frame, bg="#333333", highlightthickness=0);self.canvas.pack(fill=tk.BOTH, expand=True);main_paned.add(canvas_frame, weight=3)
        editor_frame = ttk.Frame(main_paned);self._create_editor_widgets(editor_frame);main_paned.add(editor_frame, weight=1)
        self.status_bar = ttk.Label(self.root, text="準備完了", anchor=tk.W, padding=(5, 2));self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _create_menu(self):
        # (変更なし)
        self.menubar.delete(0, tk.END)
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label="新規", command=self.new_project)
        self.file_menu.add_command(label="開く...", command=self.open_project)
        self.recent_files_menu = tk.Menu(self.file_menu, tearoff=0)
        self.file_menu.add_cascade(label="最近使ったプロジェクトを開く", menu=self.recent_files_menu)
        self.file_menu.add_command(label="保存", command=self.save_project)
        self.file_menu.add_command(label="名前を付けて保存...", command=self.save_project_as)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="設定...", command=self._show_settings)
        self.file_menu.add_separator()
        theme_menu = tk.Menu(self.file_menu, tearoff=0)
        theme_menu.add_command(label="ダークテーマ", command=lambda: self.set_theme("dark"))
        theme_menu.add_command(label="ライトテーマ", command=lambda: self.set_theme("light"))
        self.file_menu.add_cascade(label="テーマ", menu=theme_menu)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="終了", command=self._on_closing)
        self.menubar.add_cascade(label="ファイル", menu=self.file_menu)
        self.edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.edit_menu.add_command(label="シーンを追加", command=self.add_scene)
        self.edit_menu.add_command(label="選択中のシーンを削除", command=self.delete_scene, accelerator="Delete")
        self.menubar.add_cascade(label="編集", menu=self.edit_menu)
        self.plugin_menu = tk.Menu(self.menubar, tearoff=0)
        self.plugin_menu.add_command(label="プラグイン管理...", command=self._show_plugin_management)
        self.menubar.add_cascade(label="プラグイン", menu=self.plugin_menu, state="disabled")
        self._update_recent_files_menu()
    
    def _update_menu_accelerators(self):
        # (変更なし)
        self.file_menu.entryconfig("新規", accelerator=self.config_manager.get_shortcut_display('new_project'))
        self.file_menu.entryconfig("開く...", accelerator=self.config_manager.get_shortcut_display('open_project'))
        self.file_menu.entryconfig("保存", accelerator=self.config_manager.get_shortcut_display('save_project'))
        self.file_menu.entryconfig("名前を付けて保存...", accelerator=self.config_manager.get_shortcut_display('save_project_as'))
        self.edit_menu.entryconfig("シーンを追加", accelerator=self.config_manager.get_shortcut_display('add_scene'))
    
    def _create_editor_widgets(self, parent_frame):
        # (変更なし)
        self.editor_notebook = ttk.Notebook(parent_frame)
        self.editor_notebook.pack(fill=tk.BOTH, expand=True)
        scene_tab_pane = ttk.PanedWindow(self.editor_notebook, orient=tk.VERTICAL)
        self.editor_notebook.add(scene_tab_pane, text="シーン/分岐")
        scene_info_frame = ttk.LabelFrame(scene_tab_pane, text="シーン情報", padding=10)
        scene_info_frame.columnconfigure(1, weight=1); scene_info_frame.rowconfigure(2, weight=1)
        ttk.Label(scene_info_frame, text="シーン名:").grid(row=0, column=0, sticky="w", pady=2)
        self.scene_name_entry = ttk.Entry(scene_info_frame)
        self.scene_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.scene_name_entry.bind("<FocusOut>", self._on_scene_data_changed)
        self.scene_name_entry.bind("<Return>", self._on_scene_data_changed)
        self.scene_name_entry.bind("<KeyRelease>", self._on_editor_modified)
        self.editor_plugin_frame = ttk.Frame(scene_info_frame)
        self.editor_plugin_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0), padx=5)
        ttk.Label(scene_info_frame, text="内容:").grid(row=2, column=0, sticky="nw", pady=(5,2))
        self.scene_content_text = TextWithLineNumbers(scene_info_frame, wrap=tk.WORD, height=10)
        self.scene_content_text.grid(row=2, column=1, sticky="nsew", padx=5, pady=2)
        self.scene_content_text.bind("<FocusOut>", self._on_scene_data_changed)
        self.text_info_label = ttk.Label(scene_info_frame, text="文字数: 0 | 行数: 1")
        self.text_info_label.grid(row=3, column=1, sticky="e", padx=5)
        self.scene_content_text.text.bind("<<Modified>>", self._update_text_info, add=True)
        scene_tab_pane.add(scene_info_frame, weight=2)
        branch_frame = ttk.LabelFrame(scene_tab_pane, text="分岐管理", padding=10)
        branch_frame.rowconfigure(0, weight=1); branch_frame.columnconfigure(0, weight=1)
        columns = ("text", "target", "condition")
        self.branch_tree = ttk.Treeview(branch_frame, columns=columns, show="headings", height=5)
        self.branch_tree.heading("text", text="選択肢"); self.branch_tree.heading("target", text="遷移先"); self.branch_tree.heading("condition", text="条件")
        self.branch_tree.column("text", width=120, anchor='w'); self.branch_tree.column("target", width=100, anchor='w'); self.branch_tree.column("condition", width=120, anchor='w')
        self.branch_tree.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.branch_tree.bind('<<TreeviewSelect>>', self._update_branch_buttons_state)
        self.branch_tree.bind('<Double-1>', self.edit_branch)
        branch_btn_frame = ttk.Frame(branch_frame)
        branch_btn_frame.grid(row=1, column=0, columnspan=3, sticky="w", pady=(5,0))
        self.add_branch_btn = ttk.Button(branch_btn_frame, text="追加", command=self.add_branch, width=8)
        self.add_branch_btn.pack(side=tk.LEFT, padx=2)
        self.edit_branch_btn = ttk.Button(branch_btn_frame, text="編集", command=self.edit_branch, width=8)
        self.edit_branch_btn.pack(side=tk.LEFT, padx=2)
        self.delete_branch_btn = ttk.Button(branch_btn_frame, text="削除", command=self.delete_branch, width=8)
        self.delete_branch_btn.pack(side=tk.LEFT, padx=2)
        scene_tab_pane.add(branch_frame, weight=1)
        Tooltip(self.add_branch_btn, f"分岐を追加 ({self.config_manager.get_shortcut_display('add_branch')})")
        Tooltip(self.edit_branch_btn, "選択した分岐を編集 (ダブルクリック)")
        Tooltip(self.delete_branch_btn, "選択した分岐を削除 (Delete)")

    def _bind_events(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self._on_canvas_double_click)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)
        ### BUG FIX 2: マウスホイールイベントを一つのハンドラに統合
        self.canvas.bind("<MouseWheel>", self._on_mousewheel_combined) # for Windows/macOS
        self.canvas.bind("<Button-4>", self._on_mousewheel_combined) # for Linux (scroll up)
        self.canvas.bind("<Button-5>", self._on_mousewheel_combined) # for Linux (scroll down)
        self.root.bind("<Delete>", self._on_delete_key_pressed)
    
    def register_data_key(self, key: str, default_value: Any):
        # (変更なし)
        if key in self.pluggable_data_keys or key == "scenes": print(f"警告: データキー '{key}' は既に登録済みか、予約されています。"); return
        print(f"[データ] プラグイン用データキー '{key}' をデフォルト値 '{default_value}' で登録しました。"); self.pluggable_data_keys[key] = default_value
    
    def _on_canvas_press(self, event):
        self.canvas.focus_set(); self.canvas.scan_mark(event.x, event.y)
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y); clicked_node_id = self._get_node_id_at(cx, cy)
        if clicked_node_id:
            scene = self.get_scene_by_id(clicked_node_id)
            if scene:
                self.drag_state = {
                    "type": "node", "item_id": clicked_node_id,
                    "start_x_canvas": cx, "start_y_canvas": cy, "last_x_canvas": cx, "last_y_canvas": cy, # キャンバス座標
                    "start_x_screen": event.x, "start_y_screen": event.y, # ### UX IMPROVEMENT: スクリーン座標も保持
                    "original_x_world": scene.x, "original_y_world": scene.y, # ワールド座標
                    "moved": False
                }
        else:
            self.drag_state = {
                "type": "pan", "start_x_screen": event.x, "start_y_screen": event.y, "moved": False
            }
    
    def _on_canvas_drag(self, event):
        if not self.drag_state: return

        ### UX IMPROVEMENT: 一定距離をドラッグした場合にのみ "moved" フラグを立てる
        if not self.drag_state.get("moved"):
            dist_sq = (event.x - self.drag_state["start_x_screen"])**2 + (event.y - self.drag_state["start_y_screen"])**2
            if dist_sq >= self.DRAG_THRESHOLD_SQUARED:
                self.drag_state["moved"] = True
            else:
                return # 閾値未満なら何もしない

        drag_type = self.drag_state.get("type")
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if drag_type == "node":
            dx = cx - self.drag_state["last_x_canvas"]; dy = cy - self.drag_state["last_y_canvas"]
            self.canvas.move(f"node_{self.drag_state['item_id']}", dx, dy)
            self.drag_state["last_x_canvas"], self.drag_state["last_y_canvas"] = cx, cy
        elif drag_type == "pan":
            self.canvas.scan_dragto(event.x, event.y, gain=1)
    
    def _on_canvas_release(self, event):
        if not self.drag_state: return
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if not self.drag_state.get("moved"):
            if self.drag_state.get("type") == "node": self.select_scene(self.get_scene_by_id(self.drag_state["item_id"]))
            elif self.drag_state.get("type") == "pan": self.select_scene(None)
        elif self.drag_state.get("type") == "node":
            scene = self.get_scene_by_id(self.drag_state["item_id"])
            if scene:
                total_dx_canvas = cx - self.drag_state["start_x_canvas"]
                total_dy_canvas = cy - self.drag_state["start_y_canvas"]
                scene.x = self.drag_state["original_x_world"] + (total_dx_canvas / self.scale)
                scene.y = self.drag_state["original_y_world"] + (total_dy_canvas / self.scale)
                self._mark_dirty(); self._redraw_canvas()
        self.drag_state = {}
    
    def _on_canvas_double_click(self, event):
        # (変更なし)
        if self.selected_scene: self.scene_name_entry.focus_set(); self.scene_name_entry.selection_range(0, tk.END)
    
    def _on_canvas_right_click(self, event):
        # (変更なし)
        context_menu = tk.Menu(self.root, tearoff=0); cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y); clicked_node_id = self._get_node_id_at(cx, cy)
        if clicked_node_id:
            scene = self.get_scene_by_id(clicked_node_id)
            if scene and scene != self.selected_scene: self.select_scene(scene)
            context_menu.add_command(label=f"シーン '{scene.name}' を削除", command=self.delete_scene); context_menu.add_separator()
        context_menu.add_command(label="ここにシーンを追加", command=lambda: self.add_scene(at_canvas_pos=(cx, cy))); context_menu.add_command(label="ビューをリセット", command=self.reset_view)
        try: context_menu.tk_popup(event.x_root, event.y_root)
        finally: context_menu.grab_release()

    ### BUG FIX 2: 統合されたマウスホイールイベントハンドラ
    def _on_mousewheel_combined(self, event):
        is_control_pressed = (event.state & 0x4)
        is_shift_pressed = (event.state & 0x1)

        # Linuxではevent.deltaがなく、event.num (4 or 5) を使う
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            direction = 1 # 上/拡大
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            direction = -1 # 下/縮小
        else:
            return

        if is_control_pressed:
            factor = 1.1 if direction > 0 else 1/1.1
            self._zoom(factor, event.x, event.y)
        elif is_shift_pressed:
            self.canvas.xview_scroll(-1 * direction, "units")
        else:
            self.canvas.yview_scroll(-1 * direction, "units")
            
    def _get_node_id_at(self, x: float, y: float) -> Optional[str]:
        # (変更なし)
        items = self.canvas.find_overlapping(x - 2, y - 2, x + 2, y + 2)
        for item in reversed(items):
            tags = self.canvas.gettags(item)
            if "node" in tags:
                for tag in tags:
                    if tag.startswith("node_"): return tag.split("_")[1]
        return None
    
    def select_scene(self, scene: Optional[Scene]):
        # (変更なし)
        if self.selected_scene == scene: return
        self._save_current_scene_data(); self.selected_scene = scene; self._update_editor_ui_state(); self._redraw_canvas()
    
    def add_plugin_menu_command(self, label: str, command: callable):
        # (変更なし)
        if not self.plugin_menu: return
        self.menubar.entryconfig("プラグイン", state="normal"); self.plugin_menu.add_command(label=label, command=command)
    
    def remove_plugin_menu_command(self, label: str):
        # (変更なし)
        if not self.plugin_menu: return
        try:
            self.plugin_menu.delete(label)
            if self.plugin_menu.index("end") is None: self.menubar.entryconfig("プラグイン", state="disabled")
        except tk.TclError: pass
    
    def _on_editor_modified(self, event=None):
        # (変更なし)
        self._mark_dirty()
        
    def _on_scene_data_changed(self, event=None):
        # (変更なし)
        if not self.selected_scene: return
        name_changed = self.scene_name_entry.get() != self.selected_scene.name
        content_changed = self.scene_content_text.get("1.0", tk.END).strip() != self.selected_scene.content
        if name_changed or content_changed:
            self._save_current_scene_data()
            self._update_editor_ui_state() # シーン名変更を即座にUIに反映
            self._redraw_canvas()
            self._mark_dirty()

    def _save_current_scene_data(self):
        # (変更なし)
        if not self.selected_scene: return
        self.selected_scene.name = self.scene_name_entry.get()
        self.selected_scene.content = self.scene_content_text.get("1.0", tk.END).strip()
    
    def _mark_dirty(self, dirty=True):
        # (変更なし)
        if self.is_dirty == dirty: return
        self.is_dirty = dirty
        title = self.root.title()
        if dirty and not title.endswith(" *"):
            self.root.title(title + " *")
        elif not dirty and title.endswith(" *"):
            self.root.title(title[:-2])
    
    def set_theme(self, theme_name: str):
        # (変更なし)
        sv_ttk.set_theme(theme_name)
        self.canvas.config(bg="#333333" if theme_name == "dark" else "#F0F0F0")
        self._redraw_canvas()
    
    def _world_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        # (変更なし)
        return (x + self.view_offset_x) * self.scale, (y + self.view_offset_y) * self.scale
    
    def _screen_to_world(self, x: float, y: float) -> Tuple[float, float]:
        # (変更なし)
        return (x / self.scale) - self.view_offset_x, (y / self.scale) - self.view_offset_y
    
    def _redraw_canvas(self):
        # (変更なし)
        self.canvas.delete("all")
        self._draw_branches()
        self._draw_nodes()
        self.canvas.tag_raise("selected")
        self._update_status_bar()
    
    def _draw_nodes(self):
        # (変更なし)
        for scene in self.scenes:
            sx, sy = self._world_to_screen(scene.x, scene.y); radius = self.NODE_RADIUS * self.scale
            is_selected = self.selected_scene and self.selected_scene.id == scene.id
            common_tag = f"node_{scene.id}"; tags = ("node", common_tag)
            if is_selected: tags += ("selected",)
            fill_color = "#4E6A85" if is_selected else "#6C757D"; outline_color = "#87CEFA" if is_selected else "#ADB5BD"
            outline_width = 3 * self.scale if is_selected else 1.5 * self.scale
            text_fill = "#FFFF80" if is_selected else "white"; font_style = "bold" if is_selected else "normal"
            font_size = max(8, int(10 * self.scale)); font = ("Arial", font_size, font_style)
            self.canvas.create_oval(sx - radius, sy - radius, sx + radius, sy + radius, fill=fill_color, outline=outline_color, width=outline_width, tags=tags)
            self.canvas.create_text(sx, sy, text=scene.name, fill=text_fill, font=font, tags=tags)
    
    def _draw_branches(self):
        # (変更なし)
        scene_map = {s.id: s for s in self.scenes}
        for scene in self.scenes:
            for branch in scene.branches:
                target_scene = scene_map.get(branch["target"])
                if not target_scene: continue
                start_x, start_y, end_x, end_y = scene.x, scene.y, target_scene.x, target_scene.y
                dx, dy, dist = end_x - start_x, end_y - start_y, math.hypot(end_x - start_x, end_y - start_y)
                if dist == 0: continue
                start_offset_x, start_offset_y = start_x + (dx / dist) * self.NODE_RADIUS, start_y + (dy / dist) * self.NODE_RADIUS
                end_offset_x, end_offset_y = end_x - (dx / dist) * self.NODE_RADIUS, end_y - (dy / dist) * self.NODE_RADIUS
                s_start_x, s_start_y = self._world_to_screen(start_offset_x, start_offset_y)
                s_end_x, s_end_y = self._world_to_screen(end_offset_x, end_offset_y)
                self.canvas.create_line(s_start_x, s_start_y, s_end_x, s_end_y, fill="#999999", width=1.5 * self.scale, arrow=tk.LAST)
                mid_x, mid_y = (s_start_x + s_end_x) / 2, (s_start_y + s_end_y) / 2
                font_size, cond_font_size = max(7, int(9 * self.scale)), max(6, int(8 * self.scale))
                font, cond_font = ("Arial", font_size), ("Arial", cond_font_size, "italic")
                self.canvas.create_text(mid_x, mid_y - (6 * self.scale), text=branch["text"], fill="#CCCCCC", font=font)
                if branch["condition"]: self.canvas.create_text(mid_x, mid_y + (6 * self.scale), text=f"[{branch['condition']}]", fill="#AAAAAA", font=cond_font)

    def get_scene_by_id(self, scene_id: str) -> Optional[Scene]:
        # (変更なし)
        return next((s for s in self.scenes if s.id == scene_id), None)
    
    def _update_editor_ui_state(self):
        # (変更なし)
        is_scene_selected = self.selected_scene is not None; state = tk.NORMAL if is_scene_selected else tk.DISABLED
        self.scene_name_entry.config(state=state); self.scene_content_text.text.config(state=state)
        self.scene_name_entry.delete(0, tk.END); self.scene_content_text.delete("1.0", tk.END)
        if is_scene_selected:
            self.scene_name_entry.insert(0, self.selected_scene.name)
            self.scene_content_text.insert("1.0", self.selected_scene.content)
        self.add_branch_btn.config(state=state); self._update_branch_list(); self._update_text_info()
    
    def _update_branch_list(self):
        # (変更なし)
        self.branch_tree.delete(*self.branch_tree.get_children())
        if self.selected_scene:
            scene_map = {s.id: s.name for s in self.scenes}
            for i, branch in enumerate(self.selected_scene.branches):
                target_name = scene_map.get(branch["target"], "不明なシーン")
                self.branch_tree.insert("", tk.END, iid=str(i), values=(branch["text"], target_name, branch["condition"]))
        self._update_branch_buttons_state()
    
    def _update_branch_buttons_state(self, event=None):
        # (変更なし)
        is_branch_selected = bool(self.branch_tree.selection())
        state = tk.NORMAL if self.selected_scene and is_branch_selected else tk.DISABLED
        self.edit_branch_btn.config(state=state); self.delete_branch_btn.config(state=state)
    
    def _update_status_bar(self, message: Optional[str] = None):
        # (変更なし)
        if message:
            self.status_bar.config(text=message)
            self.root.after(3000, lambda: self._update_status_bar())
        else:
            status = f"選択中: {self.selected_scene.name}" if self.selected_scene else "シーン未選択"
            status += f" | シーン数: {len(self.scenes)} | ズーム: {self.scale:.2f}"; self.status_bar.config(text=status)
    
    def _update_text_info(self, event=None):
        # (変更なし)
        self._mark_dirty()
        content = self.scene_content_text.get("1.0", "end-1c"); char_count = len(content)
        line_count = content.count("\n") + 1 if content else 0
        self.text_info_label.config(text=f"文字数: {char_count} | 行数: {line_count}"); self.scene_content_text.text.edit_modified(False)
    
    def _check_dirty_and_proceed(self) -> bool:
        # (変更なし)
        if not self.is_dirty: return True
        answer = messagebox.askyesnocancel("確認", "現在のプロジェクトに変更があります。保存しますか？")
        if answer is True: return self.save_project()
        elif answer is False: return True
        else: return False

    def _on_closing(self):
        # (変更なし)
        if self._check_dirty_and_proceed(): self.root.destroy()
    
    def new_project(self, event=None, startup=False):
        # (変更なし)
        if not startup and not self._check_dirty_and_proceed(): return
        self.current_project_path = None; self.project_data = {"scenes": []}
        for key, default in self.pluggable_data_keys.items(): self.project_data[key] = default
        self.scenes = []; self.project_data["scenes"] = self.scenes; self.selected_scene = None
        self.view_offset_x, self.view_offset_y, self.scale = 0.0, 0.0, 1.0
        self.root.title("ノベルゲーム制作支援ツール - 無題"); self._mark_dirty(False)
        self._update_editor_ui_state(); self._redraw_canvas()
    
    def open_project(self, event=None, path_to_open: Optional[Path] = None):
        # (変更なし)
        if not self._check_dirty_and_proceed(): return
        path_str = str(path_to_open) if path_to_open else filedialog.askopenfilename(filetypes=[("ノベルプロジェクト", "*.ngp")])
        if not path_str: return
        try:
            path = Path(path_str);
            with open(path, "r", encoding="utf-8") as f: data = json.load(f)
            scenes_data = data.get("scenes", []);
            if not isinstance(scenes_data, list): raise ValueError("scenesデータがリスト形式ではありません。")
            self.project_data = {};
            for key, default in self.pluggable_data_keys.items(): self.project_data[key] = data.get(key, default)
            self.scenes = [Scene.from_dict(d) for d in scenes_data]; self.project_data["scenes"] = self.scenes
            self.current_project_path = path; self.selected_scene = None; self.view_offset_x, self.view_offset_y, self.scale = 0.0, 0.0, 1.0
            self.root.title(f"ノベルゲーム制作支援ツール - {self.current_project_path.name}"); self._mark_dirty(False)
            self._update_editor_ui_state(); self._redraw_canvas(); self.config_manager.add_recent_file(path)
            self._update_recent_files_menu(); self._update_status_bar(f"プロジェクト '{path.name}' を開きました。")
        except Exception as e: messagebox.showerror("エラー", f"プロジェクトの読み込みに失敗しました:\n{e}")
    
    def save_project(self, event=None) -> bool:
        # (変更なし)
        if not self.current_project_path: return self.save_project_as()
        else: return self._save_to_file(self.current_project_path)
    
    def save_project_as(self, event=None) -> bool:
        # (変更なし)
        path_str = filedialog.asksaveasfilename(defaultextension=".ngp", filetypes=[("ノベルプロジェクト", "*.ngp")])
        if not path_str: return False
        path = Path(path_str); self.current_project_path = path; self.root.title(f"ノベルゲーム制作支援ツール - {path.name}")
        return self._save_to_file(path)

    def _save_to_file(self, path: Path, update_dirty_flag: bool = True) -> bool:
        # (変更なし)
        self._save_current_scene_data(); data_to_save = {}
        for key in self.pluggable_data_keys:
            if key in self.project_data: data_to_save[key] = self.project_data[key]
        data_to_save["scenes"] = [s.to_dict() for s in self.scenes]
        try:
            with open(path, "w", encoding="utf-8") as f: json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            if update_dirty_flag:
                self._mark_dirty(False); self.config_manager.add_recent_file(path); self._update_recent_files_menu()
                self._update_status_bar(f"プロジェクトを '{path.name}' に保存しました。")
            return True
        except Exception as e:
            if update_dirty_flag: messagebox.showerror("エラー", f"保存に失敗しました:\n{e}")
            else: print(f"バックアップ保存失敗: {e}")
            return False

    def _update_recent_files_menu(self):
        # (変更なし)
        if not self.recent_files_menu: return
        self.recent_files_menu.delete(0, tk.END)
        recent_files = self.config_manager.get_recent_files()
        if not recent_files: self.recent_files_menu.add_command(label="（履歴なし）", state="disabled"); return
        for i, path in enumerate(recent_files):
            path_text = str(path);
            if len(path_text) > 60: path_text = path_text[:25] + "..." + path_text[-30:]
            self.recent_files_menu.add_command(label=f"{i+1}. {path_text}", command=lambda p=path: self.open_project(path_to_open=p))

    def add_scene(self, event=None, at_screen_pos: Optional[Tuple[float, float]] = None, return_scene=False, at_canvas_pos=None):
        # (変更なし)
        if at_canvas_pos: wx, wy = at_canvas_pos
        elif at_screen_pos: wx, wy = self._screen_to_world(at_screen_pos[0], at_screen_pos[1])
        else: wx, wy = self._screen_to_world(self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2)
        new_scene = Scene(name="新しいシーン", x=wx, y=wy); self.scenes.append(new_scene); self.select_scene(new_scene)
        self._mark_dirty(); self._redraw_canvas()
        if return_scene: return new_scene
    
    def delete_scene(self, event=None):
        # (変更なし)
        if not self.selected_scene: return
        if not messagebox.askyesno("確認", f"シーン '{self.selected_scene.name}' を削除しますか？\nこのシーンへの分岐も全て削除されます。"): return
        sid = self.selected_scene.id; self.scenes = [s for s in self.scenes if s.id != sid]
        for scene in self.scenes: scene.branches = [b for b in scene.branches if b.get("target") != sid]
        self.select_scene(None); self._mark_dirty(); self._redraw_canvas()
    
    def add_branch(self, event=None):
        if not self.selected_scene: return
        ### BUG FIX 3: `app=self`を渡す
        dialog = BranchDialog(self.root, "分岐を追加", self.scenes, self.selected_scene, app=self)
        if dialog.result:
            self.selected_scene.add_branch(**dialog.result)
            self._mark_dirty(); self._update_branch_list(); self._redraw_canvas()
    
    def edit_branch(self, event=None):
        if not self.selected_scene or not self.branch_tree.selection(): return
        try: branch_index = self.branch_tree.index(self.branch_tree.selection()[0]); branch = self.selected_scene.branches[branch_index]
        except (ValueError, IndexError): messagebox.showerror("エラー", "選択された分岐が見つかりません。"); return
        ### BUG FIX 3: `app=self`を渡す
        dialog = BranchDialog(self.root, "分岐を編集", self.scenes, self.selected_scene, app=self, initial_text=branch["text"], initial_target_id=branch["target"], initial_condition=branch["condition"])
        if dialog.result:
            self.selected_scene.branches[branch_index] = dialog.result
            self._mark_dirty(); self._update_branch_list(); self._redraw_canvas()
    
    def delete_branch(self):
        # (変更なし)
        if not self.selected_scene or not self.branch_tree.selection(): return
        if not messagebox.askyesno("確認", "選択した分岐を削除しますか？"): return
        indices_to_delete = sorted([self.branch_tree.index(iid) for iid in self.branch_tree.selection()], reverse=True)
        for index in indices_to_delete: del self.selected_scene.branches[index]
        self._mark_dirty(); self._update_branch_list(); self._redraw_canvas()
    
    def _show_settings(self):
        # (変更なし)
        SettingsDialog(self.root, self.config_manager)
    
    def _on_delete_key_pressed(self, event):
        # (変更なし)
        focused_widget = self.root.focus_get()
        if isinstance(focused_widget, ttk.Treeview): self.delete_branch()
        elif isinstance(focused_widget, tk.Canvas): self.delete_scene()
    
    def _zoom(self, factor, x=None, y=None):
        # (変更なし)
        if x is None: x = self.canvas.winfo_width() / 2
        if y is None: y = self.canvas.winfo_height() / 2
        world_x_before, world_y_before = self._screen_to_world(x, y)
        self.scale *= factor; self.scale = max(0.2, min(3.0, self.scale))
        world_x_after, world_y_after = self._screen_to_world(x, y)
        self.view_offset_x += world_x_before - world_x_after
        self.view_offset_y += world_y_before - world_y_after
        self._redraw_canvas()
    
    def zoom_in(self, event=None): self._zoom(1.2)
    def zoom_out(self, event=None): self._zoom(1/1.2)
    def reset_view(self, event=None): self.view_offset_x, self.view_offset_y, self.scale = 0.0, 0.0, 1.0; self._redraw_canvas()
    
    def setup_shortcuts(self):
        ### BUG FIX 1: `unbind_all`をやめ、管理下のショートカットのみを安全にunbindする
        for shortcut in self.bound_shortcuts:
            self.root.unbind(shortcut)
        self.bound_shortcuts.clear()

        bindings = {'new_project': self.new_project, 'open_project': self.open_project, 'save_project': self.save_project, 'save_project_as': self.save_project_as, 'add_scene': self.add_scene, 'add_branch': self.add_branch, 'zoom_in': self.zoom_in, 'zoom_out': self.zoom_out, 'reset_view': self.reset_view}
        for action, command in bindings.items():
            shortcut = self.config_manager.get_shortcut(action)
            if not shortcut: continue
            parts = shortcut.replace('+', '-').split('-')
            modifiers = sorted([p.capitalize() for p in parts[:-1] if p.lower() in ('control', 'alt', 'shift')])
            key = parts[-1].lower()
            if not key: continue
            
            # tkinterのフォーマットに変換
            tk_key_parts = []
            for mod in modifiers: tk_key_parts.append(mod)
            # 'plus' や 'minus' などの特殊なキー名を正しく扱う
            key_map = {'plus': 'plus', 'minus': 'minus', 'equal': 'equal'}
            tk_key_parts.append(key_map.get(key, key))
            tk_key = f"<{'-'.join(tk_key_parts)}>"
            
            self.root.bind(tk_key, lambda e, cmd=command: cmd())
            self.bound_shortcuts.append(tk_key) # 新しいバインドをリストに追加

        self._update_menu_accelerators()
    
    def _load_plugins(self):
        # (変更なし)
        print("[メイン] プラグインのロード処理を開始します..."); plugin_names = self.plugin_manager.discover_plugins()
        if not plugin_names: print("[メイン] ロード対象のプラグインはありませんでした。"); return
        for name in plugin_names: self.plugin_manager.load_plugin(name)

# --- メイン実行ブロック ---
if __name__ == "__main__":
    # (変更なし)
    if not getattr(sys, 'frozen', False):
        try:
            APP_MODULE_NAME = Path(__file__).stem
            sys.modules[APP_MODULE_NAME] = sys.modules['__main__']
        except NameError: # 対話モードなど__file__がない場合
            pass
    root = tk.Tk()
    root.update_idletasks()
    screen_width = root.winfo_screenwidth(); screen_height = root.winfo_screenheight()
    window_width = 1280; window_height = 800
    x = (screen_width // 2) - (window_width // 2); y = (screen_height // 2) - (window_height // 2)
    root.geometry(f'{window_width}x{window_height}+{x}+{y}')
    sv_ttk.set_theme("dark")
    app = NovelGameEditor(root)
    root.mainloop()
