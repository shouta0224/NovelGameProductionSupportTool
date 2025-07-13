import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import uuid
import configparser
import importlib
import inspect
import os
from pathlib import Path
from typing import List, Dict, Type, Optional

# --- Character クラス ---
class Character:
    def __init__(self, name: str, char_id: str, description: str = "", portrait_path: Optional[str] = None):
        self.id = char_id
        self.name = name
        self.description = description
        self.portrait_path = portrait_path

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "portrait_path": self.portrait_path
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Character':
        return cls(
            name=data.get("name", "無名"),
            char_id=data.get("id", str(uuid.uuid4())),
            description=data.get("description", ""),
            portrait_path=data.get("portrait_path")
        )

    def __str__(self):
        return f"{self.name} (ID: {self.id})"
# --- Character クラス 終了 ---

class IPlugin:
    def __init__(self, app):
        self.app = app
    
    def setup(self): pass
    def register(self): pass
    def teardown(self): pass

class PluginManager:
    def __init__(self, app):
        self.app = app
        self.plugins: Dict[str, IPlugin] = {}
        self.plugin_dir = "plugins"
        os.makedirs(self.plugin_dir, exist_ok=True)
    
    def discover_plugins(self) -> List[str]:
        plugin_files = Path(self.plugin_dir).glob("*.py")
        return [f.stem for f in plugin_files if f.is_file() and not f.name.startswith("_")]
    
    def load_plugin(self, plugin_name: str) -> bool:
        if plugin_name in self.plugins: return False
        try:
            module = importlib.import_module(f"{self.plugin_dir}.{plugin_name}")
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, IPlugin) and obj != IPlugin:
                    plugin = obj(self.app)
                    plugin.setup()
                    plugin.register()
                    self.plugins[plugin_name] = plugin
                    return True
        except Exception as e: print(f"プラグイン'{plugin_name}'のロードに失敗: {e}")
        return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        if plugin_name not in self.plugins: return False
        try:
            self.plugins[plugin_name].teardown()
            del self.plugins[plugin_name]
            return True
        except Exception as e: print(f"プラグイン'{plugin_name}'のアンロードに失敗: {e}")
        return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        self.unload_plugin(plugin_name)
        return self.load_plugin(plugin_name)

class ConfigManager:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = "config.ini"
        self.load_config()
    
    def load_config(self):
        self.config['SHORTCUTS'] = {
            'new_project': 'Control-n', 'open_project': 'Control-o', 'save_project': 'Control-s',
            'add_scene': 'Control-a', 'delete_scene': 'Control-d'
        }
        try:
            with open(self.config_file, 'r') as f: self.config.read_file(f)
        except FileNotFoundError: self.save_config()
    
    def save_config(self):
        with open(self.config_file, 'w') as f: self.config.write(f)
    
    def get_shortcut(self, action): return self.config['SHORTCUTS'].get(action, '')
    
    def get_shortcut_display(self, action):
        shortcut = self.get_shortcut(action)
        return shortcut.replace('Control-', 'Ctrl+').title()

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.title("設定")
        self.config_manager = config_manager
        self.transient(parent)
        self.grab_set()
        self.create_widgets()
        self.resizable(False, False)
        self.wait_window(self)
    
    def create_widgets(self):
        ttk.Label(self, text="ショートカットキー設定").grid(row=0, column=0, columnspan=2, pady=5)
        ttk.Label(self, text="新規プロジェクト:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.new_project_entry = ttk.Entry(self); self.new_project_entry.grid(row=1, column=1, padx=5, pady=2)
        self.new_project_entry.insert(0, self.config_manager.get_shortcut('new_project'))
        ttk.Label(self, text="プロジェクトを開く:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.open_project_entry = ttk.Entry(self); self.open_project_entry.grid(row=2, column=1, padx=5, pady=2)
        self.open_project_entry.insert(0, self.config_manager.get_shortcut('open_project'))
        ttk.Label(self, text="プロジェクトを保存:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.save_project_entry = ttk.Entry(self); self.save_project_entry.grid(row=3, column=1, padx=5, pady=2)
        self.save_project_entry.insert(0, self.config_manager.get_shortcut('save_project'))
        ttk.Label(self, text="シーンを追加:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.add_scene_entry = ttk.Entry(self); self.add_scene_entry.grid(row=4, column=1, padx=5, pady=2)
        self.add_scene_entry.insert(0, self.config_manager.get_shortcut('add_scene'))
        ttk.Label(self, text="シーンを削除:").grid(row=5, column=0, sticky="w", padx=5, pady=2)
        self.delete_scene_entry = ttk.Entry(self); self.delete_scene_entry.grid(row=5, column=1, padx=5, pady=2)
        self.delete_scene_entry.insert(0, self.config_manager.get_shortcut('delete_scene'))
        
        button_frame = ttk.Frame(self); button_frame.grid(row=6, column=0, columnspan=2, pady=5)
        ttk.Button(button_frame, text="保存", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def save_settings(self):
        self.config_manager.config['SHORTCUTS'] = {
            'new_project': self.new_project_entry.get(), 'open_project': self.open_project_entry.get(),
            'save_project': self.save_project_entry.get(), 'add_scene': self.add_scene_entry.get(),
            'delete_scene': self.delete_scene_entry.get()
        }
        self.config_manager.save_config()
        self.destroy()

class Scene:
    def __init__(self, name="New Scene", content="", x=0, y=0):
        self.id = str(uuid.uuid4())
        self.name = name
        self.content = content
        self.x, self.y = x, y
        self.branches = []

    def add_branch(self, text, target_scene_id, condition=""):
        self.branches.append({"text": text, "target": target_scene_id, "condition": condition})

    def to_dict(self):
        return {"id": self.id, "name": self.name, "content": self.content, "x": self.x, "y": self.y, "branches": self.branches}

    @classmethod
    def from_dict(cls, data):
        scene = cls(data["name"], data["content"], data["x"], data["y"])
        scene.id, scene.branches = data["id"], data["branches"]
        return scene

# --- CharacterManagementDialog クラス ---
class CharacterManagementDialog(tk.Toplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent)
        self.title("キャラクター管理")
        self.app = app_instance
        self.transient(parent)
        self.grab_set()

        self.current_character: Optional[Character] = None
        self.characters_original_state = [char.to_dict() for char in self.app.characters] 

        self.create_widgets()
        self.load_character_list()
        self.resizable(False, False)
        self.wait_window(self)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        list_frame = ttk.LabelFrame(main_frame, text="キャラクター一覧")
        list_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=5, padx=5)
        
        self.char_listbox = tk.Listbox(list_frame, height=10, exportselection=False, width=30)
        self.char_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.char_listbox.bind("<<ListboxSelect>>", self.on_listbox_select)

        list_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.char_listbox.yview)
        list_scrollbar.grid(row=0, column=1, sticky="ns")
        self.char_listbox.config(yscrollcommand=list_scrollbar.set)
        list_frame.columnconfigure(0, weight=1); list_frame.rowconfigure(0, weight=1)

        edit_frame = ttk.LabelFrame(main_frame, text="キャラクター編集")
        edit_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=5, padx=5)

        ttk.Label(edit_frame, text="名前:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.name_entry = ttk.Entry(edit_frame); self.name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(edit_frame, text="ID:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.id_entry = ttk.Entry(edit_frame); self.id_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(edit_frame, text="説明:").grid(row=2, column=0, sticky="nw", padx=5, pady=2)
        self.description_text = tk.Text(edit_frame, height=5, width=40, wrap=tk.WORD)
        self.description_text.grid(row=2, column=1, sticky="nsew", padx=5, pady=2)
        desc_scrollbar = ttk.Scrollbar(edit_frame, orient=tk.VERTICAL, command=self.description_text.yview)
        desc_scrollbar.grid(row=2, column=2, sticky="ns")
        self.description_text.config(yscrollcommand=desc_scrollbar.set)

        ttk.Label(edit_frame, text="立ち絵パス:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.portrait_path_entry = ttk.Entry(edit_frame); self.portrait_path_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
        self.browse_button = ttk.Button(edit_frame, text="参照", command=self.browse_portrait)
        self.browse_button.grid(row=3, column=2, padx=2)

        edit_frame.columnconfigure(1, weight=1); edit_frame.rowconfigure(2, weight=1)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        self.new_button = ttk.Button(button_frame, text="新規作成", command=self.new_character)
        self.new_button.pack(side=tk.LEFT, padx=5)
        self.save_button = ttk.Button(button_frame, text="保存", command=self.save_character)
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.delete_button = ttk.Button(button_frame, text="削除", command=self.delete_character)
        self.delete_button.pack(side=tk.LEFT, padx=5)
        self.close_button = ttk.Button(button_frame, text="閉じる", command=self.on_cancel)
        self.close_button.pack(side=tk.LEFT, padx=5)

        self.save_button.config(state=tk.DISABLED)
        self.delete_button.config(state=tk.DISABLED)

    def load_character_list(self):
        self.char_listbox.delete(0, tk.END)
        for i, char in enumerate(self.app.characters):
            display_text = f"{char.name} (ID: {char.id})"
            self.char_listbox.insert(tk.END, display_text)
            if char.name == "ナレーション":
                self.char_listbox.itemconfig(i, {'bg': '#e0e0e0'})
        
    def on_listbox_select(self, event):
        selected_indices = self.char_listbox.curselection()
        if not selected_indices: return

        index = selected_indices[0]
        self.current_character = self.app.characters[index]

        is_narration = (self.current_character.name == "ナレーション")

        self.name_entry.config(state=tk.NORMAL if not is_narration else tk.DISABLED)
        self.id_entry.config(state=tk.NORMAL if not is_narration else tk.DISABLED)
        self.description_text.config(state=tk.NORMAL if not is_narration else tk.DISABLED)
        self.portrait_path_entry.config(state=tk.NORMAL if not is_narration else tk.DISABLED)
        self.browse_button.config(state=tk.NORMAL if not is_narration else tk.DISABLED)
        self.save_button.config(state=tk.NORMAL if not is_narration else tk.DISABLED)
        self.delete_button.config(state=tk.NORMAL if not is_narration else tk.DISABLED)

        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, self.current_character.name)
        self.id_entry.delete(0, tk.END)
        self.id_entry.insert(0, self.current_character.id)
        self.description_text.delete("1.0", tk.END)
        self.description_text.insert("1.0", self.current_character.description)
        self.portrait_path_entry.delete(0, tk.END)
        if self.current_character.portrait_path:
            self.portrait_path_entry.insert(0, self.current_character.portrait_path)
        
        if is_narration:
            self.save_button.config(state=tk.DISABLED)
            self.delete_button.config(state=tk.DISABLED)

    def new_character(self):
        if self.current_character: self.save_character() # 変更があれば保存

        self.current_character = None
        self.name_entry.delete(0, tk.END)
        self.id_entry.delete(0, tk.END); self.id_entry.insert(0, "自動生成") # IDは新規作成時に自動生成
        self.description_text.delete("1.0", tk.END)
        self.portrait_path_entry.delete(0, tk.END)

        self.name_entry.config(state=tk.NORMAL)
        self.id_entry.config(state=tk.NORMAL) # 新規作成時はIDも編集可能にする
        self.description_text.config(state=tk.NORMAL)
        self.portrait_path_entry.config(state=tk.NORMAL)
        self.browse_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.NORMAL)
        self.delete_button.config(state=tk.DISABLED)

        self.char_listbox.selection_clear(0, tk.END) # リスト選択解除

    def save_character(self):
        name = self.name_entry.get().strip()
        char_id = self.id_entry.get().strip()
        
        if not name: messagebox.showerror("エラー", "キャラクター名を入力してください。", parent=self); return
        if not char_id: messagebox.showerror("エラー", "キャラクターIDを入力してください。", parent=self); return

        # ナレーションキャラクターの名前・IDは変更不可
        if self.current_character and self.current_character.name == "ナレーション":
            messagebox.showwarning("情報", "ナレーションの名前およびIDは変更できません。", parent=self)
            return

        # IDのユニーク性チェック
        if self.current_character is None: # 新規作成時のみチェック
            if any(char.id == char_id for char in self.app.characters):
                messagebox.showerror("エラー", f"キャラクターID '{char_id}' は既に使用されています。", parent=self); return
        elif self.current_character.id != char_id: # 既存キャラでID変更時のみチェック
             if any(char.id == char_id for char in self.app.characters if char.id != self.current_character.id):
                messagebox.showerror("エラー", f"キャラクターID '{char_id}' は既に使用されています。", parent=self); return

        if self.current_character: # 既存キャラクターの更新
            original_name = self.current_character.name
            self.current_character.name = name
            self.current_character.id = char_id
            self.current_character.description = self.description_text.get("1.0", tk.END).strip()
            self.current_character.portrait_path = self.portrait_path_entry.get().strip() or None
            
            selected_index = self.char_listbox.curselection()[0]
            self.char_listbox.delete(selected_index)
            self.char_listbox.insert(selected_index, f"{self.current_character.name} (ID: {self.current_character.id})")
            self.char_listbox.select_set(selected_index)

            if original_name != name: self.app.update_character_buttons()

        else: # 新規キャラクターの作成
            new_char = Character(name=name, char_id=char_id, description=self.description_text.get("1.0", tk.END).strip(), portrait_path=self.portrait_path_entry.get().strip() or None)
            self.app.characters.append(new_char)
            
            new_index = self.char_listbox.size()
            self.char_listbox.insert(tk.END, f"{new_char.name} (ID: {new_char.id})")
            self.char_listbox.selection_clear(0, tk.END)
            self.char_listbox.select_set(new_index)
            self.on_listbox_select(None)
            self.app.update_character_buttons()

        self.save_button.config(state=tk.NORMAL)
        self.delete_button.config(state=tk.NORMAL)

    def delete_character(self):
        selected_indices = self.char_listbox.curselection()
        if not selected_indices: return

        index = selected_indices[0]
        character_to_delete = self.app.characters[index]

        if character_to_delete.name == "ナレーション":
            messagebox.showerror("エラー", "ナレーションキャラクターは削除できません。", parent=self)
            return

        if messagebox.askyesno("確認", f"'{character_to_delete.name}' を削除しますか？", parent=self):
            del self.app.characters[index]
            self.char_listbox.delete(index)
            
            self.current_character = None
            self.name_entry.delete(0, tk.END)
            self.id_entry.delete(0, tk.END)
            self.description_text.delete("1.0", tk.END)
            self.portrait_path_entry.delete(0, tk.END)
            self.save_button.config(state=tk.DISABLED)
            self.delete_button.config(state=tk.DISABLED)
            
            self.app.update_character_buttons()

    def browse_portrait(self):
        filepath = filedialog.askopenfilename(
            title="立ち絵ファイルを選択",
            filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.gif"), ("すべてのファイル", "*.*")]
        )
        if filepath:
            self.portrait_path_entry.delete(0, tk.END)
            self.portrait_path_entry.insert(0, filepath)

    def has_unsaved_changes(self) -> bool:
        if self.current_character:
            if self.current_character.name != "ナレーション":
                if self.current_character.name != self.name_entry.get().strip() or \
                   self.current_character.id != self.id_entry.get().strip() or \
                   self.current_character.description != self.description_text.get("1.0", tk.END).strip() or \
                   self.current_character.portrait_path != (self.portrait_path_entry.get().strip() or None):
                    return True
        
        if len(self.app.characters) != len(self.characters_original_state): return True

        for i, char in enumerate(self.app.characters):
            if char.name == "ナレーション": continue
            original_char_data = next((d for d in self.characters_original_state if d.get("id") == char.id), None)
            if original_char_data is None: return True # 新規追加
            
            if char.name != original_char_data.get("name") or \
               char.id != original_char_data.get("id") or \
               char.description != original_char_data.get("description") or \
               char.portrait_path != original_char_data.get("portrait_path"):
                return True
        
        return False

    def on_cancel(self):
        if self.has_unsaved_changes():
            if not messagebox.askyesno("確認", "変更が保存されていません。閉じてよろしいですか？", parent=self): return
        self.destroy()

class NovelGameEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("ノベルゲーム制作支援ツール")
        self.root.geometry("1200x800")

        self.characters: List[Character] = [] # キャラクターリスト

        self.toolbar_frame = ttk.Frame(self.root)
        self.toolbar_frame.pack(fill=tk.X, padx=5, pady=2)

        self.plugin_manager = PluginManager(self)
        self.load_plugins()
        
        self.config_manager = ConfigManager()
        self.current_project = None
        self.scenes = []
        self.selected_scene = None
        self.drag_data = {"x": 0, "y": 0, "item": None}
        
        self.create_widgets()
        self.create_menu()
        self.setup_shortcuts()
        
        self.scene_name_entry.bind("<FocusOut>", self.on_scene_name_changed)
        self.scene_name_entry.bind("<Return>", self.on_scene_name_changed)
        self.scene_content_text.bind("<FocusOut>", self.on_scene_content_changed) 
        self.canvas.bind("<Button-3>", self.show_context_menu)

        self.load_characters_from_project()
        self.update_editor_state()

    def load_plugins(self):
        """利用可能なプラグインをロード"""
        for plugin_name in self.plugin_manager.discover_plugins():
            self.plugin_manager.load_plugin(plugin_name)
    
    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        # *** new_project メソッドを修正 ***
        file_menu.add_command(label="新規プロジェクト", command=self.new_project, accelerator=self.config_manager.get_shortcut_display('new_project'))
        # *** 修正ここまで ***
        file_menu.add_command(label="プロジェクトを開く", command=self.open_project, accelerator=self.config_manager.get_shortcut_display('open_project'))
        file_menu.add_command(label="プロジェクトを保存", command=self.save_project, accelerator=self.config_manager.get_shortcut_display('save_project'))
        file_menu.add_command(label="名前を付けて保存", command=self.save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="設定", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="シーンを追加", command=self.add_scene, accelerator=self.config_manager.get_shortcut_display('add_scene'))
        edit_menu.add_command(label="シーンを削除", command=self.delete_scene, accelerator=self.config_manager.get_shortcut_display('delete_scene'))
        menubar.add_cascade(label="編集", menu=edit_menu)

        character_menu = tk.Menu(menubar, tearoff=0)
        character_menu.add_command(label="キャラクター管理...", command=self.show_character_management)
        menubar.add_cascade(label="キャラクター", menu=character_menu)
        
        self.root.config(menu=menubar)
        self.menubar = menubar

    def create_widgets(self): 
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        self.canvas_frame = ttk.Frame(self.main_paned, width=800)
        self.canvas = tk.Canvas(self.canvas_frame, bg="white", scrollregion=(0, 0, 2000, 2000))
        
        self.hscroll = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.vscroll = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.hscroll.set, yscrollcommand=self.vscroll.set)
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.hscroll.grid(row=1, column=0, sticky="ew")
        self.vscroll.grid(row=0, column=1, sticky="ns")
        self.canvas_frame.grid_rowconfigure(0, weight=1); self.canvas_frame.grid_columnconfigure(0, weight=1)
        
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        
        self.editor_frame = ttk.Frame(self.main_paned, width=400)
        
        self.scene_info_frame = ttk.LabelFrame(self.editor_frame, text="シーン情報")
        self.scene_info_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)  
        
        ttk.Label(self.scene_info_frame, text="シーン名:").grid(row=0, column=0, sticky="w")
        self.scene_name_entry = ttk.Entry(self.scene_info_frame)
        self.scene_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(self.scene_info_frame, text="内容:").grid(row=1, column=0, sticky="nw")
        self.scene_content_text = tk.Text(self.scene_info_frame, height=20, wrap=tk.WORD) 
        self.scene_content_text.grid(row=1, column=1, sticky="nsew", padx=5, pady=2)
        self.scene_content_text.bind("<FocusOut>", self.on_scene_content_changed) 
        
        text_scroll = ttk.Scrollbar(self.scene_info_frame, orient=tk.VERTICAL, command=self.scene_content_text.yview)
        text_scroll.grid(row=1, column=2, sticky="ns")
        self.scene_content_text.config(yscrollcommand=text_scroll.set)
        
        self.scene_info_frame.grid_columnconfigure(1, weight=1); self.scene_info_frame.grid_rowconfigure(1, weight=1)
        
        # キャラクターボタン表示用フレームは update_editor_state() で動的に作成

        self.branch_frame = ttk.LabelFrame(self.editor_frame, text="分岐管理")
        self.branch_frame.pack(fill=tk.BOTH, padx=5, pady=5) 
        
        self.branch_tree = ttk.Treeview(self.branch_frame, columns=("text", "target", "condition"), show="headings", height=6) 
        self.branch_tree.heading("text", text="選択肢テキスト")
        self.branch_tree.heading("target", text="遷移先")
        self.branch_tree.heading("condition", text="条件")
        self.branch_tree.pack(fill=tk.BOTH, padx=5, pady=2)
        
        tree_scroll = ttk.Scrollbar(self.branch_frame, orient=tk.VERTICAL, command=self.branch_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.branch_tree.config(yscrollcommand=tree_scroll.set)
        
        button_frame = ttk.Frame(self.branch_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        self.add_branch_btn = ttk.Button(button_frame, text="分岐を追加", command=self.add_branch)
        self.add_branch_btn.pack(side=tk.LEFT, padx=2)
        self.edit_branch_btn = ttk.Button(button_frame, text="分岐を編集", command=self.edit_branch)
        self.edit_branch_btn.pack(side=tk.LEFT, padx=2)
        self.delete_branch_btn = ttk.Button(button_frame, text="分岐を削除", command=self.delete_branch)
        self.delete_branch_btn.pack(side=tk.LEFT, padx=2)
        
        self.scene_btn_frame = ttk.Frame(self.editor_frame)
        self.scene_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.add_scene_btn = ttk.Button(self.scene_btn_frame, text="シーンを追加", command=self.add_scene)
        self.add_scene_btn.pack(side=tk.LEFT, padx=2)
        self.delete_scene_btn = ttk.Button(self.scene_btn_frame, text="シーンを削除", command=self.delete_scene)
        self.delete_scene_btn.pack(side=tk.LEFT, padx=2)
        
        self.main_paned.add(self.canvas_frame, weight=3)
        self.main_paned.add(self.editor_frame, weight=1)
    
    def update_character_buttons(self):
        if not hasattr(self, 'character_button_frame'):
            self.character_button_frame = ttk.Frame(self.scene_info_frame)
            self.character_button_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=5, pady=5) 
            self.scene_info_frame.grid_rowconfigure(2, weight=0)
        else:
            for widget in self.character_button_frame.winfo_children(): widget.destroy()
        
        if self.selected_scene:
            ttk.Button(
                self.character_button_frame, text="ナレーション",
                command=lambda: self.insert_character_text('""', '""')
            ).pack(side=tk.LEFT, padx=2)

            for char in self.characters:
                if char.name == "ナレーション": continue 
                ttk.Button(
                    self.character_button_frame, text=char.name,
                    command=lambda c=char: self.insert_character_text(c.id, c.name)
                ).pack(side=tk.LEFT, padx=2)
    
    def insert_character_text(self, char_id_or_text: str, char_name: str):
        if self.scene_content_text.winfo_exists():
            if char_id_or_text == '""': insert_text = '""'
            else: insert_text = f'{char_id_or_text} "" '
            
            current_pos = self.scene_content_text.index(tk.INSERT)
            self.scene_content_text.insert(current_pos, insert_text)
            
            if char_id_or_text == '""': new_cursor_pos = f"{current_pos}.{len('""') - 1}"
            else: new_cursor_pos = f"{current_pos}.{len(char_id_or_text) + len(' "" ') - 2}"
            
            self.scene_content_text.mark_set(tk.INSERT, new_cursor_pos)
            self.scene_content_text.see(tk.INSERT)
            self.scene_content_text.focus_set()
        
    def show_character_management(self):
        CharacterManagementDialog(self.root, self)
        self.update_editor_state()

    def load_characters_from_project(self):
        self.characters.clear()
        if self.current_project:
            try:
                with open(self.current_project, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.characters = [Character.from_dict(char_data) for char_data in data.get("characters", [])]
            except Exception as e:
                print(f"キャラクターの読み込みに失敗しました: {e}"); self.characters = []

        if not any(char.name == "ナレーション" for char in self.characters):
            narration_char = Character(name="ナレーション", char_id=str(uuid.uuid4()), description="ナレーション用キャラクター")
            self.characters.insert(0, narration_char)

    def save_characters_to_project(self, data: Dict):
        data["characters"] = [char.to_dict() for char in self.characters]

    def open_project(self):
        file_path = filedialog.askopenfilename(
            title="プロジェクトを開く",
            filetypes=[("ノベルゲームプロジェクト", "*.ngp"), ("すべてのファイル", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.characters = [Character.from_dict(char_data) for char_data in data.get("characters", [])]
                    if not any(char.name == "ナレーション" for char in self.characters):
                        narration_char = Character(name="ナレーション", char_id=str(uuid.uuid4()), description="ナレーション用キャラクター")
                        self.characters.insert(0, narration_char)

                    self.scenes = [Scene.from_dict(scene_data) for scene_data in data["scenes"]]
                    self.current_project = file_path
                    
                    self.draw_scenes(); self.update_editor_state()
            except FileNotFoundError: messagebox.showerror("エラー", f"ファイル '{file_path}' が見つかりません。")
            except json.JSONDecodeError: messagebox.showerror("エラー", f"ファイル '{file_path}' は有効なJSON形式ではありません。")
            except Exception as e: messagebox.showerror("エラー", f"プロジェクトの読み込みに失敗しました:\n{str(e)}")
    
    def save_project(self):
        self._save_current_scene_content() 
        if self.current_project: self.save_to_file(self.current_project); return True
        else: return self.save_project_as()
    
    def save_project_as(self):
        self._save_current_scene_content()
        file_path = filedialog.asksaveasfilename(
            title="プロジェクトを保存",defaultextension=".ngp",
            filetypes=[("ノベルゲームプロジェクト", "*.ngp"), ("すべてのファイル", "*.*")]
        )
        if file_path: self.current_project = file_path; self.save_to_file(self.current_project); return True
        return False
    
    def save_to_file(self, file_path):
        data = {"scenes": [scene.to_dict() for scene in self.scenes]}
        self.save_characters_to_project(data)
        try:
            with open(file_path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e: messagebox.showerror("エラー", f"プロジェクトの保存に失敗しました:\n{str(e)}"); return False
    
    def add_scene(self):
        new_scene = Scene("新しいシーン", "", 100, 100)
        self.scenes.append(new_scene)
        self._save_current_scene_content()
        self.selected_scene = new_scene
        self.draw_scenes(); self.update_editor_state()
        self.scene_name_entry.focus_set(); self.scene_name_entry.select_range(0, tk.END)

    def delete_scene(self):
        if not self.selected_scene: return
        for scene in self.scenes: scene.branches = [b for b in scene.branches if b["target"] != self.selected_scene.id]
        self.scenes = [s for s in self.scenes if s.id != self.selected_scene.id]
        self.selected_scene = None
        self.draw_scenes(); self.update_editor_state()
    
    def add_branch(self):
        if not self.selected_scene: return
        dialog = BranchDialog(self.root, "分岐を追加", self.scenes, self.selected_scene)
        if dialog.result:
            self.selected_scene.add_branch(dialog.result["text"], dialog.result["target"], dialog.result["condition"])
            self.draw_scenes(); self.update_branch_list()
    
    def edit_branch(self):
        if not self.selected_scene or not self.branch_tree.selection(): return
        selected_item = self.branch_tree.selection()[0]
        branch_index = int(self.branch_tree.index(selected_item))
        branch = self.selected_scene.branches[branch_index]
        dialog = BranchDialog(self.root, "分岐を編集", self.scenes, self.selected_scene,
                              initial_text=branch["text"], initial_target=branch["target"], initial_condition=branch["condition"])
        if dialog.result:
            self.selected_scene.branches[branch_index] = {
                "text": dialog.result["text"], "target": dialog.result["target"], "condition": dialog.result["condition"]
            }
            self.draw_scenes(); self.update_branch_list()
    
    def delete_branch(self):
        if not self.selected_scene or not self.branch_tree.selection(): return
        selected_item = self.branch_tree.selection()[0]
        branch_index = int(self.branch_tree.index(selected_item))
        del self.selected_scene.branches[branch_index]
        self.draw_scenes(); self.update_branch_list()
    
    def update_branch_list(self):
        self.branch_tree.delete(*self.branch_tree.get_children())
        if self.selected_scene:
            for branch in self.selected_scene.branches:
                target_scene = next((s for s in self.scenes if s.id == branch["target"]), None)
                target_name = target_scene.name if target_scene else "不明なシーン"
                self.branch_tree.insert("", tk.END, values=(branch["text"], target_name, branch["condition"]))
            
            if self.selected_scene.branches:
                self.edit_branch_btn.config(state=tk.NORMAL); self.delete_branch_btn.config(state=tk.NORMAL)
            else:
                self.edit_branch_btn.config(state=tk.DISABLED); self.delete_branch_btn.config(state=tk.DISABLED)
    
    def draw_scenes(self):
        self.canvas.delete("all")
        scene_nodes = {}
        for scene in self.scenes:
            node_id = f"scene_{scene.id}"
            scene_nodes[scene.id] = node_id
            fill_color = "lightblue" if scene == self.selected_scene else "white"
            self.canvas.create_oval(
                scene.x - 50, scene.y - 30, scene.x + 50, scene.y + 30,
                fill=fill_color, outline="black", tags=(node_id, "scene_node")
            )
            self.canvas.create_text(
                scene.x, scene.y, text=scene.name, tags=(node_id, "scene_text")
            )
        
        for scene in self.scenes:
            for branch in scene.branches:
                if branch["target"] in scene_nodes:
                    start_x, start_y = scene.x, scene.y
                    end_scene = next(s for s in self.scenes if s.id == branch["target"])
                    end_x, end_y = end_scene.x, end_scene.y
                    
                    arrow_style = tk.LAST if start_x != end_x or start_y != end_y else None
                    line_id = self.canvas.create_line(
                        start_x, start_y, end_x, end_y,
                        arrow=arrow_style, tags=(scene_nodes[scene.id], scene_nodes[branch["target"]], "branch_line")
                    )
                    
                    mid_x = (start_x + end_x) / 2
                    mid_y = (start_y + end_y) / 2
                    
                    self.canvas.create_text(
                        mid_x, mid_y - 10, text=branch["text"], tags=(scene_nodes[scene.id], scene_nodes[branch["target"]], "branch_text")
                    )
                    if branch["condition"]:
                        self.canvas.create_text(
                            mid_x, mid_y + 10, text=f"[{branch['condition']}]",
                            font=("Arial", 9), tags=(scene_nodes[scene.id], scene_nodes[branch["target"]], "condition_text")
                        )
    
    def on_canvas_click(self, event):
        clicked_items = self.canvas.find_overlapping(event.x - 5, event.y - 5, event.x + 5, event.y + 5)
        scene_node_clicked = False; clicked_scene_id = None
        for item in clicked_items:
            tags = self.canvas.gettags(item)
            if "scene_node" in tags or "scene_text" in tags:
                scene_node_clicked = True
                for tag in tags:
                    if tag.startswith("scene_"): clicked_scene_id = tag.split("_")[1]; break
                break

        if scene_node_clicked and clicked_scene_id:
            new_selected_scene = next((s for s in self.scenes if s.id == clicked_scene_id), None)
            if new_selected_scene:
                self._save_current_scene_content() 
                self.selected_scene = new_selected_scene
                self.drag_data["item"] = self.selected_scene
                self.drag_data["x"] = event.x
                self.drag_data["y"] = event.y
                self.draw_scenes(); self.update_editor_state()
        else:
            self._save_current_scene_content() 
            self.drag_data["item"] = "background"
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
    
    def on_canvas_drag(self, event):
        if not self.drag_data["item"]: return
        if self.drag_data["item"] == "background":
            dx = event.x - self.drag_data["x"]; dy = event.y - self.drag_data["y"]
            self.canvas.xview_scroll(-dx, "units"); self.canvas.yview_scroll(-dy, "units")
            self.drag_data["x"] = event.x; self.drag_data["y"] = event.y
        elif isinstance(self.drag_data["item"], Scene):
            scene = self.drag_data["item"]
            dx = event.x - self.drag_data["x"]; dy = event.y - self.drag_data["y"]
            scene.x += dx; scene.y += dy
            self.drag_data["x"] = event.x; self.drag_data["y"] = event.y
            self.draw_scenes()
    
    def on_canvas_release(self, event):
        self.drag_data["item"] = None
    
    def on_canvas_double_click(self, event):
        clicked_items = self.canvas.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        for item in clicked_items:
            tags = self.canvas.gettags(item)
            if "scene_node" in tags or "scene_text" in tags:
                self._save_current_scene_content() 
                node_id = tags[0]
                scene_id = node_id.split("_")[1]
                self.selected_scene = next((s for s in self.scenes if s.id == scene_id), None)
                self.draw_scenes(); self.update_editor_state()
                break
    
    def on_mousewheel(self, event):
        zoom_factor = 1.1
        if event.delta == 120 or event.delta > 0 or (hasattr(event, 'num') and event.num == 4): scale = zoom_factor
        elif event.delta == -120 or event.delta < 0 or (hasattr(event, 'num') and event.num == 5): scale = 1 / zoom_factor
        else: return
        self.canvas.scale("all", event.x, event.y, scale, scale)
    
    def on_scene_content_changed(self, event=None):
        """シーン内容がフォーカスを失ったときに呼ばれる"""
        self._save_current_scene_content()

class BranchDialog(tk.Toplevel):
    def __init__(self, parent, title, scenes, source_scene, initial_text="", initial_target="", initial_condition=""):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        self.scenes = scenes
        self.source_scene = source_scene
        
        dialog_frame = ttk.Frame(self, padding="10")
        dialog_frame.grid(row=0, column=0, sticky="nsew")
        
        ttk.Label(dialog_frame, text="選択肢テキスト:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.text_entry = ttk.Entry(dialog_frame); self.text_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.text_entry.insert(0, initial_text)
        
        ttk.Label(dialog_frame, text="遷移先シーン:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.target_var = tk.StringVar()
        self.target_combo = ttk.Combobox(dialog_frame, textvariable=self.target_var, state="readonly")
        self.target_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        
        available_scenes = [s for s in scenes if s.id != source_scene.id]
        self.target_combo["values"] = [s.name for s in available_scenes]
        if initial_target:
            target_scene = next((s for s in scenes if s.id == initial_target), None)
            if target_scene and target_scene.id != source_scene.id:
                self.target_var.set(target_scene.name)
        
        ttk.Label(dialog_frame, text="条件 (任意):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.condition_entry = ttk.Entry(dialog_frame); self.condition_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        self.condition_entry.insert(0, initial_condition)
        
        button_frame = ttk.Frame(dialog_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
        dialog_frame.columnconfigure(1, weight=1)
        self.resizable(False, False)
        self.wait_window(self)
    
    def on_ok(self):
        text = self.text_entry.get().strip()
        target_name = self.target_var.get().strip()
        condition = self.condition_entry.get().strip()
        
        if not text: messagebox.showerror("エラー", "選択肢テキストを入力してください。", parent=self); return
        if not target_name: messagebox.showerror("エラー", "遷移先シーンを選択してください。", parent=self); return
            
        target_scene = next((s for s in self.scenes if s.name == target_name and s.id != self.source_scene.id), None)
        if not target_scene: messagebox.showerror("エラー", "無効な遷移先シーンです。", parent=self); return
            
        self.result = {"text": text, "target": target_scene.id, "condition": condition}
        self.destroy()
    
    def on_cancel(self): self.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = NovelGameEditor(root)
    root.mainloop()
