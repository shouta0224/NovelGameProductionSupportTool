# plugins/my_exporter.py

from tkinter import messagebox, filedialog
import os

# ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓
# 【重要】メインアプリのファイル名に合わせて変更してください
# 例：ファイル名が "app.py" なら from app import IPlugin, NovelGameEditor
from NovelGameProductionSupportTool import IPlugin, NovelGameEditor
# ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑

class TextExporterPlugin(IPlugin):
    """
    プロジェクトの全シーンを単一のテキストファイルに書き出すプラグイン。
    """
    def __init__(self, app: NovelGameEditor):
        """プラグインの初期化。appインスタンスを受け取る。"""
        super().__init__(app)
        self.menu_label = "テキストファイルへ書き出す"

    def register(self):
        """
        アプリケーションに機能を登録します。
        ここでは「プラグイン」メニューに項目を追加しています。
        """
        self.app.add_plugin_menu_command(self.menu_label, self.export_to_text)

    def teardown(self):
        """
        プラグインがアンロードされる際のクリーンアップ処理。
        登録したメニュー項目を削除します。
        """
        self.app.remove_plugin_menu_command(self.menu_label)

    def export_to_text(self):
        """
        メニュー項目がクリックされたときに実行されるメインの処理。
        """
        if not self.app.scenes:
            messagebox.showwarning("書き出しエラー", "書き出すシーンがありません。", parent=self.app.root)
            return

        # 保存ダイアログを開いて、保存先のファイルパスを取得
        filepath = filedialog.asksaveasfilename(
            title="テキストファイルとして保存",
            defaultextension=".txt",
            filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")],
            # プロジェクト名に基づいて初期ファイル名を提案
            initialfile=f"{os.path.splitext(self.app.root.title())[0]}_export.txt"
        )

        if not filepath:
            # キャンセルされた場合は何もしない
            return

        try:
            # ファイルに書き出す内容を生成
            full_text = ""
            for scene in self.app.scenes:
                # self.app を通じてメインアプリのデータにアクセスできる
                full_text += f"■ {scene.name}\n"
                full_text += "--------------------------------\n"
                full_text += f"{scene.content}\n"
                full_text += "\n"
            
            # ファイルに書き込み
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_text)
            
            messagebox.showinfo("書き出し成功", f"プロジェクトをテキストファイルに書き出しました。\n{filepath}", parent=self.app.root)

        except Exception as e:
            messagebox.showerror("書き出しエラー", f"ファイルの書き出し中にエラーが発生しました:\n{e}", parent=self.app.root)