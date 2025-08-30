#!/usr/bin/env python3
"""
Automated Backup System for Crypto Bot
======================================

Features:
- Automated daily/hourly backups
- Database backups (SQLite, CSV files)
- Configuration backups
- Log file archival
- Cloud storage integration (optional)
- Backup verification and restoration
- Disaster recovery procedures
"""

import os
import shutil
import sqlite3
import json
import tarfile
import gzip
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import hashlib
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackupSystem:
    """Comprehensive backup system for crypto bot"""
    
    def __init__(self, config_path: str = "config/backup_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.backup_dir = Path(self.config.get('backup_directory', 'backups'))
        self.backup_dir.mkdir(exist_ok=True)
        
    def _load_config(self) -> Dict[str, Any]:
        """Load backup configuration"""
        default_config = {
            "backup_directory": "backups",
            "retention_days": 30,
            "compression_enabled": True,
            "verification_enabled": True,
            "files_to_backup": [
                "trade_history.csv",
                "tax_data.db", 
                "health_monitor.db",
                "risk_state.json",
                ".env",
                "config/",
                "dashboard/"
            ],
            "exclude_patterns": [
                "*.log",
                "*.pyc",
                "__pycache__/",
                ".git/",
                "node_modules/",
                "venv/",
                ".venv/"
            ],
            "schedule": {
                "hourly_backups": True,
                "daily_backups": True,
                "weekly_backups": True
            },
            "cloud_storage": {
                "enabled": False,
                "provider": "s3",  # s3, gcs, azure
                "bucket": "",
                "credentials": {}
            }
        }
        
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                # Create default config
                os.makedirs(os.path.dirname(self.config_path) if os.path.dirname(self.config_path) else '.', exist_ok=True)
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
        except Exception as e:
            logger.error(f"Error loading backup config: {e}")
            return default_config
            
    def create_backup(self, backup_type: str = "manual") -> Dict[str, Any]:
        """Create a comprehensive backup"""
        timestamp = datetime.now(timezone.utc)
        backup_name = f"crypto_bot_backup_{backup_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        backup_info = {
            "backup_name": backup_name,
            "backup_type": backup_type,
            "timestamp": timestamp.isoformat(),
            "files_backed_up": [],
            "total_size_bytes": 0,
            "checksum": "",
            "status": "in_progress"
        }
        
        try:
            logger.info(f"Starting {backup_type} backup: {backup_name}")
            
            # Backup files
            for file_pattern in self.config.get('files_to_backup', []):
                self._backup_file_or_directory(file_pattern, backup_path, backup_info)
                
            # Create database dumps
            self._create_database_dumps(backup_path, backup_info)
            
            # Create backup manifest
            self._create_backup_manifest(backup_path, backup_info)
            
            # Calculate total size
            backup_info["total_size_bytes"] = self._calculate_directory_size(backup_path)
            
            # Create compressed archive if enabled
            if self.config.get('compression_enabled', True):
                archive_path = self._create_compressed_archive(backup_path, backup_name)
                backup_info["compressed_archive"] = str(archive_path)
                backup_info["compressed_size_bytes"] = archive_path.stat().st_size
                
            # Calculate checksum
            if "compressed_archive" in backup_info:
                backup_info["checksum"] = self._calculate_file_checksum(backup_info["compressed_archive"])
            else:
                backup_info["checksum"] = self._calculate_directory_checksum(backup_path)
                
            # Verify backup if enabled
            if self.config.get('verification_enabled', True):
                verification_result = self._verify_backup(backup_info)
                backup_info["verification"] = verification_result
                
            backup_info["status"] = "completed"
            logger.info(f"Backup completed successfully: {backup_name}")
            
        except Exception as e:
            backup_info["status"] = "failed"
            backup_info["error"] = str(e)
            logger.error(f"Backup failed: {e}")
            
        # Save backup info
        info_file = backup_path / "backup_info.json"
        with open(info_file, 'w') as f:
            json.dump(backup_info, f, indent=2, default=str)
            
        return backup_info
        
    def _backup_file_or_directory(self, source_pattern: str, backup_path: Path, backup_info: Dict):
        """Backup individual file or directory"""
        source_path = Path(source_pattern)
        
        if source_path.is_file():
            # Single file backup
            dest_file = backup_path / source_path.name
            shutil.copy2(source_path, dest_file)
            backup_info["files_backed_up"].append({
                "source": str(source_path),
                "destination": str(dest_file),
                "size_bytes": source_path.stat().st_size,
                "type": "file"
            })
            logger.debug(f"Backed up file: {source_path}")
            
        elif source_path.is_dir():
            # Directory backup
            dest_dir = backup_path / source_path.name
            
            # Use shutil.copytree with ignore patterns
            ignore_patterns = self.config.get('exclude_patterns', [])
            
            def ignore_func(directory, files):
                ignored = []
                for pattern in ignore_patterns:
                    for file in files:
                        if self._matches_pattern(file, pattern):
                            ignored.append(file)
                return ignored
                
            shutil.copytree(source_path, dest_dir, ignore=ignore_func)
            
            # Count files and calculate size
            file_count = 0
            total_size = 0
            for file_path in dest_dir.rglob('*'):
                if file_path.is_file():
                    file_count += 1
                    total_size += file_path.stat().st_size
                    
            backup_info["files_backed_up"].append({
                "source": str(source_path),
                "destination": str(dest_dir),
                "size_bytes": total_size,
                "file_count": file_count,
                "type": "directory"
            })
            logger.debug(f"Backed up directory: {source_path} ({file_count} files)")
            
        else:
            logger.warning(f"Source not found or not accessible: {source_pattern}")
            
    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches ignore pattern"""
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)
        
    def _create_database_dumps(self, backup_path: Path, backup_info: Dict):
        """Create SQL dumps of SQLite databases"""
        db_dumps_dir = backup_path / "database_dumps"
        db_dumps_dir.mkdir(exist_ok=True)
        
        # Find SQLite databases
        sqlite_files = list(Path('.').glob('*.db')) + list(Path('.').glob('**/*.db'))
        
        for db_file in sqlite_files:
            if db_file.exists():
                try:
                    # Create SQL dump
                    dump_file = db_dumps_dir / f"{db_file.stem}_dump.sql"
                    
                    with sqlite3.connect(db_file) as conn:
                        with open(dump_file, 'w') as f:
                            for line in conn.iterdump():
                                f.write(f"{line}\n")
                                
                    backup_info["files_backed_up"].append({
                        "source": str(db_file),
                        "destination": str(dump_file),
                        "size_bytes": dump_file.stat().st_size,
                        "type": "database_dump"
                    })
                    
                    logger.debug(f"Created database dump: {db_file} -> {dump_file}")
                    
                except Exception as e:
                    logger.error(f"Failed to create dump for {db_file}: {e}")
                    
    def _create_backup_manifest(self, backup_path: Path, backup_info: Dict):
        """Create backup manifest with metadata"""
        manifest = {
            "backup_info": backup_info,
            "system_info": {
                "hostname": os.uname().nodename if hasattr(os, 'uname') else 'unknown',
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
                "working_directory": str(Path.cwd()),
                "backup_tool_version": "1.0.0"
            },
            "file_manifest": []
        }
        
        # Create detailed file manifest
        for item in backup_path.rglob('*'):
            if item.is_file() and item.name != 'manifest.json':
                try:
                    manifest["file_manifest"].append({
                        "path": str(item.relative_to(backup_path)),
                        "size_bytes": item.stat().st_size,
                        "modified_time": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                        "checksum": self._calculate_file_checksum(item)
                    })
                except Exception as e:
                    logger.warning(f"Failed to get manifest info for {item}: {e}")
                    
        # Save manifest
        manifest_file = backup_path / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2, default=str)
            
    def _create_compressed_archive(self, backup_path: Path, backup_name: str) -> Path:
        """Create compressed tar.gz archive"""
        archive_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(backup_path, arcname=backup_name)
            
        # Remove uncompressed directory to save space
        shutil.rmtree(backup_path)
        
        logger.debug(f"Created compressed archive: {archive_path}")
        return archive_path
        
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""
            
    def _calculate_directory_checksum(self, directory_path: Path) -> str:
        """Calculate aggregate checksum for directory"""
        hash_sha256 = hashlib.sha256()
        
        for file_path in sorted(directory_path.rglob('*')):
            if file_path.is_file():
                file_hash = self._calculate_file_checksum(file_path)
                hash_sha256.update(file_hash.encode())
                
        return hash_sha256.hexdigest()
        
    def _calculate_directory_size(self, directory_path: Path) -> int:
        """Calculate total size of directory"""
        total_size = 0
        for file_path in directory_path.rglob('*'):
            if file_path.is_file():
                try:
                    total_size += file_path.stat().st_size
                except:
                    pass
        return total_size
        
    def _verify_backup(self, backup_info: Dict) -> Dict[str, Any]:
        """Verify backup integrity"""
        verification = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "files_verified": 0,
            "files_failed": 0,
            "overall_status": "unknown",
            "details": []
        }
        
        try:
            if "compressed_archive" in backup_info:
                # Verify compressed archive
                archive_path = Path(backup_info["compressed_archive"])
                if archive_path.exists():
                    # Test archive integrity
                    with tarfile.open(archive_path, 'r:gz') as tar:
                        tar.getnames()  # This will fail if archive is corrupted
                    verification["files_verified"] = 1
                    verification["overall_status"] = "passed"
                else:
                    verification["files_failed"] = 1
                    verification["overall_status"] = "failed"
                    verification["details"].append("Compressed archive not found")
            else:
                verification["overall_status"] = "skipped"
                verification["details"].append("No compressed archive to verify")
                
        except Exception as e:
            verification["files_failed"] = 1
            verification["overall_status"] = "failed"
            verification["details"].append(f"Verification failed: {str(e)}")
            
        return verification
        
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        backups = []
        
        # Check for backup info files
        for info_file in self.backup_dir.glob('**/backup_info.json'):
            try:
                with open(info_file, 'r') as f:
                    backup_info = json.load(f)
                backups.append(backup_info)
            except Exception as e:
                logger.error(f"Failed to read backup info from {info_file}: {e}")
                
        # Sort by timestamp, newest first
        backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return backups
        
    def cleanup_old_backups(self, retention_days: int = None) -> int:
        """Clean up old backups based on retention policy"""
        if retention_days is None:
            retention_days = self.config.get('retention_days', 30)
            
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        deleted_count = 0
        
        backups = self.list_backups()
        
        for backup in backups:
            try:
                backup_date = datetime.fromisoformat(backup['timestamp'].replace('Z', '+00:00'))
                
                if backup_date < cutoff_date:
                    # Delete backup
                    backup_name = backup['backup_name']
                    
                    # Delete compressed archive if exists
                    if 'compressed_archive' in backup:
                        archive_path = Path(backup['compressed_archive'])
                        if archive_path.exists():
                            archive_path.unlink()
                            logger.info(f"Deleted old backup archive: {archive_path}")
                            
                    # Delete backup directory if exists
                    backup_dir = self.backup_dir / backup_name
                    if backup_dir.exists():
                        shutil.rmtree(backup_dir)
                        logger.info(f"Deleted old backup directory: {backup_dir}")
                        
                    deleted_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to delete old backup {backup.get('backup_name', 'unknown')}: {e}")
                
        logger.info(f"Cleaned up {deleted_count} old backups (retention: {retention_days} days)")
        return deleted_count
        
    def restore_backup(self, backup_name: str, restore_path: str = "restore") -> bool:
        """Restore from backup"""
        try:
            restore_dir = Path(restore_path)
            restore_dir.mkdir(exist_ok=True)
            
            # Find backup archive
            archive_path = self.backup_dir / f"{backup_name}.tar.gz"
            
            if not archive_path.exists():
                logger.error(f"Backup archive not found: {archive_path}")
                return False
                
            # Extract archive
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(restore_dir)
                
            logger.info(f"Backup restored successfully to: {restore_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_name}: {e}")
            return False

# Automated backup scheduler
def run_scheduled_backup():
    """Run scheduled backup based on configuration"""
    backup_system = BackupSystem()
    
    # Determine backup type based on schedule
    current_hour = datetime.now().hour
    current_day = datetime.now().weekday()
    
    if current_hour == 0 and current_day == 0:  # Weekly backup (Sunday midnight)
        backup_type = "weekly"
    elif current_hour == 0:  # Daily backup (midnight)
        backup_type = "daily"  
    else:  # Hourly backup
        backup_type = "hourly"
        
    # Create backup
    result = backup_system.create_backup(backup_type)
    
    # Cleanup old backups
    backup_system.cleanup_old_backups()
    
    return result

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Crypto Bot Backup System")
    parser.add_argument("--create", choices=["manual", "hourly", "daily", "weekly"], 
                       help="Create backup of specified type")
    parser.add_argument("--list", action="store_true", help="List all backups")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old backups")
    parser.add_argument("--restore", help="Restore backup by name")
    parser.add_argument("--restore-path", default="restore", help="Path for restoration")
    
    args = parser.parse_args()
    
    backup_system = BackupSystem()
    
    if args.create:
        result = backup_system.create_backup(args.create)
        print(f"Backup result: {json.dumps(result, indent=2, default=str)}")
        
    elif args.list:
        backups = backup_system.list_backups()
        print(f"Found {len(backups)} backups:")
        for backup in backups:
            status = backup.get('status', 'unknown')
            size_mb = backup.get('total_size_bytes', 0) / (1024 * 1024)
            print(f"  {backup['backup_name']} - {backup['timestamp']} - {status} - {size_mb:.1f}MB")
            
    elif args.cleanup:
        deleted = backup_system.cleanup_old_backups()
        print(f"Cleaned up {deleted} old backups")
        
    elif args.restore:
        success = backup_system.restore_backup(args.restore, args.restore_path)
        print(f"Restore {'successful' if success else 'failed'}")
        
    else:
        # Run scheduled backup
        result = run_scheduled_backup()
        print(f"Scheduled backup result: {json.dumps(result, indent=2, default=str)}")