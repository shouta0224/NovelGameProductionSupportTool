import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import uuid
import configparser
import importlib
import inspect
import os
from pathlib import Path
from typing import List, Dict, Type, Optional, Any, Tuple
import math

# UIテーマライブラリ (pip install sv-ttk)
import sv_ttk

# --- プラグイン関連 ---

class IPlugin:
    """
    プラグインの基底クラス。
    すべてのプラグインはこのクラスを継承し、必須メソッドを実装する必要があります。
    """
    def __init__(self, app: 'NovelGameEditor'):
        self.app = app
    def setup(self) -> None: pass
    def register(self) -> None: pass
    def teardown(self) -> None: pass

class PluginManager:
    """
    プラグインの発見、ロード、アンロード、リロードを管理するクラス。
    """
    def __init__(self, app: 'NovelGameEditor'):
        self.app = app
        self.plugins: Dict[str, IPlugin] = {}
        self.plugin_dir = Path("plugins")
        self.plugin_dir.mkdir(exist_ok=True)

    def discover_plugins(self) -> List[str]:
        plugin_files = self.plugin_dir.glob("*.py")
        return [f.stem for f in plugin_files if f.is_file() and not f.name.startswith("_")]

    def load_plugin(self, plugin_name: str) -> bool:
        if plugin_name in self.plugins: return False
        try:
            module = importlib.import_module(f"{self.plugin_dir.name}.{plugin_name}")
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, IPlugin) and obj != IPlugin:
                    plugin_instance = obj(self.app)
                    plugin_instance.setup()
                    plugin_instance.register()
                    self.plugins[plugin_name] = plugin_instance
                    print(f"プラグイン'{plugin_name}'をロードしました。")
                    return True
        except Exception as e:
            print(f"プラグイン'{plugin_name}'のロード中にエラー: {e}")
        return False

    def unload_plugin(self, plugin_name: str) -> bool:
        if plugin_name not in self.plugins: return False
        try:
            self.plugins[plugin_name].teardown()
            del self.plugins[plugin_name]
            print(f"プラグイン'{plugin_name}'をアンロードしました。")
            return True
        except Exception as e:
            print(f"プラグイン'{plugin_name}'のアンロード中にエラー: {e}")
        return False

# --- 設定管理 ---

class ConfigManager:
    """
    アプリケーションの設定（ショートカットキーなど）を管理するクラス。
    """
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = Path("config.ini")
        self._load_config()

    def _load_config(self) -> None:
        default_shortcuts = {
            'new_project': 'Control-n', 'open_project': 'Control-o',
            'save_project': 'Control-s', 'add_scene': 'Control-a',
            'delete_scene': 'Control-d'
        }
        if not self.config.has_section('SHORTCUTS'):
            self.config.add_section('SHORTCUTS')
        for key, value in default_shortcuts.items():
            if not self.config.has_option('SHORTCUTS', key):
                self.config.set('SHORTCUTS', key, value)
        if self.config_file.exists():
            self.config.read(self.config_file, encoding='utf-8')
        self._save_config()

    def _save_config(self) -> None:
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)

    def get_shortcut(self, action: str) -> str:
        return self.config.get('SHORTCUTS', action, fallback='')

    def set_shortcut(self, action: str, shortcut: str) -> None:
        if not self.config.has_section('SHORTCUTS'):
            self.config.add_section('SHORTCUTS')
        self.config.set('SHORTCUTS', action, shortcut)
        self._save_config()

    def get_shortcut_display(self, action: str) -> str:
        return self.get_shortcut(action).replace('Control-', 'Ctrl+').title()

# --- 設定ダイアログ ---

class SettingsDialog(tk.Toplevel):
    """
    ショートカットキーなどのアプリケーション設定を変更するためのダイアログ。
    """
    def __init__(self, parent: tk.Tk, config_manager: ConfigManager):
        super().__init__(parent)
        self.title("設定")
        self.config_manager = config_manager
        self.transient(parent)
        self.grab_set()
        self.shortcut_entry_widgets = {}
        self._create_widgets()
        self.resizable(False, False)
        self.wait_window(self)

    def _create_widgets(self) -> None:
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main_frame, text="ショートカットキー設定", font="-weight bold").grid(
            row=0, column=0, columnspan=2, pady=10)
        shortcut_actions = {
            'new_project': "新規プロジェクト", 'open_project': "プロジェクトを開く",
            'save_project': "プロジェクトを保存", 'add_scene': "シーンを追加",
            'delete_scene': "シーンを削除"
        }
        for i, (action_key, action_label) in enumerate(shortcut_actions.items(), 1):
            ttk.Label(main_frame, text=f"{action_label}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            entry = ttk.Entry(main_frame, width=30)
            entry.grid(row=i, column=1, padx=5, pady=2)
            entry.insert(0, self.config_manager.get_shortcut(action_key))
            self.shortcut_entry_widgets[action_key] = entry
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=len(shortcut_actions) + 1, column=0, columnspan=2, pady=15)
        ttk.Button(button_frame, text="保存", command=self._save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _save_settings(self) -> None:
        for action_key, entry_widget in self.shortcut_entry_widgets.items():
            self.config_manager.set_shortcut(action_key, entry_widget.get().strip())
        if hasattr(self.master, 'setup_shortcuts'):
            self.master.setup_shortcuts()
        self.destroy()

# --- データ構造 ---

class Scene:
    """
    ノベルゲームの1シーンを表すクラス。
    """
    def __init__(self, name: str = "New Scene", content: str = "", x: float = 0.0, y: float = 0.0):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.content: str = content
        self.x: float = float(x)
        self.y: float = float(y)
        self.branches: List[Dict[str, str]] = []

    def add_branch(self, text: str, target: str, condition: str = "") -> None:
        self.branches.append({"text": text, "target": target, "condition": condition})

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "content": self.content,
                "x": self.x, "y": self.y, "branches": self.branches}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scene':
        scene = cls(data.get("name", "Unnamed Scene"), data.get("content", ""), data.get("x", 0.0), data.get("y", 0.0))
        scene.id = data.get("id", str(uuid.uuid4()))
        scene.branches = data.get("branches", [])
        return scene

# --- メインアプリケーションクラス (不具合修正済み) ---
class NovelGameEditor:
    NODE_RADIUS = 35
    NODE_DIAMETER = NODE_RADIUS * 2

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ノベルゲーム制作支援ツール")
        self.root.geometry("1280x800")

        self.config_manager = ConfigManager()
        self.plugin_manager = PluginManager(self)
        self.current_project_path: Optional[Path] = None
        self.scenes: List[Scene] = []
        self.selected_scene: Optional[Scene] = None
        self.is_dirty = False

        self.scale = 1.0
        self.view_offset_x = 0.0
        self.view_offset_y = 0.0

        self.drag_state = {}

        self._create_widgets()
        self._bind_events()
        self.setup_shortcuts()
        self._load_plugins()

        self.new_project(startup=True)
        self._update_status_bar()

    def _create_widgets(self):
        self._create_menu()
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        canvas_frame = ttk.Frame(main_paned)
        self.canvas = tk.Canvas(canvas_frame, bg="#333333", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        main_paned.add(canvas_frame, weight=3)
        
        editor_frame = ttk.Frame(main_paned)
        self._create_editor_widgets(editor_frame)
        main_paned.add(editor_frame, weight=1)

        self.status_bar = ttk.Label(self.root, text="準備完了", anchor=tk.W, padding=(5, 2))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="新規", command=self.new_project, accelerator=self.config_manager.get_shortcut_display('new_project'))
        file_menu.add_command(label="開く", command=self.open_project, accelerator=self.config_manager.get_shortcut_display('open_project'))
        file_menu.add_command(label="保存", command=self.save_project, accelerator=self.config_manager.get_shortcut_display('save_project'))
        file_menu.add_command(label="名前を付けて保存", command=self.save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="設定", command=self._show_settings)
        file_menu.add_separator()
        self.theme_menu = tk.Menu(file_menu, tearoff=0)
        self.theme_menu.add_command(label="ダークテーマ", command=lambda: self.set_theme("dark"))
        self.theme_menu.add_command(label="ライトテーマ", command=lambda: self.set_theme("light"))
        file_menu.add_cascade(label="テーマ", menu=self.theme_menu)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self._on_closing)
        menubar.add_cascade(label="ファイル", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="シーンを追加", command=lambda: self.add_scene(), accelerator=self.config_manager.get_shortcut_display('add_scene'))
        edit_menu.add_command(label="選択中のシーンを削除", command=self.delete_scene, accelerator=self.config_manager.get_shortcut_display('delete_scene'))
        menubar.add_cascade(label="編集", menu=edit_menu)

    def _create_editor_widgets(self, parent_frame):
        editor_paned = ttk.PanedWindow(parent_frame, orient=tk.VERTICAL)
        editor_paned.pack(fill=tk.BOTH, expand=True)

        scene_info_frame = ttk.LabelFrame(editor_paned, text="シーン情報", padding=10)
        scene_info_frame.columnconfigure(1, weight=1)
        scene_info_frame.rowconfigure(1, weight=1)
        ttk.Label(scene_info_frame, text="シーン名:").grid(row=0, column=0, sticky="w", pady=2)
        self.scene_name_entry = ttk.Entry(scene_info_frame)
        self.scene_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.scene_name_entry.bind("<FocusOut>", self._on_scene_data_changed)
        self.scene_name_entry.bind("<Return>", self._on_scene_data_changed)
        ttk.Label(scene_info_frame, text="内容:").grid(row=1, column=0, sticky="nw", pady=2)
        self.scene_content_text = tk.Text(scene_info_frame, height=10, wrap=tk.WORD, relief=tk.FLAT)
        self.scene_content_text.grid(row=1, column=1, sticky="nsew", padx=5, pady=2)
        self.scene_content_text.bind("<FocusOut>", self._on_scene_data_changed)
        editor_paned.add(scene_info_frame, weight=2)

        branch_frame = ttk.LabelFrame(editor_paned, text="分岐管理", padding=10)
        branch_frame.rowconfigure(0, weight=1)
        branch_frame.columnconfigure(0, weight=1)
        columns = ("text", "target", "condition")
        self.branch_tree = ttk.Treeview(branch_frame, columns=columns, show="headings", height=5)
        self.branch_tree.heading("text", text="選択肢")
        self.branch_tree.heading("target", text="遷移先")
        self.branch_tree.heading("condition", text="条件")
        self.branch_tree.column("text", width=120, anchor='w')
        self.branch_tree.column("target", width=100, anchor='w')
        self.branch_tree.column("condition", width=120, anchor='w')
        self.branch_tree.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.branch_tree.bind('<<TreeviewSelect>>', lambda e: self._update_editor_ui_state())
        
        branch_btn_frame = ttk.Frame(branch_frame)
        branch_btn_frame.grid(row=1, column=0, columnspan=3, sticky="w", pady=(5,0))
        self.add_branch_btn = ttk.Button(branch_btn_frame, text="追加", command=self.add_branch, width=8)
        self.add_branch_btn.pack(side=tk.LEFT, padx=2)
        self.edit_branch_btn = ttk.Button(branch_btn_frame, text="編集", command=self.edit_branch, width=8)
        self.edit_branch_btn.pack(side=tk.LEFT, padx=2)
        self.delete_branch_btn = ttk.Button(branch_btn_frame, text="削除", command=self.delete_branch, width=8)
        self.delete_branch_btn.pack(side=tk.LEFT, padx=2)
        editor_paned.add(branch_frame, weight=1)

    def _bind_events(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self._on_canvas_double_click)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)
        self.canvas.bind("<MouseWheel>", self._on_canvas_mousewheel)

    def _on_canvas_press(self, event):
        self._save_current_scene_data()
        self.canvas.focus_set()
        
        clicked_node_id = self._get_node_id_at(event.x, event.y)
        
        if clicked_node_id:
            scene = self.get_scene_by_id(clicked_node_id)
            if scene:
                self.drag_state = {
                    "type": "node", "item_id": clicked_node_id,
                    "start_x": event.x, "start_y": event.y,
                    "original_x": scene.x, "original_y": scene.y
                }
                if self.selected_scene != scene:
                    self.select_scene(scene)
        else:
            self.drag_state = {
                "type": "pan", "start_x": event.x, "start_y": event.y
            }
            self.select_scene(None)
    
    def _on_canvas_drag(self, event):
        drag_type = self.drag_state.get("type")
        if not drag_type: return

        if drag_type == "node":
            scene = self.get_scene_by_id(self.drag_state["item_id"])
            if scene:
                dx = event.x - self.drag_state["start_x"]
                dy = event.y - self.drag_state["start_y"]
                
                scene.x = self.drag_state["original_x"] + (dx / self.scale)
                scene.y = self.drag_state["original_y"] + (dy / self.scale)
                
                self._redraw_canvas()

        elif drag_type == "pan":
            dx = event.x - self.drag_state["start_x"]
            dy = event.y - self.drag_state["start_y"]
            
            self.view_offset_x += dx / self.scale
            self.view_offset_y += dy / self.scale
            
            self.drag_state["start_x"], self.drag_state["start_y"] = event.x, event.y
            self._redraw_canvas()
    
    def _on_canvas_release(self, event):
        if self.drag_state.get("type") == "node":
            dx = event.x - self.drag_state.get("start_x", event.x)
            dy = event.y - self.drag_state.get("start_y", event.y)
            if abs(dx) > 3 or abs(dy) > 3:
                self._mark_dirty()
        self.drag_state = {}

    def _on_canvas_double_click(self, event):
        if self.selected_scene:
            self.scene_name_entry.focus_set()
            self.scene_name_entry.selection_range(0, tk.END)

    def _on_canvas_right_click(self, event):
        context_menu = tk.Menu(self.root, tearoff=0)
        clicked_node_id = self._get_node_id_at(event.x, event.y)

        if clicked_node_id:
            scene = self.get_scene_by_id(clicked_node_id)
            if scene and scene != self.selected_scene:
                self.select_scene(scene)
            
            context_menu.add_command(label=f"シーン '{scene.name}' を削除", command=self.delete_scene)
            context_menu.add_separator()
        
        context_menu.add_command(label="ここにシーンを追加", command=lambda: self.add_scene(at_screen_pos=(event.x, event.y)))
        context_menu.add_command(label="ビューをリセット", command=self.reset_view)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def _on_canvas_mousewheel(self, event):
        zoom_factor = 1.1 if (event.delta > 0 or event.num == 4) else 1/1.1
        cursor_x_screen, cursor_y_screen = event.x, event.y
        world_x_before, world_y_before = self._screen_to_world(cursor_x_screen, cursor_y_screen)
        
        self.scale *= zoom_factor
        self.scale = max(0.2, min(3.0, self.scale))
        
        world_x_after, world_y_after = self._screen_to_world(cursor_x_screen, cursor_y_screen)
        
        self.view_offset_x += world_x_before - world_x_after
        self.view_offset_y += world_y_before - world_y_after
        
        self._redraw_canvas()

    def _get_node_id_at(self, x: int, y: int) -> Optional[str]:
        items = self.canvas.find_overlapping(x - 1, y - 1, x + 1, y + 1)
        for item in reversed(items):
            tags = self.canvas.gettags(item)
            if "node" in tags or "node_text" in tags:
                for tag in tags:
                    if tag.startswith("node_"):
                        return tag.split("_")[1]
        return None

    def reset_view(self):
        self.view_offset_x, self.view_offset_y, self.scale = 0.0, 0.0, 1.0
        self._redraw_canvas()

    def _on_scene_data_changed(self, event=None):
        if not self.selected_scene: return
        
        name_changed = self.scene_name_entry.get() != self.selected_scene.name
        content_changed = self.scene_content_text.get("1.0", tk.END).strip() != self.selected_scene.content
        
        if name_changed or content_changed:
            self._save_current_scene_data()
            self._redraw_canvas()
            self._mark_dirty()

    def _save_current_scene_data(self):
        if not self.selected_scene: return
        self.selected_scene.name = self.scene_name_entry.get()
        self.selected_scene.content = self.scene_content_text.get("1.0", tk.END).strip()
    
    def _mark_dirty(self, dirty=True):
        if self.is_dirty == dirty: return
        self.is_dirty = dirty
        title = self.root.title()
        if dirty and not title.endswith(" *"):
            self.root.title(title + " *")
        elif not dirty and title.endswith(" *"):
            self.root.title(title[:-2])
            
    def set_theme(self, theme_name: str):
        sv_ttk.set_theme(theme_name)
        self.canvas.config(bg="#333333" if theme_name == "dark" else "#F0F0F0")
        self._redraw_canvas()

    def _world_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        screen_x = (x + self.view_offset_x) * self.scale
        screen_y = (y + self.view_offset_y) * self.scale
        return screen_x, screen_y
    
    def _screen_to_world(self, x: float, y: float) -> Tuple[float, float]:
        world_x = (x / self.scale) - self.view_offset_x
        world_y = (y / self.scale) - self.view_offset_y
        return world_x, world_y

    def _redraw_canvas(self):
        self.canvas.delete("all")
        self._draw_branches()
        self._draw_nodes()
        self.canvas.tag_raise("selected")
        self._update_status_bar()

    def _draw_nodes(self):
        for scene in self.scenes:
            sx, sy = self._world_to_screen(scene.x, scene.y)
            radius = self.NODE_RADIUS * self.scale
            
            is_selected = self.selected_scene and self.selected_scene.id == scene.id
            
            tags = ("node", f"node_{scene.id}")
            if is_selected:
                tags += ("selected",)
            
            fill_color = "#4E6A85" if is_selected else "#6C757D"
            outline_color = "#87CEFA" if is_selected else "#ADB5BD"
            outline_width = 3 * self.scale if is_selected else 1.5 * self.scale
            
            self.canvas.create_oval(sx - radius, sy - radius, sx + radius, sy + radius,
                                    fill=fill_color, outline=outline_color, width=outline_width,
                                    tags=tags)
            
            font_size = max(8, int(10 * self.scale))
            font = ("Arial", font_size)
            self.canvas.create_text(sx, sy, text=scene.name, fill="white", font=font,
                                    tags=("node_text", f"node_{scene.id}"))

    def _draw_branches(self):
        scene_map = {s.id: s for s in self.scenes}
        for scene in self.scenes:
            for branch in scene.branches:
                target_scene = scene_map.get(branch["target"])
                if not target_scene: continue
                
                start_x, start_y = scene.x, scene.y
                end_x, end_y = target_scene.x, target_scene.y
                
                dx, dy = end_x - start_x, end_y - start_y
                dist = math.hypot(dx, dy)
                if dist == 0: continue
                
                start_offset_x = start_x + (dx / dist) * self.NODE_RADIUS
                start_offset_y = start_y + (dy / dist) * self.NODE_RADIUS
                end_offset_x = end_x - (dx / dist) * self.NODE_RADIUS
                end_offset_y = end_y - (dy / dist) * self.NODE_RADIUS
                
                s_start_x, s_start_y = self._world_to_screen(start_offset_x, start_offset_y)
                s_end_x, s_end_y = self._world_to_screen(end_offset_x, end_offset_y)

                self.canvas.create_line(s_start_x, s_start_y, s_end_x, s_end_y,
                                                  fill="#999999", width=1.5 * self.scale, arrow=tk.LAST)
                
                mid_x = (s_start_x + s_end_x) / 2
                mid_y = (s_start_y + s_end_y) / 2
                font_size = max(7, int(9 * self.scale))
                font = ("Arial", font_size)
                
                self.canvas.create_text(mid_x, mid_y - (6 * self.scale), text=branch["text"], fill="#CCCCCC", font=font)
                if branch["condition"]:
                    cond_font = ("Arial", max(6, int(8 * self.scale)), "italic")
                    self.canvas.create_text(mid_x, mid_y + (6 * self.scale), text=f"[{branch['condition']}]", fill="#AAAAAA", font=cond_font)

    def get_scene_by_id(self, scene_id: str) -> Optional[Scene]:
        return next((s for s in self.scenes if s.id == scene_id), None)
        
    def select_scene(self, scene: Optional[Scene]):
        if self.selected_scene == scene: return
        self._save_current_scene_data()
        self.selected_scene = scene
        self._update_editor_ui_state()
        self._redraw_canvas()

    def _update_editor_ui_state(self):
        is_scene_selected = self.selected_scene is not None
        
        self.scene_name_entry.config(state=tk.NORMAL if is_scene_selected else tk.DISABLED)
        self.scene_content_text.config(state=tk.NORMAL if is_scene_selected else tk.DISABLED)
        
        self.scene_name_entry.delete(0, tk.END)
        self.scene_content_text.delete("1.0", tk.END)

        if is_scene_selected:
            self.scene_name_entry.insert(0, self.selected_scene.name)
            self.scene_content_text.insert("1.0", self.selected_scene.content)
        
        self.add_branch_btn.config(state=tk.NORMAL if is_scene_selected else tk.DISABLED)
        
        is_branch_selected = bool(self.branch_tree.selection())
        self.edit_branch_btn.config(state=tk.NORMAL if is_branch_selected else tk.DISABLED)
        self.delete_branch_btn.config(state=tk.NORMAL if is_branch_selected else tk.DISABLED)
        
        self._update_branch_list()
    
    def _update_branch_list(self):
        self.branch_tree.delete(*self.branch_tree.get_children())
        if not self.selected_scene: return
        
        scene_map = {s.id: s.name for s in self.scenes}
        for i, branch in enumerate(self.selected_scene.branches):
            target_name = scene_map.get(branch["target"], "不明なシーン")
            self.branch_tree.insert("", tk.END, iid=str(i),
                                    values=(branch["text"], target_name, branch["condition"]))
    
    def _update_status_bar(self):
        if self.selected_scene:
            status = f"選択中: {self.selected_scene.name}"
        else:
            status = "シーン未選択"
        status += f" | シーン数: {len(self.scenes)} | ズーム: {self.scale:.2f}"
        self.status_bar.config(text=status)

    def _check_dirty_and_proceed(self) -> bool:
        if not self.is_dirty: return True
        
        answer = messagebox.askyesnocancel("確認", "現在のプロジェクトに変更があります。保存しますか？")
        if answer is True: # Yes
            self.save_project()
            return not self.is_dirty
        return answer is not None # False (No) -> True, Cancel -> False

    def _on_closing(self):
        if self._check_dirty_and_proceed():
            self.root.destroy()
            
    def new_project(self, startup=False):
        if not startup and not self._check_dirty_and_proceed(): return
        
        self.current_project_path = None
        self.scenes = []
        self.selected_scene = None
        self.view_offset_x, self.view_offset_y, self.scale = 0.0, 0.0, 1.0
        
        self.root.title("ノベルゲーム制作支援ツール - 無題")
        self._mark_dirty(False)
        self._update_editor_ui_state()
        self._redraw_canvas()

    def open_project(self):
        if not self._check_dirty_and_proceed(): return
        
        path_str = filedialog.askopenfilename(filetypes=[("ノベルプロジェクト", "*.ngp")])
        if not path_str: return

        path = Path(path_str)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.scenes = [Scene.from_dict(d) for d in data.get("scenes", [])]
            self.current_project_path = path
            self.selected_scene = None
            self.view_offset_x, self.view_offset_y, self.scale = 0.0, 0.0, 1.0

            self.root.title(f"ノベルゲーム制作支援ツール - {path.name}")
            self._mark_dirty(False)
            self._update_editor_ui_state()
            self._redraw_canvas()
        except Exception as e:
            messagebox.showerror("エラー", f"プロジェクトの読み込みに失敗しました:\n{e}")

    def save_project(self):
        if not self.current_project_path:
            self.save_project_as()
        else:
            self._save_to_file(self.current_project_path)
    
    def save_project_as(self):
        path_str = filedialog.asksaveasfilename(defaultextension=".ngp", filetypes=[("ノベルプロジェクト", "*.ngp")])
        if not path_str: return
        
        path = Path(path_str)
        self._save_to_file(path)
        self.current_project_path = path
        self.root.title(f"ノベルゲーム制作支援ツール - {path.name}")
        
    def _save_to_file(self, path: Path):
        self._save_current_scene_data()
        data = {"scenes": [s.to_dict() for s in self.scenes]}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._mark_dirty(False)
        except Exception as e:
            messagebox.showerror("エラー", f"保存に失敗しました:\n{e}")
            
    def add_scene(self, at_screen_pos: Optional[Tuple[float, float]] = None):
        if at_screen_pos:
            wx, wy = self._screen_to_world(at_screen_pos[0], at_screen_pos[1])
        else:
            wx, wy = self._screen_to_world(self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2)
        new_scene = Scene(name="新しいシーン", x=wx, y=wy)
        self.scenes.append(new_scene)
        self.select_scene(new_scene)
        self._mark_dirty()
        self._redraw_canvas()
        
    def delete_scene(self):
        if not self.selected_scene: return
        if not messagebox.askyesno("確認", f"シーン '{self.selected_scene.name}' を削除しますか？\nこのシーンへの分岐も全て削除されます。"): return
        
        sid = self.selected_scene.id
        self.scenes = [s for s in self.scenes if s.id != sid]
        for scene in self.scenes:
            scene.branches = [b for b in scene.branches if b.get("target") != sid]
        
        self.select_scene(None)
        self._mark_dirty()
        self._redraw_canvas()

    def add_branch(self):
        if not self.selected_scene: return
        dialog = BranchDialog(self.root, "分岐を追加", self.scenes, self.selected_scene)
        if dialog.result:
            self.selected_scene.add_branch(**dialog.result)
            self._mark_dirty()
            self._update_branch_list()
            self._redraw_canvas()

    def edit_branch(self):
        if not self.selected_scene or not self.branch_tree.selection(): return
        
        selected_iid = self.branch_tree.selection()[0]
        try:
            branch_index = self.branch_tree.index(selected_iid)
            branch = self.selected_scene.branches[branch_index]
        except (ValueError, IndexError):
            messagebox.showerror("エラー", "選択された分岐が見つかりません。")
            return
            
        dialog = BranchDialog(self.root, "分岐を編集", self.scenes, self.selected_scene,
                              initial_text=branch["text"],
                              initial_target_id=branch["target"],
                              initial_condition=branch["condition"])
        if dialog.result:
            self.selected_scene.branches[branch_index] = dialog.result
            self._mark_dirty()
            self._update_branch_list()
            self._redraw_canvas()

    def delete_branch(self):
        if not self.selected_scene or not self.branch_tree.selection(): return
        if not messagebox.askyesno("確認", "選択した分岐を削除しますか？"): return
        
        selected_iids = self.branch_tree.selection()
        indices_to_delete = sorted([self.branch_tree.index(iid) for iid in selected_iids], reverse=True)
        
        for index in indices_to_delete:
            del self.selected_scene.branches[index]
            
        self._mark_dirty()
        self._update_branch_list()
        self._redraw_canvas()
    
    def _show_settings(self):
        SettingsDialog(self.root, self.config_manager)
        
    def setup_shortcuts(self):
        for action, key in self.config_manager.config.items('SHORTCUTS'):
            tk_key = f"<{key.replace('-', '-').title()}>"
            command = getattr(self, action, None)
            if command:
                self.root.bind(tk_key, lambda e, cmd=command: cmd())
    
    def _load_plugins(self):
        for name in self.plugin_manager.discover_plugins():
            self.plugin_manager.load_plugin(name)

# --- 分岐設定ダイアログクラス ---
class BranchDialog(tk.Toplevel):
    def __init__(self, parent, title, all_scenes, source_scene, 
                 initial_text="", initial_target_id="", initial_condition=""):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        self.target_scenes = {s.name: s.id for s in all_scenes if s.id != source_scene.id}
        
        self._create_widgets(initial_text, initial_target_id, initial_condition)
        self.resizable(False, False)
        self.wait_window(self)

    def _create_widgets(self, initial_text, initial_target_id, initial_condition):
        frame = ttk.Frame(self, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="選択肢テキスト:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.text_entry = ttk.Entry(frame, width=40)
        self.text_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.text_entry.insert(0, initial_text)
        self.text_entry.focus_set()

        ttk.Label(frame, text="遷移先シーン:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.target_var = tk.StringVar()
        self.target_combo = ttk.Combobox(frame, textvariable=self.target_var, 
                                         values=list(self.target_scenes.keys()), state="readonly")
        self.target_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        if initial_target_id:
            target_name = next((name for name, id_ in self.target_scenes.items() if id_ == initial_target_id), None)
            if target_name:
                self.target_var.set(target_name)

        ttk.Label(frame, text="条件 (任意):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.condition_entry = ttk.Entry(frame, width=40)
        self.condition_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        self.condition_entry.insert(0, initial_condition)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(15, 0))
        ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="キャンセル", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _on_ok(self):
        text = self.text_entry.get().strip()
        target_name = self.target_var.get()
        
        if not text:
            messagebox.showerror("エラー", "選択肢テキストを入力してください。", parent=self)
            return
        if not target_name:
            messagebox.showerror("エラー", "遷移先シーンを選択してください。", parent=self)
            return
        
        self.result = {
            "text": text,
            "target": self.target_scenes[target_name],
            "condition": self.condition_entry.get().strip()
        }
        self.destroy()

# --- メイン実行ブロック ---
if __name__ == "__main__":
    root = tk.Tk()
    sv_ttk.set_theme("dark") # デフォルトテーマを設定
    app = NovelGameEditor(root)
    root.mainloop()
