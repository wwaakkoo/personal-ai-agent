"""
Personal AI Agent - タスクマネージャーテスト
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from modules.task_manager import TaskManager, Task, TaskStatus, TaskPriority

class TestTaskManager:
    """タスクマネージャーのテストクラス"""
    
    @pytest.fixture
    async def task_manager(self):
        """TaskManagerのフィクスチャ"""
        memory_system = Mock()
        memory_system.store_knowledge = AsyncMock()
        
        llm_provider = Mock()
        llm_provider.generate_response = AsyncMock()
        
        return TaskManager(memory_system, llm_provider)
    
    @pytest.mark.asyncio
    async def test_create_task(self, task_manager):
        """タスク作成のテスト"""
        task = await task_manager.create_task(
            title="テストタスク",
            description="テスト用のタスクです",
            priority=TaskPriority.HIGH
        )
        
        assert task.title == "テストタスク"
        assert task.description == "テスト用のタスクです"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
        assert task.id in task_manager.tasks
    
    @pytest.mark.asyncio
    async def test_complete_task(self, task_manager):
        """タスク完了のテスト"""
        # タスク作成
        task = await task_manager.create_task("完了テスト")
        task_id = task.id
        
        # タスク完了
        result = await task_manager.complete_task(task_id)
        
        assert result is True
        assert task_manager.tasks[task_id].status == TaskStatus.COMPLETED
        assert task_manager.tasks[task_id].completed_at is not None
    
    @pytest.mark.asyncio
    async def test_task_intent_analysis(self, task_manager):
        """タスク意図分析のテスト"""
        # 作成意図
        intent = await task_manager._analyze_task_intent("新しいタスクを作成してください")
        assert intent["action"] == "create"
        
        # 一覧意図
        intent = await task_manager._analyze_task_intent("タスク一覧を表示")
        assert intent["action"] == "list"
        
        # 完了意図
        intent = await task_manager._analyze_task_intent("タスクを完了にしたい")
        assert intent["action"] == "complete"
    
    @pytest.mark.asyncio
    async def test_priority_detection(self, task_manager):
        """優先度検出のテスト"""
        intent = await task_manager._analyze_task_intent("緊急のタスクを作成")
        assert intent["filters"].get("priority") == TaskPriority.URGENT
        
        intent = await task_manager._analyze_task_intent("重要なタスクを表示")
        assert intent["filters"].get("priority") == TaskPriority.HIGH
    
    def test_task_filter_matching(self, task_manager):
        """タスクフィルタリングのテスト"""
        # テストタスク作成
        task = Task(
            id="test_id",
            title="テストタスク",
            description="説明",
            status=TaskStatus.PENDING,
            priority=TaskPriority.HIGH,
            due_date=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            completed_at=None,
            tags=["test"],
            estimated_duration=None,
            actual_duration=None,
            dependencies=[],
            subtasks=[],
            metadata={}
        )
        
        # 優先度フィルター
        assert task_manager._task_matches_filters(task, {"priority": TaskPriority.HIGH})
        assert not task_manager._task_matches_filters(task, {"priority": TaskPriority.LOW})
        
        # ステータスフィルター
        assert task_manager._task_matches_filters(task, {"status": TaskStatus.PENDING})
        assert not task_manager._task_matches_filters(task, {"status": TaskStatus.COMPLETED})
    
    def test_duration_parsing(self, task_manager):
        """時間パースのテスト"""
        # 時間の解析
        duration = task_manager._parse_duration("2時間30分")
        assert duration == timedelta(hours=2, minutes=30)
        
        duration = task_manager._parse_duration("1時間")
        assert duration == timedelta(hours=1)
        
        duration = task_manager._parse_duration("45分")
        assert duration == timedelta(minutes=45)
        
        duration = task_manager._parse_duration("不明")
        assert duration is None
    
    def test_due_date_parsing(self, task_manager):
        """期日パースのテスト"""
        # 日付形式
        due_date = task_manager._parse_due_date("2024-01-15")
        assert due_date.year == 2024
        assert due_date.month == 1
        assert due_date.day == 15
        
        # 相対日付
        due_date = task_manager._parse_due_date("今日")
        assert due_date.date() == datetime.now().date()
        
        due_date = task_manager._parse_due_date("明日")
        expected = datetime.now() + timedelta(days=1)
        assert due_date.date() == expected.date()
        
        due_date = task_manager._parse_due_date("不明")
        assert due_date is None
    
    @pytest.mark.asyncio
    async def test_get_analytics(self, task_manager):
        """分析機能のテスト"""
        # テストタスクを追加
        await task_manager.create_task("タスク1", priority=TaskPriority.HIGH)
        await task_manager.create_task("タスク2", priority=TaskPriority.MEDIUM)
        task3 = await task_manager.create_task("タスク3", priority=TaskPriority.LOW)
        
        # 1つ完了
        await task_manager.complete_task(task3.id)
        
        analytics = await task_manager.get_task_analytics()
        
        assert analytics["total_tasks"] == 3
        assert analytics["completed_tasks"] == 1
        assert analytics["pending_tasks"] == 2
        assert analytics["completion_rate"] == pytest.approx(33.33, rel=1e-2)

if __name__ == "__main__":
    pytest.main([__file__])