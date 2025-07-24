import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox
from pathlib import Path
import uuid
from typing import TYPE_CHECKING, Optional, Dict, Any

# 型チェック時のみインポートを有効にする（循環参照を避けるため）
if TYPE_CHECKING:
    from __main__ import IPlugin, NovelGameEditor, Tooltip

# IPluginを動的に取得（アプリケーションのメインモジュールから）
# これにより、__main__を直接インポートせずに済む
try:
    from __main__ import IPlugin, Tooltip
except ImportError:
    # 実行ファイル化などで__main__が見つからない場合のフォールバック
    class IPlugin:
        def __init__(self, app): self.app = app
    class Tooltip:
        def __init__(self, w, t): pass


class Character:
    """キャラクターのデータを保持するクラス"""
    def __init__(self, name: str = "新規キャラクター", description: str = "", color: str = "#FFFFFF", image_path: str = ""):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.description: str = description
        self.color: str = color
        self.image_path: str = image_path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "image_path": self.image_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        char = cls()
        char.id = data.get("id", str(uuid.uuid4()))
        char.name = data.get("name", "名称未設定")
        char.description = data.get("description", "")
        char.color = data.get("color", "#FFFFFF")
        char.image_path = data.get("image_path", "")
        return char

class CharacterManagerPlugin(IPlugin):
    """キャラクター管理機能を提供するプラグイン"""
    
    def setup(self) -> None:
        """プラグインの初期設定"""
        print("[プラグイン: CharacterManager] セットアップを開始します。")
        self.characters: Dict[str, Character] = {}
        self.selected_character_id: Optional[str] = None
        
        # プロジェクトデータに 'characters' キーを登録
        self.app.register_data_key("characters", [])

    def register(self) -> None:
        """UIの登録やイベントのバインド"""
        print("[プラグイン: CharacterManager] UIを登録します。")
        self._patch_project_methods()
        self._create_ui()
        # UI作成後に、最初のキャラクター読み込みを実行する
        self._load_characters_from_project()

    def teardown(self) -> None:
        """プラグインのクリーンアップ処理"""
        print("[プラグイン: CharacterManager] 終了処理を実行します。")
        # タブを削除
        try:
            if self.notebook:
                self.notebook.forget(self.main_frame)
        except tk.TclError:
            pass # ウィンドウが既に閉じられている場合など

    def _patch_project_methods(self):
        """既存のプロジェクト操作メソッドを拡張（パッチ）する"""
        # 元のメソッドを保持
        original_new_project = self.app.new_project
        original_open_project = self.app.open_project
        original_save_to_file = self.app._save_to_file

        def new_project_with_chars(*args, **kwargs):
            original_new_project(*args, **kwargs)
            # UIが作成された後で、新しい空のプロジェクトからキャラクター情報をロード（実質的にクリア）する
            if hasattr(self, 'char_tree'):
                self._load_characters_from_project()
                print("[プラグイン: CharacterManager] 新規プロジェクトでキャラクターリストを初期化しました。")

        def open_project_with_chars(*args, **kwargs):
            original_open_project(*args, **kwargs)
            if hasattr(self, 'char_tree'):
                self._load_characters_from_project()
                print("[プラグイン: CharacterManager] プロジェクトからキャラクターを読み込みました。")
            
        def save_to_file_with_chars(path: Path) -> bool:
            # UIが作成されていれば、現在編集中のキャラクターデータを保存
            if hasattr(self, 'name_entry'):
                self._save_current_character_data()
            
            # プロジェクトデータにキャラクター情報を反映
            self.app.project_data['characters'] = [char.to_dict() for char in self.characters.values()]
            
            return original_save_to_file(path)

        # メソッドを差し替え
        self.app.new_project = new_project_with_chars
        self.app.open_project = open_project_with_chars
        self.app._save_to_file = save_to_file_with_chars


    def _create_ui(self):
        """キャラクター管理用のUIを構築する"""
        # メインアプリ側で self.editor_notebook が作られていることを期待する
        if not hasattr(self.app, 'editor_notebook'):
            print("[エラー] キャラクター管理プラグインは、メインアプリの editor_notebook を見つけられませんでした。")
            return
        
        # self.editor_notebook に直接アクセスする
        self.notebook = self.app.editor_notebook

        # キャラクター管理用のメインフレームを作成
        self.main_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.main_frame, text="キャラクター管理")

        # --- レイアウト設定 ---
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(0, weight=1)

        # --- ツールバー ---
        toolbar = ttk.Frame(self.main_frame)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        self.add_btn = ttk.Button(toolbar, text="追加", command=self._add_character, width=8)
        self.add_btn.pack(side=tk.LEFT, padx=2)
        Tooltip(self.add_btn, "新しいキャラクターを追加します。")

        self.delete_btn = ttk.Button(toolbar, text="削除", command=self._delete_character, width=8, state=tk.DISABLED)
        self.delete_btn.pack(side=tk.LEFT, padx=2)
        Tooltip(self.delete_btn, "選択中のキャラクターを削除します。")

        # --- メインコンテンツ（左右分割） ---
        content_pane = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        content_pane.grid(row=1, column=0, sticky="nsew")

        # 左側: キャラクターリスト
        list_frame = ttk.Frame(content_pane)
        content_pane.add(list_frame, weight=1)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        
        self.char_tree = ttk.Treeview(list_frame, columns=("name",), show="headings", selectmode="browse")
        self.char_tree.heading("name", text="キャラクター名")
        self.char_tree.column("name", anchor="w")
        self.char_tree.grid(row=0, column=0, sticky="nsew")
        self.char_tree.bind('<<TreeviewSelect>>', self._on_character_select)

        # 右側: キャラクター詳細編集
        details_frame = ttk.LabelFrame(content_pane, text="キャラクター詳細")
        content_pane.add(details_frame, weight=2)
        details_frame.columnconfigure(1, weight=1)
        
        # 名前
        ttk.Label(details_frame, text="名前:").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.name_entry = ttk.Entry(details_frame)
        self.name_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        self.name_entry.bind("<FocusOut>", self._on_data_changed)
        self.name_entry.bind("<Return>", self._on_data_changed)

        # 説明
        ttk.Label(details_frame, text="説明:").grid(row=1, column=0, sticky="nw", padx=5, pady=3)
        self.desc_text = tk.Text(details_frame, height=5, wrap=tk.WORD)
        self.desc_text.grid(row=1, column=1, columnspan=2, sticky="nsew", padx=5, pady=3)
        self.desc_text.bind("<FocusOut>", self._on_data_changed)
        
        # テーマカラー
        ttk.Label(details_frame, text="カラー:").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        self.color_swatch = tk.Label(details_frame, text="      ", bg="#FFFFFF", relief="sunken")
        self.color_swatch.grid(row=2, column=1, sticky="w", padx=5, pady=3)
        color_btn = ttk.Button(details_frame, text="選択...", command=self._choose_color)
        color_btn.grid(row=2, column=2, sticky="w", padx=5)

        # 画像パス
        ttk.Label(details_frame, text="画像:").grid(row=3, column=0, sticky="w", padx=5, pady=3)
        self.image_path_entry = ttk.Entry(details_frame, state="readonly")
        self.image_path_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=3)
        image_btn = ttk.Button(details_frame, text="参照...", command=self._choose_image)
        image_btn.grid(row=3, column=2, sticky="w", padx=5)
        
        self._update_details_state(tk.DISABLED)


    def _load_characters_from_project(self):
        """プロジェクトデータからキャラクター情報を読み込む"""
        # 念のため現在の編集内容を保存（別のプロジェクトを開く前に）
        if self.selected_character_id and hasattr(self, 'name_entry'):
             self._save_current_character_data()
        
        self.characters.clear()
        # self.app.project_data['characters'] は辞書のリストのはず
        char_data_list = self.app.project_data.get("characters", [])
        
        # データが Character オブジェクトだった場合（既に処理済みの場合）はそのまま使う
        # データが辞書だった場合は Character.from_dict で変換する
        for char_data in char_data_list:
            if isinstance(char_data, Character):
                char = char_data
            elif isinstance(char_data, dict):
                char = Character.from_dict(char_data)
            else:
                continue # 不明なデータはスキップ
            self.characters[char.id] = char
        
        self._update_character_list()
        self.select_character(None)


    def _update_character_list(self):
        """UIのキャラクターリストを更新する"""
        self.char_tree.delete(*self.char_tree.get_children())
        sorted_chars = sorted(self.characters.values(), key=lambda c: c.name)
        for char in sorted_chars:
            self.char_tree.insert("", tk.END, iid=char.id, values=(char.name,))


    def _on_character_select(self, event=None):
        """キャラクターがリストで選択されたときの処理"""
        selection = self.char_tree.selection()
        if not selection:
            return
        
        char_id = selection[0]
        self.select_character(char_id)

    def select_character(self, char_id: Optional[str]):
        """指定されたIDのキャラクターを選択状態にする"""
        # 他のキャラクターの編集中データを保存
        if self.selected_character_id and self.selected_character_id != char_id:
             self._save_current_character_data()

        self.selected_character_id = char_id
        
        if char_id and char_id in self.characters:
            char = self.characters[char_id]
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, char.name)
            
            self.desc_text.delete("1.0", tk.END)
            self.desc_text.insert("1.0", char.description)
            
            self.color_swatch.config(bg=char.color)
            
            self.image_path_entry.config(state=tk.NORMAL)
            self.image_path_entry.delete(0, tk.END)
            self.image_path_entry.insert(0, char.image_path)
            self.image_path_entry.config(state="readonly")

            self._update_details_state(tk.NORMAL)
            self.delete_btn.config(state=tk.NORMAL)
        else:
            # 選択解除
            self.name_entry.delete(0, tk.END)
            self.desc_text.delete("1.0", tk.END)
            self.color_swatch.config(bg="#FFFFFF")
            self.image_path_entry.config(state=tk.NORMAL)
            self.image_path_entry.delete(0, tk.END)
            self.image_path_entry.config(state="readonly")
            
            self._update_details_state(tk.DISABLED)
            self.delete_btn.config(state=tk.DISABLED)


    def _update_details_state(self, state: str):
        """詳細編集フォームの有効/無効を切り替える"""
        self.name_entry.config(state=state)
        self.desc_text.config(state=state)
        # ボタンは常に有効でも良いかもしれないが、一貫性のため
        for child in self.name_entry.master.winfo_children():
            if isinstance(child, ttk.Button):
                child.config(state=state)


    def _save_current_character_data(self):
        """現在選択中のキャラクターの編集内容を保存する"""
        if not self.selected_character_id or self.selected_character_id not in self.characters:
            return
            
        char = self.characters[self.selected_character_id]
        char.name = self.name_entry.get()
        char.description = self.desc_text.get("1.0", tk.END).strip()
        # カラーと画像パスはボタン操作時に直接更新されるのでここでは不要

    def _on_data_changed(self, event=None):
        """フォームのデータが変更されたときに呼び出される"""
        if not self.selected_character_id: return
        self._save_current_character_data()
        self.app._mark_dirty()
        
        # Treeviewの表示を更新
        char = self.characters[self.selected_character_id]
        self.char_tree.item(char.id, values=(char.name,))


    def _add_character(self):
        self._save_current_character_data()
        new_char = Character()
        self.characters[new_char.id] = new_char
        self.app._mark_dirty()
        self._update_character_list()
        
        # 新しく追加したキャラクターを選択状態にする
        self.char_tree.selection_set(new_char.id)
        self.char_tree.focus(new_char.id)


    def _delete_character(self):
        if not self.selected_character_id: return
        char = self.characters[self.selected_character_id]

        # self.app.root を付けずに、直接 messagebox を呼び出す
        if not messagebox.askyesno(
            "確認", f"キャラクター '{char.name}' を削除しますか？\nこの操作は元に戻せません。", parent=self.main_frame):
            return
            
        del self.characters[self.selected_character_id]
        self.select_character(None)
        self.app._mark_dirty()
        self._update_character_list()


    def _choose_color(self):
        if not self.selected_character_id: return
        char = self.characters[self.selected_character_id]
        
        color_code = colorchooser.askcolor(title="テーマカラーを選択", initialcolor=char.color, parent=self.main_frame)
        if color_code and color_code[1]:
            char.color = color_code[1]
            self.color_swatch.config(bg=char.color)
            self.app._mark_dirty()

    def _choose_image(self):
        if not self.selected_character_id: return
        char = self.characters[self.selected_character_id]
        
        filepath = filedialog.askopenfilename(
            title="キャラクター画像を選択",
            filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.gif *.bmp"), ("すべてのファイル", "*.*")],
            parent=self.main_frame
        )
        if filepath:
            char.image_path = filepath
            self.image_path_entry.config(state=tk.NORMAL)
            self.image_path_entry.delete(0, tk.END)
            self.image_path_entry.insert(0, char.image_path)
            self.image_path_entry.config(state="readonly")
            self.app._mark_dirty()
