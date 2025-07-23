# plugins/character_manager_plugin.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import uuid

# ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓
# 【重要】メインアプリのファイル名に合わせて変更してください
# 例：ファイル名が "app.py" なら from app import IPlugin, NovelGameEditor
from NovelGameProductionSupportTool import IPlugin, NovelGameEditor
# ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑

class CharacterManagerPlugin(IPlugin):
    """キャラクター管理機能を提供するプラグイン"""
    def __init__(self, app: NovelGameEditor):
        super().__init__(app)
        self.menu_label = "キャラクター管理"
        self.manager_window = None
        # アプリケーションに、このプラグインが使うデータキーを登録する
        self.app.register_data_key("characters", default_value=[])

    def register(self):
        """アプリケーションのメニューに項目を追加"""
        self.app.add_plugin_menu_command(self.menu_label, self.open_manager_window)

    def teardown(self):
        """メニュー項目を削除"""
        self.app.remove_plugin_menu_command(self.menu_label)

    def open_manager_window(self):
        """管理ウィンドウを開く"""
        if self.manager_window and self.manager_window.winfo_exists():
            self.manager_window.lift()
            return
        
        self.manager_window = CharacterManagerWindow(self.app)

class CharacterManagerWindow(tk.Toplevel):
    """キャラクターを管理するための専用ウィンドウ"""
    def __init__(self, app: NovelGameEditor):
        super().__init__(app.root)
        self.app = app
        self.title("キャラクター管理")
        self.geometry("700x400") # 横幅を広げる
        self.transient(app.root)

        self._create_widgets()
        self._populate_character_list()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # キャラクターリストの列を更新
        columns = ("name", "description", "image_path")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings")
        self.tree.heading("name", text="キャラクター名")
        self.tree.heading("description", text="説明")
        self.tree.heading("image_path", text="立ち絵パス") # 新しい列
        
        self.tree.column("name", width=150)
        self.tree.column("description", width=250)
        self.tree.column("image_path", width=200) # 新しい列の幅

        self.tree.grid(row=0, column=0, sticky="nsew")

        btn_frame = ttk.Frame(main_frame, padding=(0, 10))
        btn_frame.grid(row=1, column=0, sticky="ew")
        ttk.Button(btn_frame, text="追加", command=self._add_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="編集", command=self._edit_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="削除", command=self._delete_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="閉じる", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _populate_character_list(self):
        """ツリービューにキャラクターリストを表示する"""
        self.tree.delete(*self.tree.get_children())
        for char in self.app.project_data["characters"]:
            # Treeviewには説明の改行をスペースに置換して表示
            desc_preview = char.get("description", "").replace("\n", " ")
            values = (
                char["name"], 
                desc_preview,
                char.get("image_path", "") # image_pathも表示
            )
            self.tree.insert("", tk.END, iid=char["id"], values=values)

    def _add_character(self):
        """キャラクター追加処理"""
        dialog = CharacterEditDialog(self, title="キャラクター追加")
        if dialog.result:
            new_char = {
                "id": str(uuid.uuid4()),
                "name": dialog.result["name"],
                "description": dialog.result["description"],
                "image_path": dialog.result["image_path"]
            }
            self.app.project_data["characters"].append(new_char)
            self.app._mark_dirty()
            self._populate_character_list()

    def _edit_character(self):
        """キャラクター編集処理"""
        selected_ids = self.tree.selection()
        if not selected_ids: return
        
        char_id = selected_ids[0]
        char_data = next((c for c in self.app.project_data["characters"] if c["id"] == char_id), None)
        if not char_data: return

        dialog = CharacterEditDialog(self, title="キャラクター編集", initial_data=char_data)
        if dialog.result:
            char_data["name"] = dialog.result["name"]
            char_data["description"] = dialog.result["description"]
            char_data["image_path"] = dialog.result["image_path"]
            self.app._mark_dirty()
            self._populate_character_list()

    def _delete_character(self):
        """キャラクター削除処理"""
        selected_ids = self.tree.selection()
        if not selected_ids: return
            
        char_id = selected_ids[0]
        char_name = self.tree.item(char_id, "values")[0]
        if messagebox.askyesno("削除の確認", f"「{char_name}」を削除しますか？", parent=self):
            self.app.project_data["characters"] = [c for c in self.app.project_data["characters"] if c["id"] != char_id]
            self.app._mark_dirty()
            self._populate_character_list()

class CharacterEditDialog(tk.Toplevel):
    """キャラクターの情報を入力するためのモーダルダイアログ"""
    def __init__(self, parent, title, initial_data=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("450x350") # ウィンドウサイズを調整
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.rowconfigure(2, weight=1) # 説明欄が伸縮するように設定
        frame.columnconfigure(1, weight=1)

        # 名前
        ttk.Label(frame, text="名前:").grid(row=0, column=0, sticky="w", pady=5)
        self.name_entry = ttk.Entry(frame, width=40)
        self.name_entry.grid(row=0, column=1, columnspan=2, sticky="ew")
        
        # 説明 (複数行対応)
        ttk.Label(frame, text="説明:").grid(row=1, column=0, sticky="nw", pady=5)
        self.desc_text = tk.Text(frame, height=5, width=40, wrap=tk.WORD)
        self.desc_text.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(0, 5))
        
        # 立ち絵パス
        ttk.Label(frame, text="立ち絵パス:").grid(row=3, column=0, sticky="w", pady=5)
        self.image_path_var = tk.StringVar()
        self.path_entry = ttk.Entry(frame, textvariable=self.image_path_var, width=30)
        self.path_entry.grid(row=3, column=1, sticky="ew")
        browse_btn = ttk.Button(frame, text="参照...", command=self._browse_file)
        browse_btn.grid(row=3, column=2, sticky="w", padx=(5, 0))

        if initial_data:
            self.name_entry.insert(0, initial_data.get("name", ""))
            self.desc_text.insert("1.0", initial_data.get("description", ""))
            self.image_path_var.set(initial_data.get("image_path", ""))

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0))
        ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="キャンセル", command=self.destroy).pack(side=tk.LEFT, padx=5)

        self.wait_window(self)

    def _browse_file(self):
        """ファイルダイアログを開いて立ち絵ファイルを選択する"""
        filepath = filedialog.askopenfilename(
            title="立ち絵ファイルを選択",
            filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.gif"), ("すべてのファイル", "*.*")],
            parent=self
        )
        if filepath:
            self.image_path_var.set(filepath)

    def _on_ok(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("入力エラー", "名前は必須です。", parent=self)
            return
            
        self.result = {
            "name": name,
            "description": self.desc_text.get("1.0", tk.END).strip(),
            "image_path": self.image_path_var.get().strip()
        }
        self.destroy()