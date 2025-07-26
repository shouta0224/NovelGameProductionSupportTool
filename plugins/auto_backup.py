import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import datetime
import configparser
from typing import TYPE_CHECKING, Optional

# 型チェック時のみインポートを有効にする
if TYPE_CHECKING:
    from __main__ import IPlugin, NovelGameEditor

# IPluginを動的に取得
try:
    from __main__ import IPlugin
except ImportError:
    class IPlugin:
        def __init__(self, app): self.app = app

class BackupSettingsDialog(tk.Toplevel):
    """バックアップ設定用のダイアログ"""
    def __init__(self, parent, plugin: 'AutoBackupPlugin'):
        super().__init__(parent)
        self.plugin = plugin
        self.title("バックアップ設定")
        self.transient(parent)
        self.grab_set()
        
        self.enabled_var = tk.BooleanVar(value=self.plugin.is_enabled)
        self.interval_var = tk.IntVar(value=self.plugin.interval_minutes)
        
        self._create_widgets()
        self.resizable(False, False)
        self.wait_window(self)

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Checkbutton(
            main_frame, text="自動バックアップを有効にする", variable=self.enabled_var
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=5)
        
        ttk.Label(main_frame, text="バックアップ間隔 (分):").grid(row=1, column=0, sticky="w", pady=5)
        
        interval_spinbox = ttk.Spinbox(
            main_frame, from_=1, to=60, width=5, textvariable=self.interval_var
        )
        interval_spinbox.grid(row=1, column=1, sticky="w", padx=5)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(15, 0))
        
        ttk.Button(button_frame, text="保存", command=self._save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _save_settings(self):
        self.plugin.set_enabled(self.enabled_var.get())
        self.plugin.set_interval(self.interval_var.get())
        messagebox.showinfo("設定完了", "バックアップ設定を保存しました。", parent=self)
        self.destroy()

class AutoBackupPlugin(IPlugin):
    def setup(self) -> None:
        print("[プラグイン: AutoBackup] セットアップを開始します。")
        self.backup_job_id: Optional[str] = None
        
        # 設定の読み込み
        self._load_config()

        # バックアップ用ディレクトリの作成
        self.backup_dir = Path.cwd() / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        print(f"[プラグイン: AutoBackup] バックアップディレクトリ: '{self.backup_dir}'")

    def register(self) -> None:
        print("[プラグイン: AutoBackup] UIを登録します。")
        self.app.add_plugin_menu_command("バックアップ設定...", self.show_settings_dialog)
        if self.is_enabled:
            self.start_backup_timer()

    def teardown(self) -> None:
        print("[プラグイン: AutoBackup] 終了処理を実行します。")
        self.stop_backup_timer()
        self.app.remove_plugin_menu_command("バックアップ設定...")
    
    def _load_config(self):
        """config.iniから設定を読み込む"""
        config = self.app.config_manager.config
        if not config.has_section('BACKUP'):
            config.add_section('BACKUP')
            config.set('BACKUP', 'enabled', 'true')
            config.set('BACKUP', 'interval_minutes', '5')
            self.app.config_manager._save_config()

        self.is_enabled = config.getboolean('BACKUP', 'enabled', fallback=True)
        self.interval_minutes = config.getint('BACKUP', 'interval_minutes', fallback=5)

    def _save_config(self):
        """設定をconfig.iniに保存する"""
        config = self.app.config_manager.config
        if not config.has_section('BACKUP'):
            config.add_section('BACKUP')
        config.set('BACKUP', 'enabled', str(self.is_enabled).lower())
        config.set('BACKUP', 'interval_minutes', str(self.interval_minutes))
        self.app.config_manager._save_config()

    def show_settings_dialog(self):
        BackupSettingsDialog(self.app.root, self)
    
    def set_enabled(self, enabled: bool):
        if self.is_enabled == enabled:
            return
        self.is_enabled = enabled
        self._save_config()
        if self.is_enabled:
            self.start_backup_timer()
        else:
            self.stop_backup_timer()
            
    def set_interval(self, minutes: int):
        minutes = max(1, min(minutes, 60)) # 1分から60分の範囲に制限
        if self.interval_minutes == minutes:
            return
        self.interval_minutes = minutes
        self._save_config()
        # タイマーが動いていれば、新しい間隔で再スケジュール
        if self.is_enabled:
            self.stop_backup_timer()
            self.start_backup_timer()

    def start_backup_timer(self):
        if self.backup_job_id:
            self.app.root.after_cancel(self.backup_job_id)
        
        interval_ms = self.interval_minutes * 60 * 1000
        self.backup_job_id = self.app.root.after(interval_ms, self.perform_backup)
        print(f"[プラグイン: AutoBackup] {self.interval_minutes}分間隔のバックアップタイマーを開始しました。")

    def stop_backup_timer(self):
        if self.backup_job_id:
            self.app.root.after_cancel(self.backup_job_id)
            self.backup_job_id = None
            print("[プラグイン: AutoBackup] バックアップタイマーを停止しました。")

    def perform_backup(self):
        """バックアップ処理を実行し、次のタイマーをスケジュールする"""
        if not self.is_enabled:
            return

        # 変更がない場合はバックアップしない
        if not self.app.is_dirty:
            print("[プラグイン: AutoBackup] 変更がないため、バックアップをスキップしました。")
            self.start_backup_timer() # 次のタイマーを再設定
            return
        
        try:
            # プロジェクト名を取得
            if self.app.current_project_path:
                base_name = self.app.current_project_path.stem
            else:
                base_name = "Untitled"
            
            # 日時情報を付加
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{base_name}_backup_{timestamp}.ngp"
            backup_path = self.backup_dir / backup_filename
            
            # メインアプリの保存ロジックを呼び出す
            # _save_to_fileは成功時にTrueを返す
            success = self.app._save_to_file(backup_path, update_dirty_flag=False)

            if success:
                # バックアップ成功時はダーティフラグをリセットしない
                self.app._update_status_bar(f"プロジェクトをバックアップしました: {backup_filename}")
                print(f"[プラグイン: AutoBackup] バックアップ成功: {backup_path}")
            else:
                print("[プラグイン: AutoBackup] バックアップに失敗しました。")

        except Exception as e:
            print(f"[プラグイン: AutoBackup] バックアップ中にエラーが発生しました: {e}")
        
        finally:
            # 次のバックアップをスケジュール
            self.start_backup_timer()