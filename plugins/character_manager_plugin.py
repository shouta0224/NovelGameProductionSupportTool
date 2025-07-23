# plugins/character_manager_plugin.py

import tkinter as tk
from tkinter import ttk, messagebox
import uuid

# メインアプリのファイル名に合わせて変更
from NovelGameProductionSupportTool import IPlugin, NovelGameEditor

class CharacterManagerPlugin(IPlugin):
    """キャラクター管理機能を提供するプラグイン"""
    def __init__(self, app: NovelGameEditor):
        super().__init__(app)
        self.menu_label = "キャラクター管理"
        self.manager_window = None

        # --- ここからが重要 ---
        # アプリケーションに、このプラグインが使うデータキーを登録する
        # これにより、新規プロジェクト作成時や古いファイルのロード時に
        # self.app.project_data['characters'] が確実に存在することが保証される
        self.app.register_data_key("characters", default_value=[])
        # --- ここまで ---

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
        
        # プラグインのウィンドウは、メインアプリのデータ(self.app)を直接参照・操作する
        self.manager_window = CharacterManagerWindow(self.app)

class CharacterManagerWindow(tk.Toplevel):
    def __init__(self, app: NovelGameEditor):
        super().__init__(app.root)
        self.app = app
        self.title("キャラクター管理")
        self.geometry("500x400")
        self.transient(app.root)
        self._create_widgets()
        self._populate_character_list()
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        columns = ("name", "description")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings")
        self.tree.heading("name", text="キャラクター名")
        self.tree.heading("description", text="説明")
        self.tree.column("name", width=150)
        self.tree.column("description", width=250)
        self.tree.grid(row=0, column=0, sticky="nsew")
        btn_frame = ttk.Frame(main_frame, padding=(0, 10))
        btn_frame.grid(row=1, column=0, sticky="ew")
        ttk.Button(btn_frame, text="追加", command=self._add_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="編集", command=self._edit_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="削除", command=self._delete_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="閉じる", command=self.destroy).pack(side=tk.RIGHT, padx=5)
    def _populate_character_list(self):
        self.tree.delete(*self.tree.get_children())
        for char in self.app.project_data["characters"]:
            self.tree.insert("", tk.END, iid=char["id"], values=(char["name"], char.get("description", "")))
    def _add_character(self):
        dialog = CharacterEditDialog(self, title="キャラクター追加")
        if dialog.result:
            new_char = {"id": str(uuid.uuid4()), "name": dialog.result["name"], "description": dialog.result["description"]}
            self.app.project_data["characters"].append(new_char)
            self.app._mark_dirty()
            self._populate_character_list()
    def _edit_character(self):
        selected_ids = self.tree.selection()
        if not selected_ids: return
        char_id = selected_ids[0]
        char_data = next((c for c in self.app.project_data["characters"] if c["id"] == char_id), None)
        if not char_data: return
        dialog = CharacterEditDialog(self, title="キャラクター編集", initial_data=char_data)
        if dialog.result:
            char_data["name"] = dialog.result["name"]
            char_data["description"] = dialog.result["description"]
            self.app._mark_dirty()
            self._populate_character_list()
    def _delete_character(self):
        selected_ids = self.tree.selection()
        if not selected_ids: return
        char_id = selected_ids[0]
        char_name = self.tree.item(char_id, "values")[0]
        if messagebox.askyesno("削除の確認", f"「{char_name}」を削除しますか？", parent=self):
            self.app.project_data["characters"] = [c for c in self.app.project_data["characters"] if c["id"] != char_id]
            self.app._mark_dirty()
            self._populate_character_list()

class CharacterEditDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_data=None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.result = None
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="名前:").grid(row=0, column=0, sticky="w", pady=5)
        self.name_entry = ttk.Entry(frame, width=30)
        self.name_entry.grid(row=0, column=1, sticky="ew")
        ttk.Label(frame, text="説明:").grid(row=1, column=0, sticky="w", pady=5)
        self.desc_entry = ttk.Entry(frame, width=30)
        self.desc_entry.grid(row=1, column=1, sticky="ew")
        if initial_data:
            self.name_entry.insert(0, initial_data.get("name", ""))
            self.desc_entry.insert(0, initial_data.get("description", ""))
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="キャンセル", command=self.destroy).pack(side=tk.LEFT, padx=5)
        self.wait_window(self)
    def _on_ok(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("入力エラー", "名前は必須です。", parent=self)
            return
        self.result = {"name": name, "description": self.desc_entry.get().strip()}
        self.destroy()