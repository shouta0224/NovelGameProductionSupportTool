from tkinter import messagebox
# from .plugin_interface import IPlugin
from plugin_interface import IPlugin

class ExamplePlugin(IPlugin):
    def setup(self):
        self.name = "サンプルプラグイン"
        
    def register(self):
        # メニューに項目を追加
        self.app.add_plugin_menu(
            label="サンプル機能",
            command=self.sample_function
        )
        
        # ツールバーにボタンを追加
        self.app.add_plugin_toolbar_button(
            text="サンプル",
            command=self.sample_function,
            image=None  # アイコン画像があれば指定
        )
    
    def sample_function(self):
        messagebox.showinfo("サンプル", "プラグイン機能が実行されました！")
    
    def teardown(self):
        # クリーンアップ処理
        pass
