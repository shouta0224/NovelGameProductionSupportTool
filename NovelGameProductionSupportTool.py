import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import uuid
import configparser
import importlib
import inspect
import os
from pathlib import Path
from typing import List, Dict, Type, Optional, Any

# --- プラグイン関連 ---

class IPlugin:
    """
    プラグインの基底クラス。
    すべてのプラグインはこのクラスを継承し、必須メソッドを実装する必要があります。
    """
    def __init__(self, app: 'NovelGameEditor'):
        """
        プラグインを初期化します。

        Args:
            app (NovelGameEditor): メインアプリケーションのインスタンス。
        """
        self.app = app
        # プラグイン固有の初期化処理はここで開始できます。
        # ただし、registerメソッドで具体的な機能登録を行うのが一般的です。

    def setup(self) -> None:
        """
        プラグインのセットアップ処理を行います。
        GUI要素の追加や、アプリケーションの状態変更など、
        プラグインの初期動作をここに記述します。
        """
        pass # デフォルトは何も行わない

    def register(self) -> None:
        """
        アプリケーションの機能（メニュー、ツールバーボタン、イベントハンドラなど）に
        プラグインの機能を登録します。
        """
        pass # デフォルトは何も行わない

    def teardown(self) -> None:
        """
        プラグインのアンロード時のクリーンアップ処理を行います。
        リソースの解放など、終了時の処理をここに記述します。
        """
        pass # デフォルトは何も行わない

class PluginManager:
    """
    プラグインの発見、ロード、アンロード、リロードを管理するクラス。
    指定されたディレクトリからプラグインを読み込み、アプリケーションに統合します。
    """
    def __init__(self, app: 'NovelGameEditor'):
        """
        PluginManager を初期化します。

        Args:
            app (NovelGameEditor): メインアプリケーションのインスタンス。
        """
        self.app = app
        self.plugins: Dict[str, IPlugin] = {}
        self.plugin_dir = Path("plugins") # プラグインディレクトリのパス

        # プラグインディレクトリが存在しない場合は作成する
        self.plugin_dir.mkdir(exist_ok=True)

    def discover_plugins(self) -> List[str]:
        """
        プラグインディレクトリ内の利用可能なプラグインファイルを探索します。
        ファイル名は拡張子(.py)を除いたものがプラグイン名となります。

        Returns:
            List[str]: 発見されたプラグイン名のリスト。
        """
        plugin_files = self.plugin_dir.glob("*.py")
        # ファイル名が'_'で始まらないPythonファイルをプラグイン候補とする
        return [f.stem for f in plugin_files if f.is_file() and not f.name.startswith("_")]

    def load_plugin(self, plugin_name: str) -> bool:
        """
        指定された名前のプラグインをロードします。
        プラグインファイルを見つけ、`IPlugin` を継承したクラスのインスタンスを作成し、
        `setup` および `register` メソッドを呼び出します。

        Args:
            plugin_name (str): ロードするプラグインの名前（ファイル名から`.py`を除いたもの）。

        Returns:
            bool: プラグインのロードに成功した場合はTrue、失敗した場合はFalse。
        """
        if plugin_name in self.plugins:
            print(f"プラグイン'{plugin_name}'は既にロードされています。")
            return False

        module_path = f"{self.plugin_dir}.{plugin_name}"
        try:
            # プラグインモジュールをインポート
            # Pythonのパスにプラグインディレクトリを追加する必要がある場合がある
            # sys.path.insert(0, str(self.plugin_dir)) # 必要に応じて
            module = importlib.import_module(module_path)

            # モジュール内のIPluginを継承したクラスを検索
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, IPlugin) and obj != IPlugin:
                    # プラグインクラスのインスタンスを作成し、セットアップと登録を行う
                    plugin_instance = obj(self.app)
                    plugin_instance.setup()
                    plugin_instance.register()
                    self.plugins[plugin_name] = plugin_instance
                    print(f"プラグイン'{plugin_name}'をロードしました。")
                    return True # 1つのファイルに複数のプラグインがある場合でも、最初に見つかったものをロードする

        except ImportError:
            print(f"プラグイン'{plugin_name}'が見つかりません。パス: {self.plugin_dir}/{plugin_name}.py")
        except Exception as e:
            print(f"プラグイン'{plugin_name}'のロード中にエラーが発生しました: {e}")

        return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        指定された名前のプラグインをアンロードします。
        プラグインの `teardown` メソッドを呼び出し、インスタンスを削除します。

        Args:
            plugin_name (str): アンロードするプラグインの名前。

        Returns:
            bool: プラグインのアンロードに成功した場合はTrue、失敗した場合はFalse。
        """
        if plugin_name not in self.plugins:
            print(f"プラグイン'{plugin_name}'はロードされていません。")
            return False

        try:
            self.plugins[plugin_name].teardown()
            del self.plugins[plugin_name]
            print(f"プラグイン'{plugin_name}'をアンロードしました。")
            return True
        except Exception as e:
            print(f"プラグイン'{plugin_name}'のアンロード中にエラーが発生しました: {e}")
            return False

    def reload_plugin(self, plugin_name: str) -> bool:
        """
        指定された名前のプラグインを再ロードします。
        まずアンロードし、その後再度ロードを試みます。

        Args:
            plugin_name (str): 再ロードするプラグインの名前。

        Returns:
            bool: プラグインの再ロードに成功した場合はTrue、失敗した場合はFalse。
        """
        print(f"プラグイン'{plugin_name}'を再ロードします。")
        # まずアンロードを試みる
        unloaded = self.unload_plugin(plugin_name)
        # ロードを試みる
        loaded = self.load_plugin(plugin_name)
        return unloaded and loaded

# --- 設定管理 ---

class ConfigManager:
    """
    アプリケーションの設定（ショートカットキーなど）を管理するクラス。
    設定は `config.ini` ファイルに保存・ロードされます。
    """
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = Path("config.ini")
        self._load_config() # 初期化時に設定をロード

    def _load_config(self) -> None:
        """
        設定ファイルをロードします。ファイルが存在しない場合はデフォルト設定で初期化します。
        """
        # デフォルトのショートカット設定
        default_shortcuts = {
            'new_project': 'Control-n',
            'open_project': 'Control-o',
            'save_project': 'Control-s',
            'add_scene': 'Control-a',
            'delete_scene': 'Control-d'
        }
        
        # ConfigParserにデフォルトセクションと値を設定
        if not self.config.has_section('SHORTCUTS'):
            self.config.add_section('SHORTCUTS')
        for key, value in default_shortcuts.items():
            # 設定ファイルにキーが存在しない場合のみデフォルト値を設定
            if not self.config.has_option('SHORTCUTS', key):
                self.config.set('SHORTCUTS', key, value)

        try:
            # 設定ファイルを読み込む
            self.config.read(self.config_file)
            # 読み込んだ後、デフォルト値との差分があれば上書き保存する
            # これは、config.ini が存在し、一部キーが欠落している場合に対応するため
            for key, value in default_shortcuts.items():
                if not self.config.has_option('SHORTCUTS', key):
                    self.config.set('SHORTCUTS', key, value)
            self._save_config() # 整合性のために保存
        except FileNotFoundError:
            # ファイルが存在しない場合はデフォルト設定で上書き保存
            print(f"設定ファイル '{self.config_file}' が見つかりませんでした。デフォルト設定で作成します。")
            self._save_config()
        except Exception as e:
            print(f"設定ファイルの読み込み中にエラーが発生しました: {e}")
            # エラー時もデフォルト設定を維持またはロードする

    def _save_config(self) -> None:
        """
        現在の設定を `config.ini` ファイルに保存します。
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            # print(f"設定を '{self.config_file}' に保存しました。") # 毎回保存されると冗長なのでコメントアウト
        except Exception as e:
            print(f"設定ファイルの保存中にエラーが発生しました: {e}")

    def get_shortcut(self, action: str) -> str:
        """
        指定されたアクションに対応するショートカットキー文字列を取得します。

        Args:
            action (str): 取得したいショートカットのアクション名（例: 'new_project'）。

        Returns:
            str: ショートカットキー文字列（例: 'Control-n'）。設定されていない場合は空文字。
        """
        return self.config.get('SHORTCUTS', action, fallback='')

    def set_shortcut(self, action: str, shortcut: str) -> None:
        """
        指定されたアクションのショートカットキーを設定し、設定ファイルを保存します。

        Args:
            action (str): 設定したいショートカットのアクション名。
            shortcut (str): 設定するショートカットキー文字列（例: 'Control-n'）。
        """
        if not self.config.has_section('SHORTCUTS'):
            self.config.add_section('SHORTCUTS')
        self.config.set('SHORTCUTS', action, shortcut)
        self._save_config()

    def get_shortcut_display(self, action: str) -> str:
        """
        メニュー表示用のショートカット文字列を生成します。
        (例: 'Control-n' -> 'Ctrl+N')

        Args:
            action (str): ショートカットのアクション名。

        Returns:
            str: メニュー表示用の整形済みショートカット文字列。
        """
        shortcut = self.get_shortcut(action)
        # 表示用フォーマットに変換
        return shortcut.replace('Control-', 'Ctrl+').title()

# --- 設定ダイアログ ---

class SettingsDialog(tk.Toplevel):
    """
    ショートカットキーなどのアプリケーション設定を変更するためのダイアログ。
    """
    def __init__(self, parent: tk.Tk, config_manager: ConfigManager):
        """
        SettingsDialog を初期化します。

        Args:
            parent (tk.Tk): 親ウィジェット（メインウィンドウ）。
            config_manager (ConfigManager): 設定を管理するインスタンス。
        """
        super().__init__(parent)
        self.title("設定")
        self.config_manager = config_manager
        self.transient(parent) # 親ウィンドウの上に表示
        self.grab_set() # モーダルダイアログとして設定

        self._create_widgets()
        self.resizable(False, False) # サイズ変更不可にする
        self.wait_window(self) # ウィンドウが閉じられるまで待機

    def _create_widgets(self) -> None:
        """
        ダイアログのウィジェットを作成し配置します。
        """
        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ttk.Label(main_frame, text="ショートカットキー設定", font="-weight bold").grid(
            row=0, column=0, columnspan=2, pady=10
        )

        # ショートカット設定項目を動的に作成する
        shortcut_actions = {
            'new_project': "新規プロジェクト",
            'open_project': "プロジェクトを開く",
            'save_project': "プロジェクトを保存",
            'add_scene': "シーンを追加",
            'delete_scene': "シーンを削除"
        }
        
        row_num = 1
        # 各エントリーウィジェットを格納するための辞書
        self.shortcut_entry_widgets = {}
        
        for action_key, action_label in shortcut_actions.items():
            ttk.Label(main_frame, text=f"{action_label}:").grid(
                row=row_num, column=0, sticky=tk.W, padx=5, pady=2
            )
            entry = ttk.Entry(main_frame, width=30)
            entry.grid(row=row_num, column=1, padx=5, pady=2)
            entry.insert(0, self.config_manager.get_shortcut(action_key))
            # 各エントリーを後で参照できるように辞書に格納
            self.shortcut_entry_widgets[action_key] = entry
            row_num += 1

        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row_num, column=0, columnspan=2, pady=15)

        ttk.Button(button_frame, text="保存", command=self._save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _save_settings(self) -> None:
        """
        入力されたショートカットキー設定を保存します。
        """
        settings_changed = False
        # 設定ダイアログに表示されているエントリーから値を読み取る
        for action_key, entry_widget in self.shortcut_entry_widgets.items():
            new_shortcut = entry_widget.get().strip()
            current_shortcut = self.config_manager.get_shortcut(action_key)
            
            # 設定が変更された場合のみ更新・保存
            if new_shortcut != current_shortcut:
                self.config_manager.set_shortcut(action_key, new_shortcut)
                settings_changed = True
        
        # 設定が変更された場合、親ウィンドウのショートカットを再設定
        if settings_changed and hasattr(self.master, 'setup_shortcuts'):
            self.master.setup_shortcuts() # 親ウィジェットのメソッドを呼び出す
        
        self.destroy() # ダイアログを閉じる

# --- データ構造 ---

class Scene:
    """
    ノベルゲームの1シーンを表すクラス。
    シーン名、内容、位置情報、分岐情報を保持します。
    """
    def __init__(self, name: str = "New Scene", content: str = "", x: float = 0.0, y: float = 0.0):
        """
        Scene を初期化します。

        Args:
            name (str): シーンの名前。デフォルトは "New Scene"。
            content (str): シーンの本文テキスト。
            x (float): 分岐図上でのシーンノードの中心X座標。
            y (float): 分岐図上でのシーンノードの中心Y座標。
        """
        self.id: str = str(uuid.uuid4()) # 各シーンに一意のIDを付与
        self.name: str = name
        self.content: str = content
        self.x: float = float(x) # 座標はfloat型で保持
        self.y: float = float(y)
        # 分岐情報はリストで保持。各要素は辞書。
        # {"text": "選択肢テキスト", "target": "遷移先シーンID", "condition": "条件テキスト"}
        self.branches: List[Dict[str, str]] = []

    def add_branch(self, text: str, target_scene_id: str, condition: str = "") -> None:
        """
        このシーンに新しい分岐を追加します。

        Args:
            text (str): プレイヤーに表示される選択肢のテキスト。
            target_scene_id (str): 遷移先のシーンのID。
            condition (str, optional): 分岐の出現条件や遷移条件となるテキスト。デフォルトは空文字列。
        """
        self.branches.append({
            "text": text,
            "target": target_scene_id,
            "condition": condition
        })

    def to_dict(self) -> Dict[str, Any]:
        """
        シーンオブジェクトを辞書形式に変換します。JSON保存用です。

        Returns:
            Dict[str, Any]: シーンのデータを保持する辞書。
        """
        return {
            "id": self.id,
            "name": self.name,
            "content": self.content,
            "x": self.x,
            "y": self.y,
            "branches": self.branches
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scene':
        """
        辞書形式のデータからSceneオブジェクトを生成します。JSONロード用です。

        Args:
            data (Dict[str, Any]): シーンデータを格納した辞書。

        Returns:
            Scene: 生成されたSceneオブジェクト。
        """
        scene = cls(data.get("name", "Unnamed Scene"), data.get("content", ""), data.get("x", 0.0), data.get("y", 0.0))
        scene.id = data.get("id", str(uuid.uuid4())) # IDがなければ新規生成
        scene.branches = data.get("branches", [])
        return scene

# --- メインアプリケーションクラス ---

class NovelGameEditor:
    """
    ノベルゲーム制作支援ツールのメインアプリケーションクラス。
    GUIの構築、プロジェクト管理、シーン編集、分岐設定、描画などを担当します。
    """
    # 定数定義 (例: キャンバス上のノードサイズ)
    NODE_RADIUS = 30
    NODE_WIDTH = NODE_RADIUS * 2
    NODE_HEIGHT = NODE_RADIUS * 2

    def __init__(self, root: tk.Tk):
        """
        NovelGameEditor を初期化します。

        Args:
            root (tk.Tk): アプリケーションのルートウィンドウ。
        """
        self.root = root
        self.root.title("ノベルゲーム制作支援ツール")
        self.root.geometry("1200x800")

        # --- 初期化 ---
        self.plugin_manager = PluginManager(self)
        self._load_plugins() # プラグインをロード
        
        self.config_manager = ConfigManager()
        
        self.current_project_path: Optional[Path] = None # 現在開いているプロジェクトのファイルパス
        self.scenes: List[Scene] = [] # プロジェクト内のシーンのリスト
        self.selected_scene: Optional[Scene] = None # 現在選択中のシーンオブジェクト

        # ドラッグ操作のための状態管理
        self.drag_state: Dict[str, Any] = {
            "is_dragging": False,
            "item_type": None, # 'scene', 'background'
            "item_id": None,   # ドラッグ中のシーンIDなど
            "start_x": 0,
            "start_y": 0
        }
        
        # エディタフレーム内のシーン操作ボタンへの参照を初期化
        self.add_scene_btn = None
        self.delete_scene_btn = None
        
        # --- ウィジェットの作成 ---
        self._create_menu() # メニューバーを作成
        self._create_toolbar() # ツールバーを作成
        self._create_main_layout() # メインのレイアウト（キャンバスとエディタ）を作成
        self._bind_events() # イベントハンドラをバインド

        # 初期状態のUI更新
        self._update_editor_ui_state()
        self.root.update_idletasks() # ウィンドウの更新を強制

    def _create_menu(self) -> None:
        """メニューバーを作成し、ウィンドウに設定します。"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar) # メニューバーをウィンドウに設定

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
        file_menu.add_command(label="設定", command=self._show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        
        # 編集メニュー
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(
            label="シーンを追加",
            command=self.add_scene,
            accelerator=self.config_manager.get_shortcut_display('add_scene')
        )
        edit_menu.add_command(
            label="シーンを削除",
            command=self.delete_scene,
            accelerator=self.config_manager.get_shortcut_display('delete_scene')
        )
        menubar.add_cascade(label="編集", menu=edit_menu)

        # プラグインメニュー (ロードされたプラグインがあれば追加)
        if self.plugin_manager.plugins:
            plugin_menu = tk.Menu(menubar, tearoff=0)
            for name in self.plugin_manager.plugins:
                # プラグインのメニュー項目を追加する（ここではプラグイン名をそのまま表示）
                # より高度なプラグイン機能は、プラグイン側で定義させる
                plugin_menu.add_command(label=name, command=lambda n=name: messagebox.showinfo("プラグイン情報", f"'{n}' プラグインがロードされました。"))
            menubar.add_cascade(label="プラグイン", menu=plugin_menu)
        
    def _create_toolbar(self) -> None:
        """ツールバーを作成し、ウィンドウに配置します。"""
        # メインのツールバーフレームを作成
        self.toolbar_frame = ttk.Frame(self.root, padding=5)
        self.toolbar_frame.pack(fill=tk.X)

        # シーン追加ボタンをツールバーに配置
        add_scene_btn = ttk.Button(self.toolbar_frame, text="シーンを追加", command=self.add_scene)
        add_scene_btn.pack(side=tk.LEFT, padx=2)
        
        delete_scene_btn = ttk.Button(self.toolbar_frame, text="シーンを削除", command=self.delete_scene)
        delete_scene_btn.pack(side=tk.LEFT, padx=2)
        
        # ここにプラグインから追加されるボタンなどを配置できるように拡張可能

    def _create_main_layout(self) -> None:
        """メインのアプリケーションレイアウト（キャンバスとエディタ）を作成します。"""
        # 分割ウィンドウを使用して、キャンバス領域とエディタ領域を配置
        self.main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned_window.pack(fill=tk.BOTH, expand=True)
        
        # --- 左側: キャンバス (分岐図表示エリア) ---
        self.canvas_frame = ttk.Frame(self.main_paned_window, padding=5)
        
        # Canvasウィジェットの設定（スクロール可能にするため）
        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg="white",
            # スクロール領域は動的に調整されるため、初期値は仮
            scrollregion=(-2000, -2000, 2000, 2000)
        )
        
        # 水平・垂直スクロールバーの作成とCanvasへの接続
        self.h_scroll = ttk.Scrollbar(
            self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview
        )
        self.v_scroll = ttk.Scrollbar(
            self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        self.canvas.configure(
            xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set
        )
        
        # GridレイアウトでCanvasとScrollbarを配置
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.h_scroll.grid(row=1, column=0, sticky="ew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        
        # Gridセルにweightを設定して、Canvasが拡大・縮小されるようにする
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        
        # キャンバスイベントのバインド
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self._on_canvas_double_click)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click) # 右クリックメニュー用
        self.canvas.bind("<MouseWheel>", self._on_canvas_mousewheel) # ズーム用
        
        # メインウィンドウの PanedWindow にキャンバスフレームを追加
        self.main_paned_window.add(self.canvas_frame, weight=3) # 左側を広く取る
        
        # --- 右側: エディタ (シーン編集・分岐管理エリア) ---
        self.editor_frame = ttk.Frame(self.main_paned_window, padding=5)
        
        # エディタ内での分割ウィンドウ（シーン情報と分岐管理）
        self.editor_paned_window = ttk.PanedWindow(self.editor_frame, orient=tk.VERTICAL)
        self.editor_paned_window.pack(fill=tk.BOTH, expand=True)
        
        # シーン情報フレーム
        self.scene_info_frame = ttk.LabelFrame(self.editor_paned_window, text="シーン情報", padding=10)
        
        ttk.Label(self.scene_info_frame, text="シーン名:").grid(row=0, column=0, sticky="w")
        self.scene_name_entry = ttk.Entry(self.scene_info_frame)
        self.scene_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.scene_name_entry.bind("<FocusOut>", self._on_scene_name_changed)
        self.scene_name_entry.bind("<Return>", self._on_scene_name_changed) # Enterキーでも更新
        
        ttk.Label(self.scene_info_frame, text="内容:").grid(row=1, column=0, sticky="nw")
        # Textウィジェットにスクロールバーを付ける
        self.scene_content_text = tk.Text(self.scene_info_frame, height=15, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1)
        self.scene_content_text.grid(row=1, column=1, sticky="nsew", padx=5, pady=2)
        
        # Textウィジェット用のスクロールバー
        text_scroll = ttk.Scrollbar(self.scene_info_frame, orient=tk.VERTICAL, command=self.scene_content_text.yview)
        text_scroll.grid(row=1, column=2, sticky="ns")
        self.scene_content_text.config(yscrollcommand=text_scroll.set)
        self.scene_content_text.bind("<FocusOut>", self._on_scene_content_changed)
        
        # Gridセルにweightを設定
        self.scene_info_frame.grid_columnconfigure(1, weight=1)
        self.scene_info_frame.grid_rowconfigure(1, weight=1)
        
        self.editor_paned_window.add(self.scene_info_frame, weight=2) # シーン情報エリアをやや広く取る

        # 分岐管理フレーム
        self.branch_management_frame = ttk.LabelFrame(self.editor_paned_window, text="分岐管理", padding=10)
        
        # Treeview for branches
        columns = ("text", "target", "condition")
        self.branch_tree = ttk.Treeview(
            self.branch_management_frame, columns=columns, show="headings", height=6
        )
        self.branch_tree.heading("text", text="選択肢テキスト")
        self.branch_tree.heading("target", text="遷移先")
        self.branch_tree.heading("condition", text="条件")
        # 列幅の調整
        self.branch_tree.column("text", width=150)
        self.branch_tree.column("target", width=100)
        self.branch_tree.column("condition", width=150)
        
        self.branch_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        # Treeview用のスクロールバー
        tree_scroll = ttk.Scrollbar(self.branch_management_frame, orient=tk.VERTICAL, command=self.branch_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.branch_tree.config(yscrollcommand=tree_scroll.set)
        
        # 分岐操作ボタンフレーム
        branch_btn_frame = ttk.Frame(self.branch_management_frame)
        branch_btn_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

        self.add_branch_btn = ttk.Button(branch_btn_frame, text="分岐を追加", command=self.add_branch)
        self.add_branch_btn.pack(side=tk.LEFT, padx=2)
        
        self.edit_branch_btn = ttk.Button(branch_btn_frame, text="分岐を編集", command=self.edit_branch)
        self.edit_branch_btn.pack(side=tk.LEFT, padx=2)
        
        self.delete_branch_btn = ttk.Button(branch_btn_frame, text="分岐を削除", command=self.delete_branch)
        self.delete_branch_btn.pack(side=tk.LEFT, padx=2)
        
        self.editor_paned_window.add(self.branch_management_frame, weight=1) # 分岐管理エリアはやや小さく

        # エディタフレームをメインウィンドウの PanedWindow に追加
        self.main_paned_window.add(self.editor_frame, weight=1) # 右側は小さめ

        # --- エディタフレーム内のシーン操作ボタン ---
        # これらはエディタフレームの下部に配置されるため、別途フレームを作成して管理する
        self.scene_btn_frame = ttk.Frame(self.editor_frame)
        self.scene_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # エディタフレーム内の「シーンを追加」ボタン
        self.add_scene_btn = ttk.Button(self.scene_btn_frame, text="シーンを追加", command=self.add_scene)
        self.add_scene_btn.pack(side=tk.LEFT, padx=2)
        
        # エディタフレーム内の「シーンを削除」ボタン
        self.delete_scene_btn = ttk.Button(self.scene_btn_frame, text="シーンを削除", command=self.delete_scene)
        self.delete_scene_btn.pack(side=tk.LEFT, padx=2)


    def _bind_events(self) -> None:
        """アプリケーション全体のショートカットキーやグローバルイベントをバインドします。"""
        # ショートカットキーの設定
        self.setup_shortcuts()
        
        # ウィンドウを閉じる際の後処理（ここでは特に定義しませんが、必要なら追加）
        # self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def setup_shortcuts(self) -> None:
        """
        ConfigManager からショートカット設定を読み込み、それらをルートウィンドウにバインドします。
        既存のバインドがあればクリアしてから再設定します。
        """
        # 既存のバインドをすべて解除（再設定のため）
        # 注意: self.root.unbind_all("<Key>") のような全てを解除するのは避けるべき。
        # 特定のキーに対するバインドだけを解除するか、再バインド時に置き換えるのが良い。
        # ここでは、bind 関数が既存のバインドを上書きすることを期待して、シンプルに再バインドする。
        # より丁寧に行うなら、各ショートカットキーに対して個別のunbindを行う。

        # 新しいショートカットをバインド
        self._bind_shortcut('Control-n', self.new_project)
        self._bind_shortcut('Control-o', self.open_project)
        self._bind_shortcut('Control-s', self.save_project)
        self._bind_shortcut('Control-a', self.add_scene)
        self._bind_shortcut('Control-d', self.delete_scene)
        
        # メニューバーのアクセラレータ表示も更新（必要なら）
        # 例: self.root.nametowidget('.').children['!menu'].entryconfig(
        #     'ファイル', '新規プロジェクト', accelerator=self.config_manager.get_shortcut_display('new_project')
        # )

    def _bind_shortcut(self, shortcut_key_config: str, command: callable) -> None:
        """
        指定されたショートカットキー設定 (例: 'Control-n') とコマンドをルートウィンドウにバインドします。
        tkinterが認識できる形式 (例: '<Control-n>') に変換します。
        """
        # config.ini の値に基づいてtkinterのbind形式に変換
        # 例: 'Control-n' -> '<Control-n>'
        #     'Shift-F1' -> '<Shift-F1>'
        tkinter_shortcut_format = ""
        
        if not shortcut_key_config: # 設定がない場合はバインドしない
            return

        parts = shortcut_key_config.split('-')
        modifier = ""
        key = ""

        # 修飾子 (Control, Shift, Alt) を特定
        if parts[0].lower() == 'control':
            modifier = "<Control-"
            key = "-".join(parts[1:]).lower()
        elif parts[0].lower() == 'shift':
            modifier = "<Shift-"
            key = "-".join(parts[1:]).lower()
        elif parts[0].lower() == 'alt':
            modifier = "<Alt-"
            key = "-".join(parts[1:]).lower()
        else:
            # 修飾子がない場合は、キー名がそのまま modifier+key になる
            modifier = "<"
            key = shortcut_key_config.lower()

        # 最終的なtkinterのbind形式文字列を構築
        if key: # キー名が存在する場合
            tkinter_shortcut_format = f"{modifier}{key}>"
        else: # キー名が見つからなかった場合 (e.g., "Control-" のような不正な入力)
            print(f"警告: 不正なショートカットキーフォーマット '{shortcut_key_config}' です。スキップします。")
            return

        if tkinter_shortcut_format: # 有効なフォーマットが作成された場合
            try:
                # 同じイベントへのバインドは上書きされることを期待
                self.root.bind(tkinter_shortcut_format, lambda event, cmd=command: cmd())
                # print(f"ショートカットキー '{shortcut_key_config}' を '{tkinter_shortcut_format}' としてバインドしました。")
            except tk.TclError as e:
                print(f"ショートカットキー '{shortcut_key_config}' ({tkinter_shortcut_format}) のバインドに失敗しました: {e}")

    def _load_plugins(self) -> None:
        """プラグインマネージャーを使用して、利用可能なプラグインをロードします。"""
        plugin_names = self.plugin_manager.discover_plugins()
        if not plugin_names:
            # print("プラグインディレクトリにプラグインが見つかりませんでした。") # 毎回表示されると冗長なのでコメントアウト
            return

        print(f"発見されたプラグイン: {plugin_names}")
        for name in plugin_names:
            if self.plugin_manager.load_plugin(name):
                print(f"プラグイン '{name}' のロードに成功しました。")
            else:
                print(f"プラグイン '{name}' のロードに失敗しました。")

    def _update_editor_ui_state(self) -> None:
        """
        選択中のシーンに基づいて、エディタ領域（シーン名、内容、分岐リスト）の
        有効/無効状態や表示内容を更新します。
        """
        is_scene_selected = self.selected_scene is not None
        
        # シーン名と内容の入力欄の状態を設定
        if is_scene_selected:
            self.scene_name_entry.config(state=tk.NORMAL)
            self.scene_content_text.config(state=tk.NORMAL)
            
            # 現在選択中のシーンの内容を表示
            self.scene_name_entry.delete(0, tk.END)
            self.scene_name_entry.insert(0, self.selected_scene.name)
            
            self.scene_content_text.delete("1.0", tk.END)
            self.scene_content_text.insert("1.0", self.selected_scene.content)
            
            # 分岐操作ボタンの状態を設定
            self.add_branch_btn.config(state=tk.NORMAL)
            # 分岐リストが空でない、または編集対象が選択されている場合のみ編集/削除ボタンを有効化
            self.edit_branch_btn.config(state=tk.NORMAL if self.branch_tree.selection() else tk.DISABLED)
            self.delete_branch_btn.config(state=tk.NORMAL if self.branch_tree.selection() else tk.DISABLED)
            
            # シーン操作ボタンの状態を設定
            self.delete_scene_btn.config(state=tk.NORMAL) # シーン削除ボタンを有効化

        else: # シーンが選択されていない場合
            self.scene_name_entry.config(state=tk.DISABLED)
            self.scene_content_text.config(state=tk.DISABLED)
            
            # 入力欄をクリア
            self.scene_name_entry.delete(0, tk.END)
            self.scene_content_text.delete("1.0", tk.END)
            
            # 分岐操作ボタンの状態を設定
            self.add_branch_btn.config(state=tk.DISABLED)
            self.edit_branch_btn.config(state=tk.DISABLED)
            self.delete_branch_btn.config(state=tk.DISABLED)
            
            # シーン操作ボタンの状態を設定
            self.delete_scene_btn.config(state=tk.DISABLED) # シーン削除ボタンを無効化

        # 分岐リストを更新
        self._update_branch_list()
        
        # 分岐ノードの描画更新（選択状態が変わったため）
        self._redraw_canvas()

    def _update_branch_list(self) -> None:
        """
        選択中のシーンの分岐情報をTreeviewに表示・更新します。
        """
        # Treeviewの子要素をすべて削除
        for item in self.branch_tree.get_children():
            self.branch_tree.delete(item)
            
        if self.selected_scene:
            for i, branch in enumerate(self.selected_scene.branches):
                # 遷移先シーンの名前を取得
                target_scene = next(
                    (s for s in self.scenes if s.id == branch["target"]), None
                )
                target_name = target_scene.name if target_scene else "不明なシーン"
                
                # Treeviewに項目を追加 (iidとしてインデックスを文字列で設定)
                self.branch_tree.insert(
                    "", tk.END, iid=str(i),
                    values=(branch["text"], target_name, branch["condition"])
                )
            
            # 分岐がある場合は編集・削除ボタンを有効にする
            if self.selected_scene.branches:
                self.edit_branch_btn.config(state=tk.NORMAL)
                self.delete_branch_btn.config(state=tk.NORMAL)
            else:
                self.edit_branch_btn.config(state=tk.DISABLED)
                self.delete_branch_btn.config(state=tk.DISABLED)
        else:
            # シーンが選択されていない場合は無効にする
            self.edit_branch_btn.config(state=tk.DISABLED)
            self.delete_branch_btn.config(state=tk.DISABLED)

    def _save_current_scene_data(self) -> None:
        """
        現在エディタで編集中のシーン名と内容を、選択中のSceneオブジェクトに保存します。
        """
        if self.selected_scene:
            # シーン名の更新
            new_name = self.scene_name_entry.get().strip()
            if new_name and new_name != self.selected_scene.name:
                self.selected_scene.name = new_name
                self._redraw_canvas() # シーン名が変更されたらキャンバスを再描画
            
            # シーン内容の更新
            new_content = self.scene_content_text.get("1.0", tk.END).strip()
            if new_content != self.selected_scene.content:
                self.selected_scene.content = new_content
                # 内容の変更だけではキャンバスの再描画は不要だが、保存操作などで必要になる場合がある

    def _redraw_canvas(self) -> None:
        """キャンバス上の全てのシーンノードと分岐線を再描画します。"""
        self.canvas.delete("all") # 全て削除してから再描画
        
        # シーンノードの描画
        scene_node_map: Dict[str, str] = {} # Scene ID -> Canvas Item ID マッピング
        for scene in self.scenes:
            node_id = f"scene_{scene.id}" # キャンバスアイテムのタグとして使用
            scene_node_map[scene.id] = node_id
            
            # ノードの背景色（選択中か否かで変える）
            fill_color = "lightblue" if scene == self.selected_scene else "white"
            outline_color = "blue" if scene == self.selected_scene else "black"
            
            # シーンノード（円）を描画
            self.canvas.create_oval(
                scene.x - self.NODE_RADIUS, scene.y - self.NODE_RADIUS,
                scene.x + self.NODE_RADIUS, scene.y + self.NODE_RADIUS,
                fill=fill_color, outline=outline_color, tags=(node_id, "scene_node")
            )
            
            # シーン名テキストを描画
            self.canvas.create_text(
                scene.x, scene.y,
                text=scene.name, tags=(node_id, "scene_text")
            )
        
        # 分岐線の描画
        for scene in self.scenes:
            for branch in scene.branches:
                target_scene_id = branch["target"]
                if target_scene_id in scene_node_map:
                    start_pos = (scene.x, scene.y)
                    end_scene = next((s for s in self.scenes if s.id == target_scene_id), None)
                    if end_scene:
                        end_pos = (end_scene.x, end_scene.y)
                        
                        # 線を描画（開始点と終了点の少し外側から描画）
                        line_color = "gray"
                        arrow_type = tk.LAST if start_pos != end_pos else None # 同じノードへの矢印は描画しない
                        
                        # 円の端点の座標を計算
                        start_x, start_y = start_pos
                        end_x, end_y = end_pos

                        # 開始点と終了点の間のベクトル
                        dx, dy = end_x - start_x, end_y - start_y
                        dist = (dx**2 + dy**2)**0.5 # 距離

                        # ゼロ割りを避ける
                        if dist == 0:
                            continue # 同じノードへの分岐線は描画しない
                            
                        # 円の半径分のオフセットを加えて、ノードの境界線から線を開始・終了させる
                        offset_start_x = start_x + dx * (self.NODE_RADIUS / dist)
                        offset_start_y = start_y + dy * (self.NODE_RADIUS / dist)
                        offset_end_x = end_x - dx * (self.NODE_RADIUS / dist)
                        offset_end_y = end_y - dy * (self.NODE_RADIUS / dist)

                        line_id = self.canvas.create_line(
                            offset_start_x, offset_start_y,
                            offset_end_x, offset_end_y,
                            fill=line_color, arrow=arrow_type, tags=("branch_line", scene.id)
                        )
                        
                        # 分岐テキスト（線の真ん中あたりに配置）
                        mid_x = (offset_start_x + offset_end_x) / 2
                        mid_y = (offset_start_y + offset_end_y) / 2
                        
                        branch_text_id = self.canvas.create_text(
                            mid_x, mid_y - 10, # 少し上にずらす
                            text=branch["text"],
                            fill=line_color,
                            tags=("branch_text", scene.id)
                        )
                        
                        # 条件テキスト（分岐テキストの下に配置）
                        if branch["condition"]:
                            self.canvas.create_text(
                                mid_x, mid_y + 5, # 少し下にずらす
                                text=f"[条件: {branch['condition']}]",
                                font=("Arial", 8),
                                fill="darkgray",
                                tags=("condition_text", scene.id)
                            )

    # --- イベントハンドラ ---
    
    def _on_canvas_press(self, event: tk.Event) -> None:
        """
        キャンバス上でマウスボタンが押されたときの処理。
        ドラッグ開始の準備を行います。
        """
        # クリックされたアイテムを特定
        # find_closest は指定した座標に最も近いアイテムIDを返す
        # haloパラメータで、その近傍も検索対象に含めることができる
        clicked_items = self.canvas.find_closest(event.x, event.y, halo=5)
        
        item_type = None # 'scene' or 'background'
        scene_id = None

        if clicked_items:
            # 見つかったアイテムのうち、シーンノードに関連するものかチェック
            for item in clicked_items:
                tags = self.canvas.gettags(item)
                if "scene_node" in tags or "scene_text" in tags:
                    item_type = "scene"
                    # タグからシーンIDを取得（例: "scene_xxxxxxxx-xxxx-...")
                    for tag in tags:
                        if tag.startswith("scene_"):
                            scene_id = tag.split("_")[1]
                            break
                    break # シーンノードが見つかったらループ終了

        # シーンが選択されていない場合、ドラッグ操作のために現在のシーンをセットアップ
        if item_type == "scene" and scene_id:
            new_selected_scene = next((s for s in self.scenes if s.id == scene_id), None)
            if new_selected_scene:
                # 選択変更前に現在の編集内容を保存
                self._save_current_scene_data()
                
                self.selected_scene = new_selected_scene
                self._update_editor_ui_state() # UIを更新（選択状態の変更を反映）
                
                # ドラッグ操作の準備
                self.drag_state["is_dragging"] = True
                self.drag_state["item_type"] = "scene"
                self.drag_state["item_id"] = scene_id
                # イベント発生時のキャンバス上の座標を保存
                self.drag_state["start_x"] = self.canvas.canvasx(event.x)
                self.drag_state["start_y"] = self.canvas.canvasy(event.y)

        else: # 背景クリックの場合
            # 現在選択中のシーンの編集内容を保存 (フォーカスが外れるため)
            self._save_current_scene_data()
            
            self.selected_scene = None # シーン選択を解除
            self._update_editor_ui_state() # UIを更新
            
            # ドラッグ操作の準備 (パン操作)
            self.drag_state["is_dragging"] = True
            self.drag_state["item_type"] = "background"
            self.drag_state["item_id"] = None
            self.drag_state["start_x"] = self.canvas.canvasx(event.x)
            self.drag_state["start_y"] = self.canvas.canvasy(event.y)

    def _on_canvas_drag(self, event: tk.Event) -> None:
        """
        キャンバス上でマウスがドラッグされているときの処理。
        シーンノードの移動またはキャンバスのパンを行います。
        """
        if not self.drag_state["is_dragging"]:
            return # ドラッグ中でなければ何もしない
            
        # 現在のキャンバス上の座標を取得
        current_canvas_x = self.canvas.canvasx(event.x)
        current_canvas_y = self.canvas.canvasy(event.y)

        # ドラッグ開始時の座標との差分を計算
        dx = current_canvas_x - self.drag_state["start_x"]
        dy = current_canvas_y - self.drag_state["start_y"]

        if self.drag_state["item_type"] == "scene" and self.drag_state["item_id"]:
            # シーンノードの移動
            scene_id = self.drag_state["item_id"]
            scene = next((s for s in self.scenes if s.id == scene_id), None)
            if scene:
                scene.x += dx
                scene.y += dy
                
                # シーンの位置情報を更新したので、キャンバスを再描画
                self._redraw_canvas()
                
                # ドラッグ状態の開始座標を更新 (次のドラッグ移動のために)
                self.drag_state["start_x"] = current_canvas_x
                self.drag_state["start_y"] = current_canvas_y

        elif self.drag_state["item_type"] == "background":
            # キャンバスのパン操作
            # スクロールバーの移動量を調整する
            self.canvas.xview_scroll(-int(dx), "units") # dxの単位はpixelなので、unitsで指定
            self.canvas.yview_scroll(-int(dy), "units")
            
            # ドラッグ状態の開始座標を更新
            self.drag_state["start_x"] = current_canvas_x
            self.drag_state["start_y"] = current_canvas_y

    def _on_canvas_release(self, event: tk.Event) -> None:
        """
        キャンバス上でマウスボタンが離されたときの処理。
        ドラッグ操作を終了します。
        """
        self.drag_state["is_dragging"] = False
        self.drag_state["item_type"] = None
        self.drag_state["item_id"] = None
        # ドラッグ終了後、エディタUIの状態を最新にする（特にパン操作時など）
        self._update_editor_ui_state()

    def _on_canvas_double_click(self, event: tk.Event) -> None:
        """
        キャンバス上でダブルクリックされたときの処理。
        ダブルクリックされたシーンノードをエディタで開きます。
        """
        # クリックされたアイテムを特定
        clicked_items = self.canvas.find_closest(event.x, event.y, halo=5)
        
        scene_id = None
        if clicked_items:
            for item in clicked_items:
                tags = self.canvas.gettags(item)
                if "scene_node" in tags or "scene_text" in tags:
                    for tag in tags:
                        if tag.startswith("scene_"):
                            scene_id = tag.split("_")[1]
                            break
                    break # シーンノードが見つかったらループ終了

        if scene_id:
            # ダブルクリックされたシーンを取得
            target_scene = next((s for s in self.scenes if s.id == scene_id), None)
            if target_scene:
                # 選択中のシーンを変更し、エディタの状態を更新
                self._save_current_scene_data() # 変更内容を保存
                self.selected_scene = target_scene
                self._update_editor_ui_state() # UIを更新（選択状態の変更を反映）

    def _on_canvas_right_click(self, event: tk.Event) -> None:
        """
        キャンバス上で右クリックされたときにコンテキストメニューを表示します。
        """
        # 右クリックメニューを作成
        context_menu = tk.Menu(self.root, tearoff=0)
        
        # メニュー項目を追加
        context_menu.add_command(
            label="シーンを追加",
            command=lambda: self.add_scene_at_event(event), # クリック位置にシーンを追加
            accelerator=self.config_manager.get_shortcut_display('add_scene')
        )
        context_menu.add_separator()
        context_menu.add_command(label="設定", command=self._show_settings)
        
        # メニューを表示
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release() # メニューが閉じられたときにフォーカスを解放

    def _on_canvas_mousewheel(self, event: tk.Event) -> None:
        """
        キャンバス上でマウスホイールが回転したときの処理。
        キャンバスのズームを行います。
        """
        # WindowsとLinux/macOSでdeltaの取得方法が異なる
        if event.num == 5 or event.delta == -120: # ホイールダウン
            zoom_factor = 0.9
        elif event.num == 4 or event.delta == 120: # ホイールアップ
            zoom_factor = 1.1
        else:
            return # 未知のイベントは無視
            
        # マウスカーソル位置を中心としてズーム
        # canvas.scale(tagOrId, x, y, scaleFactorX, scaleFactorY=None)
        self.canvas.scale("all", event.x, event.y, zoom_factor, zoom_factor)
        # スクロール領域も再計算する必要があるが、ここでは Canvas が自動で調整する
        
    def _on_scene_name_changed(self, event: Optional[tk.Event] = None) -> None:
        """
        シーン名の入力内容が変更されたとき（フォーカスアウトまたはEnterキー）の処理。
        選択中のシーンオブジェクトを更新します。
        """
        self._save_current_scene_data()

    def _on_scene_content_changed(self, event: Optional[tk.Event] = None) -> None:
        """
        シーン内容のテキスト入力内容が変更されたとき（フォーカスアウト）の処理。
        選択中のシーンオブジェクトを更新します。
        """
        self._save_current_scene_data()

    # --- プロジェクト操作 ---

    def new_project(self) -> None:
        """新しいプロジェクトを開始します。既存のプロジェクトをクリアします。"""
        if self.scenes:
            if not messagebox.askokcancel("確認", "現在のプロジェクトは保存されていません。続行しますか？"):
                return
        
        self.current_project_path = None
        self.scenes = []
        self.selected_scene = None
        self._update_editor_ui_state()
        self._redraw_canvas()
        self.root.title("ノベルゲーム制作支援ツール - 無題") # タイトルをリセット
        print("新しいプロジェクトを開始しました。")

    def open_project(self) -> None:
        """プロジェクトファイルを開きます。"""
        file_path_str = filedialog.askopenfilename(
            title="プロジェクトを開く",
            filetypes=[("ノベルゲームプロジェクト", "*.ngp"), ("すべてのファイル", "*.*")],
            defaultextension=".ngp"
        )
        
        if not file_path_str:
            return # キャンセルされた場合は何もしない

        file_path = Path(file_path_str)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # 既存のプロジェクトデータをクリア
                self.scenes = []
                self.selected_scene = None
                
                # ファイルからシーンデータをロード
                loaded_scenes = data.get("scenes", [])
                for scene_data in loaded_scenes:
                    scene = Scene.from_dict(scene_data)
                    self.scenes.append(scene)
                
                self.current_project_path = file_path
                self._update_editor_ui_state()
                self._redraw_canvas()
                self.root.title(f"ノベルゲーム制作支援ツール - {file_path.name}") # タイトルを更新
                print(f"プロジェクト '{file_path.name}' を開きました。")

        except FileNotFoundError:
            messagebox.showerror("エラー", f"ファイルが見つかりません: {file_path_str}")
        except json.JSONDecodeError:
            messagebox.showerror("エラー", f"JSONファイルの解析に失敗しました: {file_path_str}")
        except Exception as e:
            messagebox.showerror("エラー", f"プロジェクトの読み込み中に予期せぬエラーが発生しました:\n{e}")

    def save_project(self) -> None:
        """
        現在のプロジェクトを保存します。
        プロジェクトがまだ保存されていない場合は、save_project_asを呼び出します。
        """
        self._save_current_scene_data() # 保存前に編集内容を反映
        
        if self.current_project_path:
            self._save_to_file(self.current_project_path)
        else:
            self.save_project_as() # 未保存なら名前を付けて保存へ

    def save_project_as(self) -> None:
        """
        現在のプロジェクトを新しい名前で保存します。
        """
        self._save_current_scene_data() # 保存前に編集内容を反映
        
        file_path_str = filedialog.asksaveasfilename(
            title="プロジェクトを名前を付けて保存",
            defaultextension=".ngp",
            filetypes=[("ノベルゲームプロジェクト", "*.ngp"), ("すべてのファイル", "*.*")]
        )
        
        if not file_path_str:
            return # キャンセルされた場合は何もしない
            
        self.current_project_path = Path(file_path_str)
        self._save_to_file(self.current_project_path)
        self.root.title(f"ノベルゲーム制作支援ツール - {self.current_project_path.name}") # タイトルを更新
        print(f"プロジェクトを '{self.current_project_path.name}' として保存しました。")

    def _save_to_file(self, file_path: Path) -> None:
        """
        プロジェクトデータを指定されたファイルパスにJSON形式で保存します。
        """
        data = {
            "scenes": [scene.to_dict() for scene in self.scenes]
        }
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2) # ensure_ascii=Falseで日本語をそのまま出力
        except IOError as e:
            messagebox.showerror("エラー", f"ファイルへの書き込みに失敗しました: {e}")
        except Exception as e:
            messagebox.showerror("エラー", f"プロジェクトの保存中に予期せぬエラーが発生しました:\n{e}")

    # --- シーン操作 ---
    
    def add_scene(self, x: float = 100.0, y: float = 100.0) -> None:
        """
        新しいシーンをキャンバス上の指定された位置に追加します。
        デフォルト位置は (100, 100) です。
        """
        new_scene = Scene("新しいシーン", "", x, y)
        self.scenes.append(new_scene)
        self.selected_scene = new_scene # 追加したシーンを選択状態にする
        self._update_editor_ui_state()
        self._redraw_canvas()
        print(f"シーン '{new_scene.name}' (ID: {new_scene.id[:6]}...) を追加しました。")

    def add_scene_at_event(self, event: tk.Event) -> None:
        """
        マウスイベントが発生したキャンバス上の座標に新しいシーンを追加します。
        右クリックメニューからの呼び出しで使用されます。
        """
        # イベントの座標は画面座標なので、キャンバスの表示座標に変換する
        scene_x = self.canvas.canvasx(event.x)
        scene_y = self.canvas.canvasy(event.y)
        self.add_scene(scene_x, scene_y)

    def delete_scene(self) -> None:
        """
        現在選択中のシーンを削除します。
        他のシーンから参照されている場合は、その分岐も削除します。
        """
        if not self.selected_scene:
            return
            
        # 削除確認のダイアログ
        if not messagebox.askyesno("確認", f"シーン「{self.selected_scene.name}」を削除しますか？\nこのシーンへの全ての分岐も削除されます。"):
            return
            
        # 削除対象シーンのIDを保持
        scene_id_to_delete = self.selected_scene.id
        
        # 他のシーンから、削除対象シーンへの分岐を削除
        for scene in self.scenes:
            # 現在選択中のシーンのIDと一致しない分岐のみを残す
            scene.branches = [
                b for b in scene.branches if b["target"] != scene_id_to_delete
            ]
        
        # シーンリストから削除対象シーンを削除
        self.scenes.remove(self.selected_scene)
        
        # 選択状態を解除し、UIを更新
        self.selected_scene = None
        self._update_editor_ui_state()
        self._redraw_canvas()
        print(f"シーン ID: {scene_id_to_delete[:6]}... を削除しました。")

    # --- 分岐操作 ---

    def add_branch(self) -> None:
        """
        現在選択中のシーンに新しい分岐を追加するためのダイアログを開きます。
        """
        if not self.selected_scene:
            return
            
        # 遷移先シーンの候補リストを作成（現在のシーン自身は除く）
        available_scenes_for_target = [
            s for s in self.scenes if s.id != self.selected_scene.id
        ]
        
        dialog = BranchDialog(
            self.root, "分岐を追加",
            available_scenes_for_target, # 遷移先候補として渡す
            self.selected_scene # ダイアログ内で現在のシーンを識別するため
        )
        
        if dialog.result: # OKボタンが押され、有効な結果が返された場合
            self.selected_scene.add_branch(
                dialog.result["text"],
                dialog.result["target_scene_id"],
                dialog.result["condition"]
            )
            self._update_editor_ui_state() # UIを更新して新しい分岐を表示
            print(f"シーン '{self.selected_scene.name}' に分岐を追加しました。")

    def edit_branch(self) -> None:
        """
        現在選択中のシーンの、選択されている分岐項目を編集するためのダイアログを開きます。
        """
        # Treeviewで選択されている項目があるか確認
        selected_item_ids = self.branch_tree.selection()
        if not self.selected_scene or not selected_item_ids:
            return # シーンが選択されていないか、分岐が選択されていない場合は何もしない
            
        # 選択されているのは1つだけと仮定 (Multiple selection is not enabled for BranchDialog)
        branch_index_str = selected_item_ids[0] # Treeviewのitem IDは文字列なのでインデックスとして使用
        
        try:
            branch_index = int(branch_index_str) # Treeviewのiidがインデックス文字列の場合
            branch = self.selected_scene.branches[branch_index]
        except (ValueError, IndexError):
            messagebox.showerror("エラー", "選択された分岐情報が不正です。")
            return
            
        # 遷移先シーンの候補リストを作成（現在のシーン自身は除く）
        available_scenes_for_target = [
            s for s in self.scenes if s.id != self.selected_scene.id
        ]
        
        dialog = BranchDialog(
            self.root, "分岐を編集",
            available_scenes_for_target,
            self.selected_scene,
            initial_text=branch["text"],
            initial_target_scene_id=branch["target"], # 事前にIDを渡す
            initial_condition=branch["condition"]
        )
        
        if dialog.result: # OKボタンが押され、有効な結果が返された場合
            # 選択されていた分岐情報を更新
            self.selected_scene.branches[branch_index] = {
                "text": dialog.result["text"],
                "target": dialog.result["target_scene_id"],
                "condition": dialog.result["condition"]
            }
            self._update_editor_ui_state() # UIを更新
            print(f"シーン '{self.selected_scene.name}' の分岐を編集しました。")

    def delete_branch(self) -> None:
        """
        現在選択中のシーンの、選択されている分岐項目を削除します。
        """
        selected_item_ids = self.branch_tree.selection()
        if not self.selected_scene or not selected_item_ids:
            return
            
        branch_index_str = selected_item_ids[0]
        
        if not messagebox.askyesno("確認", "選択した分岐を削除しますか？"):
            return

        try:
            branch_index = int(branch_index_str)
            # 選択されていた分岐を削除
            del self.selected_scene.branches[branch_index]
            self._update_editor_ui_state() # UIを更新
            print(f"シーン '{self.selected_scene.name}' から分岐を削除しました。")
        except (ValueError, IndexError):
            messagebox.showerror("エラー", "選択された分岐情報を削除できませんでした。")

    # --- UI表示・管理 ---

    def _show_settings(self) -> None:
        """設定ダイアログを表示します。"""
        SettingsDialog(self.root, self.config_manager)

# --- 分岐設定ダイアログクラス ---

class BranchDialog(tk.Toplevel):
    """
    シーンに分岐を追加または編集するためのモーダルダイアログ。
    選択肢テキスト、遷移先シーン、条件を設定できます。
    """
    def __init__(self,
                 parent: tk.Tk,
                 title: str,
                 available_scenes: List[Scene], # 遷移先候補となるシーンのリスト
                 source_scene: Scene, # 分岐元のシーンオブジェクト
                 initial_text: str = "",
                 initial_target_scene_id: str = "",
                 initial_condition: str = ""):
        """
        BranchDialog を初期化します。

        Args:
            parent (tk.Tk): 親ウィジェット。
            title (str): ダイアログのタイトル。
            available_scenes (List[Scene]): 遷移先として選択可能なシーンのリスト。
                                           現在のシーン自身は含まれません。
            source_scene (Scene): 分岐を作成・編集しているシーン。
            initial_text (str, optional): 初期表示される選択肢テキスト。
            initial_target_scene_id (str, optional): 初期表示される遷移先シーンのID。
            initial_condition (str, optional): 初期表示される条件テキスト。
        """
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()

        self.result: Optional[Dict[str, str]] = None # OKが押されたときの戻り値
        self.available_scenes = available_scenes
        self.source_scene = source_scene
        
        self._create_widgets(initial_text, initial_target_scene_id, initial_condition)
        self.resizable(False, False)
        self.wait_window(self) # ウィンドウが閉じるまで待機

    def _create_widgets(self,
                        initial_text: str,
                        initial_target_scene_id: str,
                        initial_condition: str) -> None:
        """ダイアログのウィジェットを作成し配置します。"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 選択肢テキスト入力
        ttk.Label(main_frame, text="選択肢テキスト:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.text_entry = ttk.Entry(main_frame, width=40)
        self.text_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.text_entry.insert(0, initial_text)
        self.text_entry.focus_set() # 初めにフォーカスを当てる

        # 遷移先シーン選択 (Combobox)
        ttk.Label(main_frame, text="遷移先シーン:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.target_scene_var = tk.StringVar()
        # 利用可能なシーン名リストを作成
        scene_names = [s.name for s in self.available_scenes]
        self.target_combo = ttk.Combobox(
            main_frame,
            textvariable=self.target_scene_var,
            values=scene_names, # シーン名リストを設定
            state="readonly" # ユーザーが直接入力できないようにする
        )
        self.target_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        
        # 初期遷移先を設定
        if initial_target_scene_id:
            target_scene = next((s for s in self.available_scenes if s.id == initial_target_scene_id), None)
            if target_scene:
                self.target_scene_var.set(target_scene.name)

        # 条件入力
        ttk.Label(main_frame, text="条件 (任意):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.condition_entry = ttk.Entry(main_frame, width=40)
        self.condition_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        self.condition_entry.insert(0, initial_condition)

        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)

        ttk.Button(button_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self._on_cancel).pack(side=tk.LEFT, padx=5)
        
        main_frame.grid_columnconfigure(1, weight=1)

    def _on_ok(self) -> None:
        """OKボタンが押されたときの処理。入力内容を検証し、結果を設定します。"""
        text = self.text_entry.get().strip()
        target_scene_name = self.target_scene_var.get().strip()
        condition = self.condition_entry.get().strip()
        
        # 入力値の検証
        if not text:
            messagebox.showerror("エラー", "選択肢テキストを入力してください。", parent=self)
            return
            
        if not target_scene_name:
            messagebox.showerror("エラー", "遷移先シーンを選択してください。", parent=self)
            return
            
        # 遷移先シーン名からIDを取得
        target_scene = next((s for s in self.available_scenes if s.name == target_scene_name), None)
        if not target_scene: # 念のため、有効なシーンIDか確認
            messagebox.showerror("エラー", "無効な遷移先シーンが選択されています。", parent=self)
            return
            
        # 結果を設定してダイアログを閉じる
        self.result = {
            "text": text,
            "target_scene_id": target_scene.id, # IDを保存
            "condition": condition
        }
        self.destroy()

    def _on_cancel(self) -> None:
        """キャンセルボタンが押されたときの処理。ダイアログを閉じます。"""
        self.destroy()

# --- メイン実行ブロック ---
if __name__ == "__main__":
    root = tk.Tk()
    # アプリケーションインスタンスを作成
    app = NovelGameEditor(root)
    # Tkinterイベントループを開始
    root.mainloop()
