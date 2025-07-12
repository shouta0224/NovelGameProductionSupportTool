import uuid

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
