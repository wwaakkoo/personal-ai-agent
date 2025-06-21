"""
Personal AI Agent - プライバシー保護システム
"""

import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)

class DataType(Enum):
    """データタイプ分類"""
    PERSONAL_INFO = "personal_info"
    CONVERSATION = "conversation"
    TASK_DATA = "task_data"
    SYSTEM_LOG = "system_log"
    ANALYTICS = "analytics"
    PREFERENCES = "preferences"

class ProcessingPurpose(Enum):
    """データ処理目的"""
    CORE_FUNCTIONALITY = "core_functionality"
    PERSONALIZATION = "personalization"
    ANALYTICS = "analytics"
    IMPROVEMENT = "improvement"
    SECURITY = "security"
    COMPLIANCE = "compliance"

class ConsentStatus(Enum):
    """同意状況"""
    GRANTED = "granted"
    DENIED = "denied"
    PENDING = "pending"
    WITHDRAWN = "withdrawn"

@dataclass
class DataProcessingRecord:
    """データ処理記録"""
    record_id: str
    data_type: DataType
    purpose: ProcessingPurpose
    processing_date: datetime
    retention_period: timedelta
    legal_basis: str
    user_consent: ConsentStatus
    anonymized: bool
    encrypted: bool
    metadata: Dict[str, Any]

@dataclass
class ConsentRecord:
    """同意記録"""
    consent_id: str
    user_id: str
    data_type: DataType
    purpose: ProcessingPurpose
    status: ConsentStatus
    granted_date: Optional[datetime]
    withdrawn_date: Optional[datetime]
    version: str
    consent_text: str

class PrivacyManager:
    """
    プライバシー保護管理システム
    
    GDPR準拠のデータ保護とプライバシー管理機能を提供
    """
    
    def __init__(self):
        self.processing_records: List[DataProcessingRecord] = []
        self.consent_records: Dict[str, ConsentRecord] = {}
        self.data_retention_policies: Dict[DataType, timedelta] = {}
        self.anonymization_rules: Dict[DataType, List[str]] = {}
        
        # デフォルト設定
        self._setup_default_policies()
        
        logger.info("PrivacyManager initialized")
    
    def _setup_default_policies(self) -> None:
        """デフォルトポリシーの設定"""
        
        # データ保持期間の設定
        self.data_retention_policies = {
            DataType.PERSONAL_INFO: timedelta(days=365 * 2),  # 2年
            DataType.CONVERSATION: timedelta(days=365),       # 1年
            DataType.TASK_DATA: timedelta(days=180),          # 6ヶ月
            DataType.SYSTEM_LOG: timedelta(days=90),          # 3ヶ月
            DataType.ANALYTICS: timedelta(days=365),          # 1年
            DataType.PREFERENCES: timedelta(days=365 * 5)     # 5年
        }
        
        # 匿名化ルール
        self.anonymization_rules = {
            DataType.PERSONAL_INFO: ["name", "email", "phone", "address"],
            DataType.CONVERSATION: ["name", "location", "personal_details"],
            DataType.TASK_DATA: ["personal_details", "location"],
            DataType.ANALYTICS: ["user_id", "ip_address", "device_id"]
        }
    
    def record_data_processing(self, 
                             data_type: DataType,
                             purpose: ProcessingPurpose,
                             user_id: str,
                             legal_basis: str = "legitimate_interest",
                             anonymized: bool = False,
                             encrypted: bool = True) -> str:
        """データ処理の記録"""
        
        import uuid
        record_id = str(uuid.uuid4())
        
        # ユーザー同意の確認
        consent_status = self.check_user_consent(user_id, data_type, purpose)
        
        record = DataProcessingRecord(
            record_id=record_id,
            data_type=data_type,
            purpose=purpose,
            processing_date=datetime.now(),
            retention_period=self.data_retention_policies.get(data_type, timedelta(days=365)),
            legal_basis=legal_basis,
            user_consent=consent_status,
            anonymized=anonymized,
            encrypted=encrypted,
            metadata={
                "user_id": user_id,
                "processing_system": "personal_ai_agent"
            }
        )
        
        self.processing_records.append(record)
        
        logger.info(f"Data processing recorded: {record_id}")
        return record_id
    
    def request_user_consent(self, 
                           user_id: str,
                           data_type: DataType,
                           purpose: ProcessingPurpose,
                           consent_text: str,
                           version: str = "1.0") -> str:
        """ユーザー同意の要求"""
        
        import uuid
        consent_id = str(uuid.uuid4())
        
        consent_record = ConsentRecord(
            consent_id=consent_id,
            user_id=user_id,
            data_type=data_type,
            purpose=purpose,
            status=ConsentStatus.PENDING,
            granted_date=None,
            withdrawn_date=None,
            version=version,
            consent_text=consent_text
        )
        
        self.consent_records[consent_id] = consent_record
        
        logger.info(f"Consent requested: {consent_id}")
        return consent_id
    
    def grant_consent(self, consent_id: str) -> bool:
        """同意の付与"""
        
        if consent_id not in self.consent_records:
            return False
        
        consent = self.consent_records[consent_id]
        consent.status = ConsentStatus.GRANTED
        consent.granted_date = datetime.now()
        
        logger.info(f"Consent granted: {consent_id}")
        return True
    
    def withdraw_consent(self, consent_id: str) -> bool:
        """同意の撤回"""
        
        if consent_id not in self.consent_records:
            return False
        
        consent = self.consent_records[consent_id]
        consent.status = ConsentStatus.WITHDRAWN
        consent.withdrawn_date = datetime.now()
        
        # 関連データの処理停止
        self._handle_consent_withdrawal(consent)
        
        logger.info(f"Consent withdrawn: {consent_id}")
        return True
    
    def check_user_consent(self, 
                          user_id: str,
                          data_type: DataType,
                          purpose: ProcessingPurpose) -> ConsentStatus:
        """ユーザー同意状況の確認"""
        
        for consent in self.consent_records.values():
            if (consent.user_id == user_id and 
                consent.data_type == data_type and 
                consent.purpose == purpose):
                return consent.status
        
        return ConsentStatus.PENDING
    
    def anonymize_data(self, data: Dict[str, Any], data_type: DataType) -> Dict[str, Any]:
        """データの匿名化"""
        
        rules = self.anonymization_rules.get(data_type, [])
        anonymized_data = data.copy()
        
        for field in rules:
            if field in anonymized_data:
                # フィールドをハッシュ化または削除
                if isinstance(anonymized_data[field], str):
                    anonymized_data[field] = self._hash_string(anonymized_data[field])
                else:
                    anonymized_data[field] = "[ANONYMIZED]"
        
        logger.debug(f"Data anonymized for type: {data_type}")
        return anonymized_data
    
    def pseudonymize_user_id(self, user_id: str, salt: str = "privacy_salt") -> str:
        """ユーザーIDの仮名化"""
        
        return self._hash_string(f"{user_id}{salt}")
    
    def generate_data_export(self, user_id: str) -> Dict[str, Any]:
        """ユーザーデータのエクスポート（GDPR Article 20対応）"""
        
        export_data = {
            "user_id": user_id,
            "export_date": datetime.now().isoformat(),
            "data_categories": {},
            "processing_records": [],
            "consent_records": []
        }
        
        # 処理記録の収集
        user_processing_records = [
            record for record in self.processing_records
            if record.metadata.get("user_id") == user_id
        ]
        
        export_data["processing_records"] = [
            {
                "record_id": record.record_id,
                "data_type": record.data_type.value,
                "purpose": record.purpose.value,
                "processing_date": record.processing_date.isoformat(),
                "retention_period_days": record.retention_period.days,
                "legal_basis": record.legal_basis
            }
            for record in user_processing_records
        ]
        
        # 同意記録の収集
        user_consent_records = [
            consent for consent in self.consent_records.values()
            if consent.user_id == user_id
        ]
        
        export_data["consent_records"] = [
            {
                "consent_id": consent.consent_id,
                "data_type": consent.data_type.value,
                "purpose": consent.purpose.value,
                "status": consent.status.value,
                "granted_date": consent.granted_date.isoformat() if consent.granted_date else None,
                "version": consent.version
            }
            for consent in user_consent_records
        ]
        
        logger.info(f"Data export generated for user: {user_id}")
        return export_data
    
    def delete_user_data(self, user_id: str, data_types: Optional[List[DataType]] = None) -> Dict[str, Any]:
        """ユーザーデータの削除（GDPR Article 17対応）"""
        
        deletion_summary = {
            "user_id": user_id,
            "deletion_date": datetime.now().isoformat(),
            "deleted_records": [],
            "anonymized_records": [],
            "retained_records": []
        }
        
        target_types = data_types or list(DataType)
        
        # 処理記録の削除・匿名化
        remaining_records = []
        for record in self.processing_records:
            if record.metadata.get("user_id") == user_id and record.data_type in target_types:
                if self._can_delete_record(record):
                    deletion_summary["deleted_records"].append(record.record_id)
                else:
                    # 法的要件により保持が必要な場合は匿名化
                    record.anonymized = True
                    record.metadata["user_id"] = self.pseudonymize_user_id(user_id)
                    deletion_summary["anonymized_records"].append(record.record_id)
                    remaining_records.append(record)
            else:
                remaining_records.append(record)
        
        self.processing_records = remaining_records
        
        logger.info(f"User data deletion completed for: {user_id}")
        return deletion_summary
    
    def cleanup_expired_data(self) -> Dict[str, int]:
        """期限切れデータの自動削除"""
        
        now = datetime.now()
        cleanup_summary = {"deleted_records": 0, "anonymized_records": 0}
        
        remaining_records = []
        
        for record in self.processing_records:
            expiry_date = record.processing_date + record.retention_period
            
            if expiry_date < now:
                if self._can_delete_record(record):
                    cleanup_summary["deleted_records"] += 1
                else:
                    # 匿名化して保持
                    record.anonymized = True
                    if "user_id" in record.metadata:
                        record.metadata["user_id"] = self.pseudonymize_user_id(
                            record.metadata["user_id"]
                        )
                    cleanup_summary["anonymized_records"] += 1
                    remaining_records.append(record)
            else:
                remaining_records.append(record)
        
        self.processing_records = remaining_records
        
        logger.info(f"Data cleanup completed: {cleanup_summary}")
        return cleanup_summary
    
    def audit_privacy_compliance(self) -> Dict[str, Any]:
        """プライバシー遵守監査"""
        
        audit_report = {
            "audit_date": datetime.now().isoformat(),
            "total_records": len(self.processing_records),
            "consent_summary": {},
            "encryption_status": {},
            "retention_compliance": {},
            "recommendations": []
        }
        
        # 同意状況の集計
        consent_counts = {}
        for consent in self.consent_records.values():
            status = consent.status.value
            consent_counts[status] = consent_counts.get(status, 0) + 1
        audit_report["consent_summary"] = consent_counts
        
        # 暗号化状況の集計
        encrypted_count = sum(1 for record in self.processing_records if record.encrypted)
        audit_report["encryption_status"] = {
            "encrypted": encrypted_count,
            "total": len(self.processing_records),
            "percentage": (encrypted_count / len(self.processing_records) * 100) if self.processing_records else 0
        }
        
        # 保持期間遵守状況
        now = datetime.now()
        overdue_count = 0
        for record in self.processing_records:
            if record.processing_date + record.retention_period < now:
                overdue_count += 1
        
        audit_report["retention_compliance"] = {
            "overdue_records": overdue_count,
            "compliance_rate": ((len(self.processing_records) - overdue_count) / len(self.processing_records) * 100) if self.processing_records else 100
        }
        
        # 推奨事項
        if overdue_count > 0:
            audit_report["recommendations"].append("期限切れデータの削除が必要です")
        
        if encrypted_count < len(self.processing_records):
            audit_report["recommendations"].append("未暗号化データの暗号化が必要です")
        
        logger.info("Privacy compliance audit completed")
        return audit_report
    
    def _handle_consent_withdrawal(self, consent: ConsentRecord) -> None:
        """同意撤回の処理"""
        
        # 関連する処理記録の更新
        for record in self.processing_records:
            if (record.metadata.get("user_id") == consent.user_id and
                record.data_type == consent.data_type and
                record.purpose == consent.purpose):
                record.user_consent = ConsentStatus.WITHDRAWN
    
    def _can_delete_record(self, record: DataProcessingRecord) -> bool:
        """記録を削除可能かチェック"""
        
        # 法的要件により保持が必要な場合
        legal_retention_purposes = [
            ProcessingPurpose.COMPLIANCE,
            ProcessingPurpose.SECURITY
        ]
        
        return record.purpose not in legal_retention_purposes
    
    def _hash_string(self, text: str) -> str:
        """文字列のハッシュ化"""
        
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def get_privacy_settings(self, user_id: str) -> Dict[str, Any]:
        """ユーザーのプライバシー設定取得"""
        
        user_consents = [
            consent for consent in self.consent_records.values()
            if consent.user_id == user_id
        ]
        
        settings = {
            "data_processing_consents": {},
            "retention_preferences": {},
            "anonymization_preferences": {}
        }
        
        for consent in user_consents:
            key = f"{consent.data_type.value}_{consent.purpose.value}"
            settings["data_processing_consents"][key] = {
                "status": consent.status.value,
                "granted_date": consent.granted_date.isoformat() if consent.granted_date else None,
                "version": consent.version
            }
        
        return settings
    
    def update_privacy_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """ユーザーのプライバシー設定更新"""
        
        try:
            # 同意設定の更新
            consents = settings.get("data_processing_consents", {})
            
            for consent_key, consent_data in consents.items():
                # 対応する同意記録を見つけて更新
                for consent in self.consent_records.values():
                    if (consent.user_id == user_id and
                        f"{consent.data_type.value}_{consent.purpose.value}" == consent_key):
                        
                        new_status = ConsentStatus(consent_data["status"])
                        if new_status != consent.status:
                            if new_status == ConsentStatus.WITHDRAWN:
                                self.withdraw_consent(consent.consent_id)
                            elif new_status == ConsentStatus.GRANTED:
                                self.grant_consent(consent.consent_id)
            
            logger.info(f"Privacy settings updated for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update privacy settings: {e}")
            return False