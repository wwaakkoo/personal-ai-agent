"""
Personal AI Agent - データベース管理システム
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Type
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from config.settings import DatabaseConfig

logger = logging.getLogger(__name__)

Base = declarative_base()

class User(Base):
    """ユーザー情報テーブル"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    full_name = Column(String(100), nullable=True)
    preferences = Column(JSON, nullable=True)
    timezone = Column(String(50), default="Asia/Tokyo")
    language = Column(String(10), default="ja")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # リレーション
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")

class Session(Base):
    """セッション管理テーブル"""
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    interaction_count = Column(Integer, default=0)
    context_data = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    
    # リレーション
    user = relationship("User", back_populates="sessions")
    interactions = relationship("Interaction", back_populates="session", cascade="all, delete-orphan")

class Memory(Base):
    """記憶・学習データテーブル"""
    __tablename__ = "memories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=False)  # interaction, learning, knowledge, preference
    importance = Column(Float, default=0.5)
    access_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    expiry_date = Column(DateTime, nullable=True)
    tags = Column(JSON, nullable=True)  # リスト形式で保存
    metadata = Column(JSON, nullable=True)
    
    # リレーション
    user = relationship("User", back_populates="memories")

class Interaction(Base):
    """対話履歴テーブル"""
    __tablename__ = "interactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    user_input = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=False)
    intent = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)
    response_time = Column(Float, nullable=True)  # レスポンス時間（秒）
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, nullable=True)
    
    # リレーション
    session = relationship("Session", back_populates="interactions")

class Task(Base):
    """タスク管理テーブル"""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending, in_progress, completed, cancelled
    priority = Column(String(10), default="medium")  # low, medium, high, urgent
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tags = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # リレーション
    user = relationship("User", back_populates="tasks")

class Knowledge(Base):
    """知識ベーステーブル"""
    __tablename__ = "knowledge"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(200), nullable=True)
    source_url = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    importance = Column(Float, default=0.5)
    access_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, nullable=True)
    tags = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)

class AuditLog(Base):
    """監査ログテーブル"""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    """
    データベース管理クラス
    
    SQLAlchemy を使用してデータベースとの統一的なインターフェースを提供
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """データベースの初期化"""
        try:
            # エンジンの作成
            self.engine = create_engine(
                self.config.url,
                echo=self.config.echo,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow
            )
            
            # セッションファクトリの作成
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # テーブルの作成
            await self._create_tables()
            
            self._initialized = True
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _create_tables(self) -> None:
        """テーブルの作成"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")
    
    def get_session(self) -> Session:
        """データベースセッションを取得"""
        if not self._initialized:
            raise RuntimeError("Database not initialized")
        
        return self.SessionLocal()
    
    async def create_user(self, 
                         username: str,
                         email: Optional[str] = None,
                         full_name: Optional[str] = None,
                         preferences: Optional[Dict[str, Any]] = None) -> User:
        """新しいユーザーを作成"""
        
        with self.get_session() as db:
            try:
                user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    preferences=preferences or {}
                )
                
                db.add(user)
                db.commit()
                db.refresh(user)
                
                logger.info(f"Created user: {username}")
                return user
                
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to create user: {e}")
                raise
    
    async def get_user(self, user_id: Optional[str] = None, username: Optional[str] = None) -> Optional[User]:
        """ユーザーを取得"""
        
        with self.get_session() as db:
            try:
                if user_id:
                    return db.query(User).filter(User.id == user_id).first()
                elif username:
                    return db.query(User).filter(User.username == username).first()
                else:
                    raise ValueError("Either user_id or username must be provided")
                    
            except Exception as e:
                logger.error(f"Failed to get user: {e}")
                return None
    
    async def create_session(self, user_id: str) -> Session:
        """新しいセッションを作成"""
        
        with self.get_session() as db:
            try:
                session = Session(user_id=user_id)
                
                db.add(session)
                db.commit()
                db.refresh(session)
                
                return session
                
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to create session: {e}")
                raise
    
    async def end_session(self, session_id: str, summary: Optional[str] = None) -> None:
        """セッションを終了"""
        
        with self.get_session() as db:
            try:
                session = db.query(Session).filter(Session.id == session_id).first()
                if session:
                    session.end_time = datetime.utcnow()
                    if summary:
                        session.summary = summary
                    
                    db.commit()
                
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to end session: {e}")
                raise
    
    async def store_interaction(self, 
                              session_id: str,
                              user_input: str,
                              agent_response: str,
                              intent: Optional[Dict[str, Any]] = None,
                              confidence: Optional[float] = None,
                              response_time: Optional[float] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> Interaction:
        """対話履歴を保存"""
        
        with self.get_session() as db:
            try:
                interaction = Interaction(
                    session_id=session_id,
                    user_input=user_input,
                    agent_response=agent_response,
                    intent=intent,
                    confidence=confidence,
                    response_time=response_time,
                    metadata=metadata
                )
                
                db.add(interaction)
                
                # セッションの対話回数を更新
                session = db.query(Session).filter(Session.id == session_id).first()
                if session:
                    session.interaction_count += 1
                
                db.commit()
                db.refresh(interaction)
                
                return interaction
                
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to store interaction: {e}")
                raise
    
    async def store_memory(self, 
                          user_id: str,
                          content: str,
                          content_type: str,
                          importance: float = 0.5,
                          tags: Optional[List[str]] = None,
                          metadata: Optional[Dict[str, Any]] = None,
                          expiry_date: Optional[datetime] = None) -> Memory:
        """記憶データを保存"""
        
        with self.get_session() as db:
            try:
                memory = Memory(
                    user_id=user_id,
                    content=content,
                    content_type=content_type,
                    importance=importance,
                    tags=tags or [],
                    metadata=metadata,
                    expiry_date=expiry_date
                )
                
                db.add(memory)
                db.commit()
                db.refresh(memory)
                
                return memory
                
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to store memory: {e}")
                raise
    
    async def search_memories(self, 
                            user_id: str,
                            query: Optional[str] = None,
                            content_type: Optional[str] = None,
                            tags: Optional[List[str]] = None,
                            limit: int = 10) -> List[Memory]:
        """記憶データを検索"""
        
        with self.get_session() as db:
            try:
                query_obj = db.query(Memory).filter(Memory.user_id == user_id)
                
                if content_type:
                    query_obj = query_obj.filter(Memory.content_type == content_type)
                
                if query:
                    # 簡単なテキスト検索（実際の実装では全文検索を使用）
                    query_obj = query_obj.filter(Memory.content.contains(query))
                
                if tags:
                    # JSONフィールドでのタグ検索
                    for tag in tags:
                        query_obj = query_obj.filter(Memory.tags.contains([tag]))
                
                memories = query_obj.order_by(
                    Memory.importance.desc(),
                    Memory.last_accessed.desc()
                ).limit(limit).all()
                
                # アクセス履歴の更新
                for memory in memories:
                    memory.access_count += 1
                    memory.last_accessed = datetime.utcnow()
                
                db.commit()
                
                return memories
                
            except Exception as e:
                logger.error(f"Failed to search memories: {e}")
                return []
    
    async def create_task(self, 
                         user_id: str,
                         title: str,
                         description: Optional[str] = None,
                         priority: str = "medium",
                         due_date: Optional[datetime] = None,
                         tags: Optional[List[str]] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> Task:
        """新しいタスクを作成"""
        
        with self.get_session() as db:
            try:
                task = Task(
                    user_id=user_id,
                    title=title,
                    description=description,
                    priority=priority,
                    due_date=due_date,
                    tags=tags or [],
                    metadata=metadata
                )
                
                db.add(task)
                db.commit()
                db.refresh(task)
                
                return task
                
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to create task: {e}")
                raise
    
    async def get_tasks(self, 
                       user_id: str,
                       status: Optional[str] = None,
                       priority: Optional[str] = None,
                       limit: int = 50) -> List[Task]:
        """タスク一覧を取得"""
        
        with self.get_session() as db:
            try:
                query_obj = db.query(Task).filter(Task.user_id == user_id)
                
                if status:
                    query_obj = query_obj.filter(Task.status == status)
                
                if priority:
                    query_obj = query_obj.filter(Task.priority == priority)
                
                return query_obj.order_by(
                    Task.priority.desc(),
                    Task.created_at.desc()
                ).limit(limit).all()
                
            except Exception as e:
                logger.error(f"Failed to get tasks: {e}")
                return []
    
    async def log_audit(self, 
                       user_id: Optional[str],
                       action: str,
                       resource_type: Optional[str] = None,
                       resource_id: Optional[str] = None,
                       details: Optional[Dict[str, Any]] = None,
                       ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None) -> None:
        """監査ログを記録"""
        
        with self.get_session() as db:
            try:
                audit_log = AuditLog(
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=details,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                db.add(audit_log)
                db.commit()
                
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to log audit: {e}")
    
    async def cleanup_old_data(self, days: int = 90) -> None:
        """古いデータの清掃"""
        
        with self.get_session() as db:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                # 期限切れの記憶データを削除
                expired_memories = db.query(Memory).filter(
                    Memory.expiry_date < datetime.utcnow()
                ).all()
                
                for memory in expired_memories:
                    db.delete(memory)
                
                # 古い監査ログを削除
                old_logs = db.query(AuditLog).filter(
                    AuditLog.created_at < cutoff_date
                ).all()
                
                for log in old_logs:
                    db.delete(log)
                
                db.commit()
                
                logger.info(f"Cleaned up {len(expired_memories)} expired memories and {len(old_logs)} old audit logs")
                
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to cleanup old data: {e}")
                raise
    
    async def get_statistics(self) -> Dict[str, Any]:
        """データベース統計を取得"""
        
        with self.get_session() as db:
            try:
                stats = {
                    "users": db.query(User).count(),
                    "active_users": db.query(User).filter(User.is_active == True).count(),
                    "sessions": db.query(Session).count(),
                    "active_sessions": db.query(Session).filter(Session.end_time.is_(None)).count(),
                    "interactions": db.query(Interaction).count(),
                    "memories": db.query(Memory).count(),
                    "tasks": db.query(Task).count(),
                    "pending_tasks": db.query(Task).filter(Task.status == "pending").count(),
                    "knowledge_items": db.query(Knowledge).count()
                }
                
                return stats
                
            except Exception as e:
                logger.error(f"Failed to get statistics: {e}")
                return {}
    
    async def close(self) -> None:
        """データベース接続を閉じる"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")