import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import uuid
import configparser
from tkinter import simpledialog
import importlib
import inspect
import os
from pathlib import Path
from typing import List, Dict, Type

class IPlugin:
    """プラグインインターフェース"""
    def __init__(self, app):
        self.app = app  # メインアプリケーションへの参照
    
    def setup(self):
        """プラグインの初期化"""
        pass
    
    def register(self):
        """機能の登録"""
        pass
    
    def teardown(self):
        """終了処理"""
        pass

class PluginManager:
    """プラグインマネージャー"""
    def __init__(self, app):
        self.app = app
        self.plugins: Dict[str, IPlugin] = {}
        self.plugin_dir = "plugins"
        
        # プラグインディレクトリがなければ作成
        os.makedirs(self.plugin_dir, exist_ok=True)
    
    def discover_plugins(self) -> List[str]:
        """利用可能なプラグインを探索"""
        plugin_files = Path(self.plugin_dir).glob("*.py")
        return [f.stem for f in plugin_files if f.is_file() and not f.name.startswith("_")]
    
    def load_plugin(self, plugin_name: str) -> bool:
        """プラグインをロード"""
        if plugin_name in self.plugins:
            return False
        
        try:
            module = importlib.import_module(f"{self.plugin_dir}.{plugin_name}")
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, IPlugin) and obj != IPlugin:
                    plugin = obj(self.app)
                    plugin.setup()
                    plugin.register()
                    self.plugins[plugin_name] = plugin
                    return True
        except Exception as e:
            print(f"プラグイン'{plugin_name}'のロードに失敗: {e}")
        return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """プラグインをアンロード"""
        if plugin_name not in self.plugins:
            return False
        
        try:
            self.plugins[plugin_name].teardown()
            del self.plugins[plugin_name]
            return True
        except Exception as e:
            print(f"プラグイン'{plugin_name}'のアンロードに失敗: {e}")
        return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """プラグインを再ロード"""
        self.unload_plugin(plugin_name)
        return self.load_plugin(plugin_name)

class ConfigManager:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = "config.ini"
        self.load_config()
    
    def load_config(self):
        # 修正後のデフォルト設定
        self.config['SHORTCUTS'] = {
            'new_project': 'Control-n',
            'open_project': 'Control-o',
            'save_project': 'Control-s',
            'add_scene': 'Control-a',
            'delete_scene': 'Control-d'
        }
        
        try:
            with open(self.config_file, 'r') as f:
                self.config.read_file(f)
        except FileNotFoundError:
            self.save_config()
    
    def save_config(self):
        with open(self.config_file, 'w') as f:
            self.config.write(f)
    
    def get_shortcut(self, action):
        return self.config['SHORTCUTS'].get(action, '')
    
    def get_shortcut_display(self, action):
        """メニュー表示用のショートカット文字列を返す"""
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
        
        # 新規プロジェクト
        ttk.Label(self, text="新規プロジェクト:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.new_project_entry = ttk.Entry(self)
        self.new_project_entry.grid(row=1, column=1, padx=5, pady=2)
        self.new_project_entry.insert(0, self.config_manager.get_shortcut('new_project'))
        
        # プロジェクトを開く
        ttk.Label(self, text="プロジェクトを開く:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.open_project_entry = ttk.Entry(self)
        self.open_project_entry.grid(row=2, column=1, padx=5, pady=2)
        self.open_project_entry.insert(0, self.config_manager.get_shortcut('open_project'))
        
        # プロジェクトを保存
        ttk.Label(self, text="プロジェクトを保存:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.save_project_entry = ttk.Entry(self)
        self.save_project_entry.grid(row=3, column=1, padx=5, pady=2)
        self.save_project_entry.insert(0, self.config_manager.get_shortcut('save_project'))
        
        # シーンを追加
        ttk.Label(self, text="シーンを追加:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.add_scene_entry = ttk.Entry(self)
        self.add_scene_entry.grid(row=4, column=1, padx=5, pady=2)
        self.add_scene_entry.insert(0, self.config_manager.get_shortcut('add_scene'))
        
        # シーンを削除
        ttk.Label(self, text="シーンを削除:").grid(row=5, column=0, sticky="w", padx=5, pady=2)
        self.delete_scene_entry = ttk.Entry(self)
        self.delete_scene_entry.grid(row=5, column=1, padx=5, pady=2)
        self.delete_scene_entry.insert(0, self.config_manager.get_shortcut('delete_scene'))
        
        # ボタンフレーム
        button_frame = ttk.Frame(self)
        button_frame.grid(row=6, column=0, columnspan=2, pady=5)
        
        ttk.Button(button_frame, text="保存", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def save_settings(self):
        self.config_manager.config['SHORTCUTS'] = {
            'new_project': self.new_project_entry.get(),
            'open_project': self.open_project_entry.get(),
            'save_project': self.save_project_entry.get(),
            'add_scene': self.add_scene_entry.get(),
            'delete_scene': self.delete_scene_entry.get()
        }
        self.config_manager.save_config()
        self.destroy()

class Scene:
    def __init__(self, name="New Scene", content="", x=0, y=0):
        self.id = str(uuid.uuid4())
        self.name = name
        self.content = content
        self.x = x
        self.y = y
        self.branches = []

    def add_branch(self, text, target_scene_id, condition=""):
        self.branches.append({
            "text": text,
            "target": target_scene_id,
            "condition": condition
        })

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "content": self.content,
            "x": self.x,
            "y": self.y,
            "branches": self.branches
        }

    @classmethod
    def from_dict(cls, data):
        scene = cls(data["name"], data["content"], data["x"], data["y"])
        scene.id = data["id"]
        scene.branches = data["branches"]
        return scene

class NovelGameEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("ノベルゲーム制作支援ツール")
        self.root.geometry("1200x800")

        self.toolbar_frame = ttk.Frame(self.root) # メインのツールバーフレームを作成
        self.toolbar_frame.pack(fill=tk.X, padx=5, pady=2) # ウィンドウに配置

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
        self.canvas.bind("<Button-3>", self.show_context_menu)

    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label="新規プロジェクト", 
            command=self.new_project,
            accelerator=self.config_manager.get_shortcut_display('new_project')
        )
        file_menu.add_command(
            label="プロジェクトを開く", 
            command=self.open_project,
            accelerator=self.config_manager.get_shortcut_display('open_project')
        )
        file_menu.add_command(
            label="プロジェクトを保存", 
            command=self.save_project,
            accelerator=self.config_manager.get_shortcut_display('save_project')
        )
        file_menu.add_command(
            label="名前を付けて保存", 
            command=self.save_project_as
        )
        file_menu.add_separator()
        file_menu.add_command(label="設定", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        
        # 編集メニュー
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(
            label="シーンを追加", 
            command=self.add_scene,
            accelerator=self.config_manager.get_shortcut('add_scene')
        )
        edit_menu.add_command(
            label="シーンを削除", 
            command=self.delete_scene,
            accelerator=self.config_manager.get_shortcut('delete_scene')
        )
        menubar.add_cascade(label="編集", menu=edit_menu)

        # プラグインメニュー
        if self.plugin_manager.plugins:
            plugin_menu = tk.Menu(menubar, tearoff=0)
            for name, plugin in self.plugin_manager.plugins.items():
                plugin_menu.add_command(label=name)
            menubar.add_cascade(label="プラグイン", menu=plugin_menu)
        
        self.root.config(menu=menubar)
    
    def create_widgets(self):
        # 分割フレーム
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # 左側 - キャンバス (分岐図)
        self.canvas_frame = ttk.Frame(self.main_paned, width=800)
        self.canvas = tk.Canvas(self.canvas_frame, bg="white", scrollregion=(0, 0, 2000, 2000))
        
        self.hscroll = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.vscroll = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.hscroll.set, yscrollcommand=self.vscroll.set)
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.hscroll.grid(row=1, column=0, sticky="ew")
        self.vscroll.grid(row=0, column=1, sticky="ns")
        
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        
        # キャンバスイベント
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        
        # 右側 - エディタ
        self.editor_frame = ttk.Frame(self.main_paned, width=400)
        
        # シーン情報フレーム（大きくする）
        self.scene_info_frame = ttk.LabelFrame(self.editor_frame, text="シーン情報")
        self.scene_info_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)  # fill=tk.BOTH, expand=Trueに変更
        
        ttk.Label(self.scene_info_frame, text="シーン名:").grid(row=0, column=0, sticky="w")
        self.scene_name_entry = ttk.Entry(self.scene_info_frame)
        self.scene_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(self.scene_info_frame, text="内容:").grid(row=1, column=0, sticky="nw")
        self.scene_content_text = tk.Text(self.scene_info_frame, height=20, wrap=tk.WORD)  # heightを15から20に増加
        self.scene_content_text.grid(row=1, column=1, sticky="nsew", padx=5, pady=2)
        
        # スクロールバーを追加
        text_scroll = ttk.Scrollbar(self.scene_info_frame, orient=tk.VERTICAL, command=self.scene_content_text.yview)
        text_scroll.grid(row=1, column=2, sticky="ns")
        self.scene_content_text.config(yscrollcommand=text_scroll.set)
        
        self.scene_info_frame.grid_columnconfigure(1, weight=1)
        self.scene_info_frame.grid_rowconfigure(1, weight=1)
        
        # 分岐管理フレーム（小さくする）
        self.branch_frame = ttk.LabelFrame(self.editor_frame, text="分岐管理")
        self.branch_frame.pack(fill=tk.BOTH, padx=5, pady=5)  # expand=Trueを削除
        
        self.branch_tree = ttk.Treeview(self.branch_frame, columns=("text", "target", "condition"), show="headings", height=6)  # heightを指定
        self.branch_tree.heading("text", text="選択肢テキスト")
        self.branch_tree.heading("target", text="遷移先")
        self.branch_tree.heading("condition", text="条件")
        self.branch_tree.pack(fill=tk.BOTH, padx=5, pady=2)
        
        # ツリービューのスクロールバーを追加
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
        
        # シーン操作ボタン
        self.scene_btn_frame = ttk.Frame(self.editor_frame)
        self.scene_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.add_scene_btn = ttk.Button(self.scene_btn_frame, text="シーンを追加", command=self.add_scene)
        self.add_scene_btn.pack(side=tk.LEFT, padx=2)
        
        self.delete_scene_btn = ttk.Button(self.scene_btn_frame, text="シーンを削除", command=self.delete_scene)
        self.delete_scene_btn.pack(side=tk.LEFT, padx=2)
        
        # パンウィンドウに追加
        self.main_paned.add(self.canvas_frame, weight=3)
        self.main_paned.add(self.editor_frame, weight=1)
        
        # 初期状態
        self.update_editor_state()

            
    def add_plugin_toolbar_button(self, text: str, command, image=None):
        """プラグインからツールバーボタンを追加"""
        btn = ttk.Button(self.toolbar_frame, text=text, command=command)
        if image:
            # ここで画像の設定を行う（例: PhotoImageなど）
            btn.config(image=image, compound=tk.LEFT) # 画像とテキストを横並びにする場合
        btn.pack(side=tk.LEFT, padx=2)
        return btn # ボタンオブジェクトを返す（必要であれば）

    def add_plugin_menu(self, label: str, command, parent_menu_label="プラグイン"):
        """プラグインからメニューを追加"""
        # メニューバーが存在するか確認
        if not hasattr(self, 'menubar'):
            # メニューバーがまだ作成されていない場合は、ここで作成し、再度メニュー追加を試みる
            # (ただし、これはより複雑な処理になる可能性があるため、通常はcreate_menuで最初に作る)
            # 一旦ここでは、既にmenubarがあることを前提とします。
            print("Error: Menubar not created yet.")
            return

        # 指定された親メニューラベルを持つメニューを探す
        plugin_menu = None
        for i, menu in enumerate(self.menubar.winfo_children()):
            if isinstance(menu, tk.Menu) and menu.cget('title') == parent_menu_label:
                plugin_menu = menu
                break
        
        # 親メニューが存在しない場合は新規作成
        if plugin_menu is None:
            plugin_menu = tk.Menu(self.menubar, tearoff=0, title=parent_menu_label)
            self.menubar.add_cascade(label=parent_menu_label, menu=plugin_menu)
            # Note: メニューバーの構造によっては、追加する順序も重要になる場合があります。
            # ここでは単純に追加していますが、必要に応じてメニューバーの構造を操作する必要があります。

        plugin_menu.add_command(label=label, command=command)
    
    def add_plugin_toolbar_button(self, text: str, command, image=None):
        """プラグインからツールバーボタンを追加"""
        btn = ttk.Button(self.toolbar_frame, text=text, command=command)
        if image:
            btn.config(image=image)
        btn.pack(side=tk.LEFT, padx=2)
        return btn

    def load_plugins(self):
        """利用可能なプラグインをロード"""
        for plugin_name in self.plugin_manager.discover_plugins():
            self.plugin_manager.load_plugin(plugin_name)
    
    def setup_shortcuts(self):
        # ショートカットキーの設定
        shortcuts = {
            self.config_manager.get_shortcut('new_project'): self.new_project,
            self.config_manager.get_shortcut('open_project'): self.open_project,
            self.config_manager.get_shortcut('save_project'): self.save_project,
            self.config_manager.get_shortcut('add_scene'): self.add_scene,
            self.config_manager.get_shortcut('delete_scene'): self.delete_scene
        }
        
        for shortcut, command in shortcuts.items():
            if shortcut:
                self.root.bind(f"<{shortcut}>", lambda e, cmd=command: cmd())
    
    def show_context_menu(self, event):
        """右クリックメニューを表示"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label="シーンを追加", 
            command=lambda: self.on_canvas_right_click(event),
            accelerator=self.config_manager.get_shortcut('add_scene')
        )
        menu.add_separator()
        menu.add_command(label="設定", command=self.show_settings)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def show_settings(self):
        """設定ダイアログを表示"""
        SettingsDialog(self.root, self.config_manager)
        # 設定変更後、ショートカットを再設定
        self.setup_shortcuts()

    def on_scene_name_changed(self, event):
        """シーン名が変更された時の処理"""
        if self.selected_scene:
            new_name = self.scene_name_entry.get().strip()
            if new_name and new_name != self.selected_scene.name:
                self.selected_scene.name = new_name
                self.draw_scenes()  # 分岐図を再描画して新しい名前を反映

    def update_editor_state(self):
        """エディタの状態を更新"""
        if self.selected_scene:
            self.scene_name_entry.config(state=tk.NORMAL)
            self.scene_content_text.config(state=tk.NORMAL)
            
            # 現在のシーン名を取得（直接オブジェクトから）
            current_name = self.selected_scene.name
            current_content = self.selected_scene.content
            
            # エントリーの内容と実際の値が異なる場合のみ更新
            if self.scene_name_entry.get() != current_name:
                self.scene_name_entry.delete(0, tk.END)
                self.scene_name_entry.insert(0, current_name)
            
            if self.scene_content_text.get("1.0", tk.END).strip() != current_content:
                self.scene_content_text.delete("1.0", tk.END)
                self.scene_content_text.insert("1.0", current_content)
        

        
    def on_canvas_right_click(self, event):
        """右クリックで新しいシーンを作成"""
        # キャンバス座標から実際の座標に変換
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        new_scene = Scene("新しいシーン", "", x, y)
        self.scenes.append(new_scene)
        self.selected_scene = new_scene
        self.draw_scenes()
        self.update_editor_state()
        
        # シーン名の編集をすぐに開始できるようにフォーカスを設定
        self.scene_name_entry.focus_set()
        self.scene_name_entry.select_range(0, tk.END)
    
    def new_project(self):
        self.current_project = None
        self.scenes = []
        self.selected_scene = None
        self.draw_scenes()
        self.update_editor_state()
    
    def open_project(self):
        file_path = filedialog.askopenfilename(
            title="プロジェクトを開く",
            filetypes=[("ノベルゲームプロジェクト", "*.ngp"), ("すべてのファイル", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.scenes = [Scene.from_dict(scene_data) for scene_data in data["scenes"]]
                    self.current_project = file_path
                    self.draw_scenes()
                    self.update_editor_state()
            except Exception as e:
                messagebox.showerror("エラー", f"プロジェクトの読み込みに失敗しました:\n{str(e)}")
    
    def save_project(self):
        if self.current_project:
            self.save_to_file(self.current_project)
        else:
            self.save_project_as()
    
    def save_project_as(self):
        file_path = filedialog.asksaveasfilename(
            title="プロジェクトを保存",
            defaultextension=".ngp",
            filetypes=[("ノベルゲームプロジェクト", "*.ngp"), ("すべてのファイル", "*.*")]
        )
        
        if file_path:
            self.current_project = file_path
            self.save_project()
    
    def save_to_file(self, file_path):
        data = {
            "scenes": [scene.to_dict() for scene in self.scenes]
        }
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("エラー", f"プロジェクトの保存に失敗しました:\n{str(e)}")
    
    def add_scene(self):
        new_scene = Scene("新しいシーン", "", 100, 100)
        self.scenes.append(new_scene)
        self.selected_scene = new_scene
        self.draw_scenes()
        self.update_editor_state()
    
    def delete_scene(self):
        if not self.selected_scene:
            return
            
        # 他のシーンからこのシーンへの参照を削除
        for scene in self.scenes:
            scene.branches = [b for b in scene.branches if b["target"] != self.selected_scene.id]
        
        # シーンを削除
        self.scenes = [s for s in self.scenes if s.id != self.selected_scene.id]
        self.selected_scene = None
        self.draw_scenes()
        self.update_editor_state()
    
    def add_branch(self):
        if not self.selected_scene:
            return
            
        dialog = BranchDialog(self.root, "分岐を追加", self.scenes, self.selected_scene)
        if dialog.result:
            self.selected_scene.add_branch(dialog.result["text"], dialog.result["target"], dialog.result["condition"])
            self.draw_scenes()
            self.update_branch_list()
    
    def edit_branch(self):
        if not self.selected_scene or not self.branch_tree.selection():
            return
            
        selected_item = self.branch_tree.selection()[0]
        branch_index = int(self.branch_tree.index(selected_item))
        branch = self.selected_scene.branches[branch_index]
        
        dialog = BranchDialog(
            self.root, 
            "分岐を編集", 
            self.scenes, 
            self.selected_scene,
            initial_text=branch["text"],
            initial_target=branch["target"],
            initial_condition=branch["condition"]
        )
        
        if dialog.result:
            self.selected_scene.branches[branch_index] = {
                "text": dialog.result["text"],
                "target": dialog.result["target"],
                "condition": dialog.result["condition"]
            }
            self.draw_scenes()
            self.update_branch_list()
    
    def delete_branch(self):
        if not self.selected_scene or not self.branch_tree.selection():
            return
            
        selected_item = self.branch_tree.selection()[0]
        branch_index = int(self.branch_tree.index(selected_item))
        del self.selected_scene.branches[branch_index]
        self.draw_scenes()
        self.update_branch_list()
    
    def update_editor_state(self):
        # シーン情報を更新
        if self.selected_scene:
            self.scene_name_entry.config(state=tk.NORMAL)
            self.scene_content_text.config(state=tk.NORMAL)
            
            self.scene_name_entry.delete(0, tk.END)
            self.scene_name_entry.insert(0, self.selected_scene.name)
            
            self.scene_content_text.delete(1.0, tk.END)
            self.scene_content_text.insert(1.0, self.selected_scene.content)
            
            self.delete_scene_btn.config(state=tk.NORMAL)
            self.add_branch_btn.config(state=tk.NORMAL)
            self.update_branch_list()
        else:
            self.scene_name_entry.config(state=tk.DISABLED)
            self.scene_content_text.config(state=tk.DISABLED)
            
            self.scene_name_entry.delete(0, tk.END)
            self.scene_content_text.delete(1.0, tk.END)
            
            self.delete_scene_btn.config(state=tk.DISABLED)
            self.add_branch_btn.config(state=tk.DISABLED)
            self.edit_branch_btn.config(state=tk.DISABLED)
            self.delete_branch_btn.config(state=tk.DISABLED)
            self.branch_tree.delete(*self.branch_tree.get_children())
    
    def update_branch_list(self):
        self.branch_tree.delete(*self.branch_tree.get_children())
        
        if self.selected_scene:
            for branch in self.selected_scene.branches:
                target_scene = next((s for s in self.scenes if s.id == branch["target"]), None)
                target_name = target_scene.name if target_scene else "不明なシーン"
                self.branch_tree.insert("", tk.END, values=(branch["text"], target_name, branch["condition"]))
            
            if self.selected_scene.branches:
                self.edit_branch_btn.config(state=tk.NORMAL)
                self.delete_branch_btn.config(state=tk.NORMAL)
            else:
                self.edit_branch_btn.config(state=tk.DISABLED)
                self.delete_branch_btn.config(state=tk.DISABLED)
    
    def draw_scenes(self):
        self.canvas.delete("all")
        
        # シーンノードを描画
        scene_nodes = {}
        for scene in self.scenes:
            node_id = f"scene_{scene.id}"
            scene_nodes[scene.id] = node_id
            
            # ノードの背景
            fill_color = "lightblue" if scene == self.selected_scene else "white"
            self.canvas.create_oval(
                scene.x - 50, scene.y - 30,
                scene.x + 50, scene.y + 30,
                fill=fill_color, outline="black", tags=(node_id, "scene_node")
            )
            
            # シーン名
            self.canvas.create_text(
                scene.x, scene.y,
                text=scene.name, tags=(node_id, "scene_text")
            )
        
        # 分岐を描画
        for scene in self.scenes:
            for branch in scene.branches:
                if branch["target"] in scene_nodes:
                    start_node = scene_nodes[scene.id]
                    end_node = scene_nodes[branch["target"]]
                    
                    # 開始シーンと終了シーンの座標を取得
                    start_x, start_y = scene.x, scene.y
                    end_scene = next(s for s in self.scenes if s.id == branch["target"])
                    end_x, end_y = end_scene.x, end_scene.y
                    
                    # 線を描画
                    arrow = tk.LAST if start_x != end_x or start_y != end_y else None
                    line_id = self.canvas.create_line(
                        start_x, start_y + 30,
                        end_x, end_y - 30,
                        arrow=arrow, tags="branch_line"
                    )
                    
                    # 分岐テキスト
                    mid_x = (start_x + end_x) / 2
                    mid_y = (start_y + end_y) / 2
                    text_id = self.canvas.create_text(
                        mid_x, mid_y,
                        text=branch["text"], tags="branch_text"
                    )
                    
                    # 条件テキスト（条件がある場合）
                    if branch["condition"]:
                        cond_id = self.canvas.create_text(
                            mid_x, mid_y + 15,
                            text=f"[条件: {branch['condition']}]",
                            font=("Arial", 8), tags="condition_text"
                        )
    
    def on_canvas_click(self, event):
        # シーンノードがクリックされたかチェック
        clicked_items = self.canvas.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        
        scene_node_clicked = False
        for item in clicked_items:
            tags = self.canvas.gettags(item)
            if "scene_node" in tags or "scene_text" in tags:
                scene_node_clicked = True
                node_id = tags[0]
                scene_id = node_id.split("_")[1]
                self.selected_scene = next((s for s in self.scenes if s.id == scene_id), None)
                break
        
        if scene_node_clicked:
            self.drag_data["item"] = self.selected_scene
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
            self.draw_scenes()
            self.update_editor_state()
        else:
            # 背景がクリックされた場合、パン操作を開始
            self.drag_data["item"] = "background"
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
    
    def on_canvas_drag(self, event):
        if not self.drag_data["item"]:
            return
            
        if self.drag_data["item"] == "background":
            # 背景のパン操作
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            self.canvas.xview_scroll(-dx, "units")
            self.canvas.yview_scroll(-dy, "units")
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
        elif isinstance(self.drag_data["item"], Scene):
            # シーンの移動
            scene = self.drag_data["item"]
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            scene.x += dx
            scene.y += dy
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
            self.draw_scenes()
    
    def on_canvas_release(self, event):
        self.drag_data["item"] = None
    
    def on_canvas_double_click(self, event):
        clicked_items = self.canvas.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        
        for item in clicked_items:
            tags = self.canvas.gettags(item)
            if "scene_node" in tags or "scene_text" in tags:
                node_id = tags[0]
                scene_id = node_id.split("_")[1]
                self.selected_scene = next((s for s in self.scenes if s.id == scene_id), None)
                self.draw_scenes()
                self.update_editor_state()
                break
    
    def on_mousewheel(self, event):
        # ズーム機能（WindowsとMac/Linuxでイベントの扱いが異なる）
        if event.num == 5 or event.delta == -120:
            self.canvas.scale("all", event.x, event.y, 0.9, 0.9)
        if event.num == 4 or event.delta == 120:
            self.canvas.scale("all", event.x, event.y, 1.1, 1.1)

class BranchDialog(tk.Toplevel):
    def __init__(self, parent, title, scenes, source_scene, initial_text="", initial_target="", initial_condition=""):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        self.scenes = scenes
        self.source_scene = source_scene
        
        # ウィジェット作成
        ttk.Label(self, text="選択肢テキスト:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.text_entry = ttk.Entry(self)
        self.text_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.text_entry.insert(0, initial_text)
        
        ttk.Label(self, text="遷移先シーン:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.target_var = tk.StringVar()
        self.target_combo = ttk.Combobox(self, textvariable=self.target_var)
        self.target_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        
        # 遷移先候補を設定（現在のシーンと自分自身は除外）
        available_scenes = [s for s in scenes if s != source_scene]
        self.target_combo["values"] = [s.name for s in available_scenes]
        if initial_target:
            target_scene = next((s for s in scenes if s.id == initial_target), None)
            if target_scene and target_scene in available_scenes:
                self.target_var.set(target_scene.name)
        
        ttk.Label(self, text="条件 (任意):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.condition_entry = ttk.Entry(self)
        self.condition_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        self.condition_entry.insert(0, initial_condition)
        
        button_frame = ttk.Frame(self)
        button_frame.grid(row=3, column=0, columnspan=2, pady=5)
        
        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
        self.columnconfigure(1, weight=1)
        self.resizable(False, False)
        self.wait_window(self)
    
    def on_ok(self):
        text = self.text_entry.get().strip()
        target_name = self.target_var.get().strip()
        condition = self.condition_entry.get().strip()
        
        if not text:
            messagebox.showerror("エラー", "選択肢テキストを入力してください")
            return
            
        if not target_name:
            messagebox.showerror("エラー", "遷移先シーンを選択してください")
            return
            
        target_scene = next((s for s in self.scenes if s.name == target_name and s != self.source_scene), None)
        if not target_scene:
            messagebox.showerror("エラー", "無効な遷移先シーンです")
            return
            
        self.result = {
            "text": text,
            "target": target_scene.id,
            "condition": condition
        }
        self.destroy()
    
    def on_cancel(self):
        self.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = NovelGameEditor(root)
    root.mainloop()
