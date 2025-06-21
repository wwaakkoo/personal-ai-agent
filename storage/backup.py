# -*- coding: utf-8 -*-
"""
Personal AI Agent - バックアップ管理システム
"""

import os
import json
import gzip
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import asyncio
import subprocess

logger = logging.getLogger(__name__)

@dataclass
class BackupInfo:
    """バックアップ情報"""
    backup_id: str
    created_at: datetime
    backup_type: str  # full, incremental, config
    file_path: str
    file_size: int
    checksum: str
    description: str
    metadata: Dict[str, Any]

class BackupManager:
    """
    バックアップ管理システム
    
    データベース、設定ファイル、ユーザーデータの
    自動バックアップと復元機能を提供
    """
    
    def __init__(self, 
                 backup_dir: str = "./backups",
                 max_backups: int = 10,
                 compress: bool = True):
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        self.compress = compress
        
        # バックアップディレクトリの作成
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # バックアップ履歴ファイル
        self.history_file = self.backup_dir / "backup_history.json"
        self.backup_history: List[BackupInfo] = []
        
        logger.info(f"BackupManager initialized: {self.backup_dir}")
    
    async def initialize(self) -> None:
        """バックアップシステムの初期化"""
        try:
            await self._load_backup_history()
            await self._cleanup_old_backups()
            
            logger.info("BackupManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize backup manager: {e}")
            raise
    
    async def create_full_backup(self, 
                               database_url: str,
                               config_files: List[str],
                               user_data_dirs: Optional[List[str]] = None,
                               description: str = "Automatic full backup") -> BackupInfo:
        """フルバックアップの作成"""
        
        backup_id = f"full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.backup_dir / f"{backup_id}.tar.gz"
        
        try:
            # 一時ディレクトリでバックアップデータを準備
            temp_dir = self.backup_dir / f"temp_{backup_id}"
            temp_dir.mkdir(exist_ok=True)
            
            # データベースバックアップ
            await self._backup_database(database_url, temp_dir / "database.sql")
            
            # 設定ファイルのバックアップ
            config_backup_dir = temp_dir / "config"
            config_backup_dir.mkdir(exist_ok=True)
            for config_file in config_files:
                if os.path.exists(config_file):
                    shutil.copy2(config_file, config_backup_dir / Path(config_file).name)
            
            # ユーザーデータのバックアップ
            if user_data_dirs:
                data_backup_dir = temp_dir / "user_data"
                data_backup_dir.mkdir(exist_ok=True)
                for data_dir in user_data_dirs:
                    if os.path.exists(data_dir):
                        dir_name = Path(data_dir).name
                        shutil.copytree(data_dir, data_backup_dir / dir_name)
            
            # メタデータファイルの作成
            metadata = {
                "backup_id": backup_id,
                "backup_type": "full",
                "created_at": datetime.now().isoformat(),
                "database_url": database_url,
                "config_files": config_files,
                "user_data_dirs": user_data_dirs or [],
                "description": description
            }
            
            with open(temp_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # アーカイブの作成
            await self._create_archive(temp_dir, backup_path)
            
            # 一時ディレクトリの削除
            shutil.rmtree(temp_dir)
            
            # チェックサムの計算
            checksum = await self._calculate_checksum(backup_path)
            
            # バックアップ情報の作成
            backup_info = BackupInfo(
                backup_id=backup_id,
                created_at=datetime.now(),
                backup_type="full",
                file_path=str(backup_path),
                file_size=backup_path.stat().st_size,
                checksum=checksum,
                description=description,
                metadata=metadata
            )
            
            # 履歴に追加
            self.backup_history.append(backup_info)
            await self._save_backup_history()
            
            logger.info(f"Full backup created: {backup_id}")
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to create full backup: {e}")
            # 一時ファイルのクリーンアップ
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            if backup_path.exists():
                backup_path.unlink()
            raise
    
    async def create_config_backup(self, 
                                 config_files: List[str],
                                 description: str = "Configuration backup") -> BackupInfo:
        """設定ファイルのみのバックアップ"""
        
        backup_id = f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.backup_dir / f"{backup_id}.tar.gz"
        
        try:
            temp_dir = self.backup_dir / f"temp_{backup_id}"
            temp_dir.mkdir(exist_ok=True)
            
            # 設定ファイルのコピー
            for config_file in config_files:
                if os.path.exists(config_file):
                    shutil.copy2(config_file, temp_dir / Path(config_file).name)
            
            # メタデータ
            metadata = {
                "backup_id": backup_id,
                "backup_type": "config",
                "created_at": datetime.now().isoformat(),
                "config_files": config_files,
                "description": description
            }
            
            with open(temp_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # アーカイブ作成
            await self._create_archive(temp_dir, backup_path)
            shutil.rmtree(temp_dir)
            
            checksum = await self._calculate_checksum(backup_path)
            
            backup_info = BackupInfo(
                backup_id=backup_id,
                created_at=datetime.now(),
                backup_type="config",
                file_path=str(backup_path),
                file_size=backup_path.stat().st_size,
                checksum=checksum,
                description=description,
                metadata=metadata
            )
            
            self.backup_history.append(backup_info)
            await self._save_backup_history()
            
            logger.info(f"Config backup created: {backup_id}")
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to create config backup: {e}")
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            if backup_path.exists():
                backup_path.unlink()
            raise
    
    async def restore_backup(self, 
                           backup_id: str,
                           restore_database: bool = True,
                           restore_config: bool = True,
                           restore_user_data: bool = True) -> bool:
        """バックアップからの復元"""
        
        try:
            # バックアップ情報の取得
            backup_info = await self.get_backup_info(backup_id)
            if not backup_info:
                raise ValueError(f"Backup not found: {backup_id}")
            
            backup_path = Path(backup_info.file_path)
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # チェックサムの検証
            if not await self._verify_checksum(backup_path, backup_info.checksum):
                raise ValueError("Backup file checksum verification failed")
            
            # 復元用一時ディレクトリ
            restore_dir = self.backup_dir / f"restore_{backup_id}"
            restore_dir.mkdir(exist_ok=True)
            
            # アーカイブの展開
            await self._extract_archive(backup_path, restore_dir)
            
            # メタデータの読み込み
            metadata_file = restore_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            else:
                metadata = backup_info.metadata
            
            # データベースの復元
            if restore_database and (restore_dir / "database.sql").exists():
                await self._restore_database(
                    metadata.get("database_url", ""),
                    restore_dir / "database.sql"
                )
                logger.info("Database restored")
            
            # 設定ファイルの復元
            if restore_config and (restore_dir / "config").exists():
                await self._restore_config_files(
                    restore_dir / "config",
                    metadata.get("config_files", [])
                )
                logger.info("Configuration files restored")
            
            # ユーザーデータの復元
            if restore_user_data and (restore_dir / "user_data").exists():
                await self._restore_user_data(
                    restore_dir / "user_data",
                    metadata.get("user_data_dirs", [])
                )
                logger.info("User data restored")
            
            # 一時ディレクトリの削除
            shutil.rmtree(restore_dir)
            
            logger.info(f"Backup restored successfully: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            # クリーンアップ
            if restore_dir.exists():
                shutil.rmtree(restore_dir)
            return False
    
    async def list_backups(self, backup_type: Optional[str] = None) -> List[BackupInfo]:
        """バックアップ一覧を取得"""
        
        if backup_type:
            return [b for b in self.backup_history if b.backup_type == backup_type]
        else:
            return self.backup_history.copy()
    
    async def get_backup_info(self, backup_id: str) -> Optional[BackupInfo]:
        """特定のバックアップ情報を取得"""
        
        for backup in self.backup_history:
            if backup.backup_id == backup_id:
                return backup
        return None
    
    async def delete_backup(self, backup_id: str) -> bool:
        """バックアップを削除"""
        
        try:
            backup_info = await self.get_backup_info(backup_id)
            if not backup_info:
                return False
            
            # ファイル削除
            backup_path = Path(backup_info.file_path)
            if backup_path.exists():
                backup_path.unlink()
            
            # 履歴から削除
            self.backup_history = [b for b in self.backup_history if b.backup_id != backup_id]
            await self._save_backup_history()
            
            logger.info(f"Backup deleted: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False
    
    async def _backup_database(self, database_url: str, output_file: Path) -> None:
        """データベースのバックアップ"""
        
        try:
            if database_url.startswith("sqlite"):
                # SQLite の場合はファイルコピー
                db_file = database_url.replace("sqlite:///", "")
                if os.path.exists(db_file):
                    shutil.copy2(db_file, output_file.with_suffix(".db"))
            
            elif database_url.startswith("postgresql"):
                # PostgreSQL の場合は pg_dump を使用
                # 実際の実装では pg_dump コマンドを実行
                # subprocess.run(["pg_dump", database_url, "-f", str(output_file)])
                pass
            
            else:
                logger.warning(f"Unsupported database type for backup: {database_url}")
                
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            raise
    
    async def _restore_database(self, database_url: str, backup_file: Path) -> None:
        """データベースの復元"""
        
        try:
            if database_url.startswith("sqlite"):
                # SQLite の場合はファイル復元
                db_file = database_url.replace("sqlite:///", "")
                if backup_file.with_suffix(".db").exists():
                    shutil.copy2(backup_file.with_suffix(".db"), db_file)
            
            elif database_url.startswith("postgresql"):
                # PostgreSQL の場合は psql を使用
                # subprocess.run(["psql", database_url, "-f", str(backup_file)])
                pass
            
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            raise
    
    async def _restore_config_files(self, config_dir: Path, original_paths: List[str]) -> None:
        """設定ファイルの復元"""
        
        for original_path in original_paths:
            config_name = Path(original_path).name
            backup_config = config_dir / config_name
            
            if backup_config.exists():
                # バックアップを作成してから復元
                if os.path.exists(original_path):
                    backup_current = f"{original_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(original_path, backup_current)
                
                # 復元
                os.makedirs(Path(original_path).parent, exist_ok=True)
                shutil.copy2(backup_config, original_path)
                logger.info(f"Restored config file: {original_path}")
    
    async def _restore_user_data(self, data_dir: Path, original_dirs: List[str]) -> None:
        """ユーザーデータの復元"""
        
        for original_dir in original_dirs:
            dir_name = Path(original_dir).name
            backup_data_dir = data_dir / dir_name
            
            if backup_data_dir.exists():
                # 現在のディレクトリをバックアップ
                if os.path.exists(original_dir):
                    backup_current = f"{original_dir}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.move(original_dir, backup_current)
                
                # 復元
                shutil.copytree(backup_data_dir, original_dir)
                logger.info(f"Restored user data: {original_dir}")
    
    async def _create_archive(self, source_dir: Path, output_path: Path) -> None:
        """アーカイブの作成"""
        
        if self.compress:
            # gzip 圧縮 tar アーカイブ
            shutil.make_archive(
                str(output_path.with_suffix("")),
                "gztar",
                str(source_dir)
            )
        else:
            # 無圧縮 tar アーカイブ
            shutil.make_archive(
                str(output_path.with_suffix("")),
                "tar",
                str(source_dir)
            )
    
    async def _extract_archive(self, archive_path: Path, extract_dir: Path) -> None:
        """アーカイブの展開"""
        
        shutil.unpack_archive(str(archive_path), str(extract_dir))
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """ファイルのチェックサムを計算"""
        
        import hashlib
        
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    async def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """チェックサムの検証"""
        
        actual_checksum = await self._calculate_checksum(file_path)
        return actual_checksum == expected_checksum
    
    async def _load_backup_history(self) -> None:
        """バックアップ履歴の読み込み"""
        
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
                
                self.backup_history = [
                    BackupInfo(
                        backup_id=item["backup_id"],
                        created_at=datetime.fromisoformat(item["created_at"]),
                        backup_type=item["backup_type"],
                        file_path=item["file_path"],
                        file_size=item["file_size"],
                        checksum=item["checksum"],
                        description=item["description"],
                        metadata=item["metadata"]
                    )
                    for item in history_data
                ]
                
                logger.info(f"Loaded {len(self.backup_history)} backup records")
                
            except Exception as e:
                logger.error(f"Failed to load backup history: {e}")
                self.backup_history = []
    
    async def _save_backup_history(self) -> None:
        """バックアップ履歴の保存"""
        
        try:
            history_data = [
                {
                    "backup_id": backup.backup_id,
                    "created_at": backup.created_at.isoformat(),
                    "backup_type": backup.backup_type,
                    "file_path": backup.file_path,
                    "file_size": backup.file_size,
                    "checksum": backup.checksum,
                    "description": backup.description,
                    "metadata": backup.metadata
                }
                for backup in self.backup_history
            ]
            
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save backup history: {e}")
            raise
    
    async def _cleanup_old_backups(self) -> None:
        """古いバックアップの削除"""
        
        if len(self.backup_history) <= self.max_backups:
            return
        
        # 作成日時でソートして古いものから削除
        sorted_backups = sorted(self.backup_history, key=lambda x: x.created_at)
        backups_to_delete = sorted_backups[:-self.max_backups]
        
        for backup in backups_to_delete:
            await self.delete_backup(backup.backup_id)
        
        logger.info(f"Cleaned up {len(backups_to_delete)} old backups")
    
    async def get_stats(self) -> Dict[str, Any]:
        """バックアップ統計を取得"""
        
        total_size = sum(backup.file_size for backup in self.backup_history)
        
        type_counts = {}
        for backup in self.backup_history:
            type_counts[backup.backup_type] = type_counts.get(backup.backup_type, 0) + 1
        
        return {
            "total_backups": len(self.backup_history),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "backup_types": type_counts,
            "latest_backup": self.backup_history[-1].created_at.isoformat() if self.backup_history else None,
            "backup_directory": str(self.backup_dir)
        }