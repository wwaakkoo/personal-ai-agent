"""
Personal AI Agent - タスク管理モジュール
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import re

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """タスクステータス"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class TaskPriority(Enum):
    """タスク優先度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class Task:
    """タスクデータクラス"""
    id: str
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    tags: List[str]
    estimated_duration: Optional[timedelta]
    actual_duration: Optional[timedelta]
    dependencies: List[str]  # 依存タスクのID
    subtasks: List[str]      # サブタスクのID
    metadata: Dict[str, Any]

class TaskManager:
    """
    タスク管理システム
    
    自然言語でのタスク作成・管理と
    インテリジェントなタスク提案機能を提供
    """
    
    def __init__(self, memory_system, llm_provider):
        self.memory_system = memory_system
        self.llm_provider = llm_provider
        
        # タスクストレージ（実際の実装ではデータベースを使用）
        self.tasks: Dict[str, Task] = {}
        
        # タスク分析パターン
        self.priority_keywords = {
            TaskPriority.URGENT: ["緊急", "至急", "すぐに", "今日中", "ASAP"],
            TaskPriority.HIGH: ["重要", "優先", "早めに", "高", "重"],
            TaskPriority.MEDIUM: ["普通", "通常", "中", "標準"],
            TaskPriority.LOW: ["後で", "余裕", "低", "いつでも"]
        }
        
        logger.info("TaskManager initialized")
    
    async def process_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """ユーザーからのタスク関連リクエストを処理"""
        
        # 意図分析
        intent = await self._analyze_task_intent(user_input)
        
        if intent["action"] == "create":
            return await self._create_task_from_input(user_input, context)
        elif intent["action"] == "list":
            return await self._list_tasks(intent.get("filters", {}))
        elif intent["action"] == "update":
            return await self._update_task_from_input(user_input, intent)
        elif intent["action"] == "complete":
            return await self._complete_task_from_input(user_input, intent)
        elif intent["action"] == "delete":
            return await self._delete_task_from_input(user_input, intent)
        else:
            return await self._general_task_assistance(user_input, context)
    
    async def _analyze_task_intent(self, user_input: str) -> Dict[str, Any]:
        """タスク関連の意図を分析"""
        
        user_input_lower = user_input.lower()
        
        # アクション判定
        if any(word in user_input_lower for word in ["作成", "追加", "新しい", "登録", "やること"]):
            action = "create"
        elif any(word in user_input_lower for word in ["一覧", "リスト", "表示", "見せて", "確認"]):
            action = "list"
        elif any(word in user_input_lower for word in ["更新", "変更", "修正", "編集"]):
            action = "update"
        elif any(word in user_input_lower for word in ["完了", "終了", "済み", "done"]):
            action = "complete"
        elif any(word in user_input_lower for word in ["削除", "消去", "キャンセル"]):
            action = "delete"
        else:
            action = "general"
        
        # フィルター抽出
        filters = {}
        
        # 優先度フィルター
        for priority, keywords in self.priority_keywords.items():
            if any(keyword in user_input_lower for keyword in keywords):
                filters["priority"] = priority
                break
        
        # ステータスフィルター
        if "進行中" in user_input_lower or "作業中" in user_input_lower:
            filters["status"] = TaskStatus.IN_PROGRESS
        elif "完了" in user_input_lower:
            filters["status"] = TaskStatus.COMPLETED
        elif "未完了" in user_input_lower or "残り" in user_input_lower:
            filters["status"] = [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
        
        # 期日フィルター
        if "今日" in user_input_lower:
            filters["due_date"] = "today"
        elif "明日" in user_input_lower:
            filters["due_date"] = "tomorrow"
        elif "今週" in user_input_lower:
            filters["due_date"] = "this_week"
        
        return {
            "action": action,
            "filters": filters,
            "confidence": 0.8
        }
    
    async def _create_task_from_input(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """ユーザー入力からタスクを作成"""
        
        # LLMを使用してタスク情報を抽出
        extraction_prompt = f"""
        以下のユーザー入力からタスク情報を抽出してください：
        
        入力: {user_input}
        
        以下の形式でJSONを返してください：
        {{
            "title": "タスクのタイトル",
            "description": "詳細説明（あれば）",
            "priority": "low/medium/high/urgent",
            "due_date": "YYYY-MM-DD（明示的な期日があれば）",
            "tags": ["タグ1", "タグ2"],
            "estimated_duration": "時間（例：2時間、30分）"
        }}
        """
        
        try:
            llm_response = await self.llm_provider.generate_response(extraction_prompt, context)
            import json
            task_info = json.loads(llm_response["content"])
            
            # タスク作成
            task = await self.create_task(
                title=task_info.get("title", "新しいタスク"),
                description=task_info.get("description"),
                priority=TaskPriority(task_info.get("priority", "medium")),
                due_date=self._parse_due_date(task_info.get("due_date")),
                tags=task_info.get("tags", []),
                estimated_duration=self._parse_duration(task_info.get("estimated_duration"))
            )
            
            return {
                "message": f"タスク「{task.title}」を作成しました。",
                "task_id": task.id,
                "actions": ["task_created"],
                "suggestions": [
                    "タスクの詳細を追加しますか？",
                    "依存関係や締切を設定しますか？"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to create task from input: {e}")
            return {
                "message": "タスクの作成に失敗しました。もう一度お試しください。",
                "error": str(e),
                "actions": [],
                "suggestions": ["具体的なタスク内容を教えてください"]
            }
    
    async def create_task(self, 
                         title: str,
                         description: Optional[str] = None,
                         priority: TaskPriority = TaskPriority.MEDIUM,
                         due_date: Optional[datetime] = None,
                         tags: Optional[List[str]] = None,
                         estimated_duration: Optional[timedelta] = None) -> Task:
        """新しいタスクを作成"""
        
        import uuid
        task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            priority=priority,
            due_date=due_date,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            completed_at=None,
            tags=tags or [],
            estimated_duration=estimated_duration,
            actual_duration=None,
            dependencies=[],
            subtasks=[],
            metadata={}
        )
        
        self.tasks[task_id] = task
        
        # 記憶システムに保存
        await self.memory_system.store_knowledge(
            knowledge=f"タスク作成: {title}",
            source="task_manager",
            tags=["task", "created"] + (tags or []),
            metadata={"task_id": task_id, "priority": priority.value}
        )
        
        logger.info(f"Task created: {task_id} - {title}")
        return task
    
    async def _list_tasks(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """タスク一覧を取得"""
        
        filtered_tasks = []
        
        for task in self.tasks.values():
            # フィルター適用
            if not self._task_matches_filters(task, filters):
                continue
            filtered_tasks.append(task)
        
        # ソート（優先度、期日順）
        filtered_tasks.sort(key=lambda t: (
            t.priority.value,
            t.due_date or datetime.max,
            t.created_at
        ))
        
        # 結果フォーマット
        if not filtered_tasks:
            message = "該当するタスクがありません。"
        else:
            task_list = []
            for task in filtered_tasks[:10]:  # 最大10件
                due_str = task.due_date.strftime("%m/%d") if task.due_date else "期限なし"
                status_emoji = self._get_status_emoji(task.status)
                priority_emoji = self._get_priority_emoji(task.priority)
                
                task_list.append(f"{status_emoji} {priority_emoji} {task.title} (期限: {due_str})")
            
            message = f"タスク一覧 ({len(filtered_tasks)}件):\n" + "\n".join(task_list)
        
        return {
            "message": message,
            "task_count": len(filtered_tasks),
            "actions": ["tasks_listed"],
            "suggestions": [
                "特定のタスクの詳細を確認しますか？",
                "新しいタスクを追加しますか？"
            ]
        }
    
    async def _update_task_from_input(self, user_input: str, intent: Dict[str, Any]) -> Dict[str, Any]:
        """ユーザー入力からタスクを更新"""
        
        # タスク特定
        task = await self._identify_task_from_input(user_input)
        if not task:
            return {
                "message": "更新するタスクを特定できませんでした。タスク名を明確に指定してください。",
                "actions": [],
                "suggestions": ["既存のタスク一覧を確認しますか？"]
            }
        
        # 更新内容を抽出
        updates = await self._extract_task_updates(user_input)
        
        # タスク更新
        original_title = task.title
        updated_fields = []
        
        if "title" in updates:
            task.title = updates["title"]
            updated_fields.append("タイトル")
        
        if "description" in updates:
            task.description = updates["description"]
            updated_fields.append("説明")
        
        if "priority" in updates:
            task.priority = TaskPriority(updates["priority"])
            updated_fields.append("優先度")
        
        if "due_date" in updates:
            task.due_date = self._parse_due_date(updates["due_date"])
            updated_fields.append("期限")
        
        if "status" in updates:
            task.status = TaskStatus(updates["status"])
            updated_fields.append("ステータス")
        
        task.updated_at = datetime.now()
        
        return {
            "message": f"タスク「{original_title}」の{', '.join(updated_fields)}を更新しました。",
            "task_id": task.id,
            "actions": ["task_updated"],
            "suggestions": ["他にも更新したい項目はありますか？"]
        }
    
    async def _complete_task_from_input(self, user_input: str, intent: Dict[str, Any]) -> Dict[str, Any]:
        """タスク完了処理"""
        
        task = await self._identify_task_from_input(user_input)
        if not task:
            return {
                "message": "完了するタスクを特定できませんでした。",
                "actions": [],
                "suggestions": ["完了したいタスク名を教えてください"]
            }
        
        # タスク完了
        await self.complete_task(task.id)
        
        return {
            "message": f"タスク「{task.title}」を完了しました！お疲れ様でした。",
            "task_id": task.id,
            "actions": ["task_completed"],
            "suggestions": [
                "他にも完了したタスクはありますか？",
                "新しいタスクを追加しますか？"
            ]
        }
    
    async def complete_task(self, task_id: str) -> bool:
        """タスクを完了"""
        
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.updated_at = datetime.now()
        
        # 実際の所要時間を計算
        if task.status == TaskStatus.IN_PROGRESS:
            # 進行開始時刻は記録されていないため、概算
            task.actual_duration = datetime.now() - task.updated_at
        
        logger.info(f"Task completed: {task_id} - {task.title}")
        return True
    
    async def _general_task_assistance(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """一般的なタスク支援"""
        
        # タスク分析とアドバイス生成
        analysis_prompt = f"""
        ユーザーからのタスク関連の質問: {user_input}
        
        現在のタスク状況を考慮して、有用なアドバイスや提案を生成してください。
        """
        
        try:
            llm_response = await self.llm_provider.generate_response(analysis_prompt, context)
            
            return {
                "message": llm_response["content"],
                "actions": ["general_assistance"],
                "suggestions": [
                    "具体的なタスクの作成や管理はいかがですか？",
                    "今日のタスクを確認しましょうか？"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to provide general task assistance: {e}")
            return {
                "message": "申し訳ありません。タスクに関して何かお手伝いできることがあれば教えてください。",
                "actions": [],
                "suggestions": [
                    "新しいタスクを作成する",
                    "既存のタスクを確認する",
                    "タスクの管理方法について相談する"
                ]
            }
    
    async def _identify_task_from_input(self, user_input: str) -> Optional[Task]:
        """ユーザー入力からタスクを特定"""
        
        # タスクタイトルとの部分マッチング
        for task in self.tasks.values():
            if task.title.lower() in user_input.lower() or user_input.lower() in task.title.lower():
                return task
        
        return None
    
    async def _extract_task_updates(self, user_input: str) -> Dict[str, Any]:
        """更新内容を抽出"""
        
        updates = {}
        user_input_lower = user_input.lower()
        
        # 優先度の更新
        for priority, keywords in self.priority_keywords.items():
            if any(keyword in user_input_lower for keyword in keywords):
                updates["priority"] = priority.value
                break
        
        # ステータスの更新
        if "開始" in user_input_lower or "着手" in user_input_lower:
            updates["status"] = TaskStatus.IN_PROGRESS.value
        elif "完了" in user_input_lower:
            updates["status"] = TaskStatus.COMPLETED.value
        elif "一時停止" in user_input_lower or "保留" in user_input_lower:
            updates["status"] = TaskStatus.PAUSED.value
        
        return updates
    
    def _task_matches_filters(self, task: Task, filters: Dict[str, Any]) -> bool:
        """タスクがフィルター条件にマッチするかチェック"""
        
        # 優先度フィルター
        if "priority" in filters and task.priority != filters["priority"]:
            return False
        
        # ステータスフィルター
        if "status" in filters:
            if isinstance(filters["status"], list):
                if task.status not in filters["status"]:
                    return False
            elif task.status != filters["status"]:
                return False
        
        # 期日フィルター
        if "due_date" in filters:
            today = datetime.now().date()
            if filters["due_date"] == "today":
                if not task.due_date or task.due_date.date() != today:
                    return False
            elif filters["due_date"] == "tomorrow":
                tomorrow = today + timedelta(days=1)
                if not task.due_date or task.due_date.date() != tomorrow:
                    return False
            elif filters["due_date"] == "this_week":
                week_end = today + timedelta(days=7)
                if not task.due_date or task.due_date.date() > week_end:
                    return False
        
        return True
    
    def _parse_due_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """期日文字列をパース"""
        
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            # 相対的な期日の処理
            today = datetime.now()
            if "今日" in date_str:
                return today
            elif "明日" in date_str:
                return today + timedelta(days=1)
            elif "来週" in date_str:
                return today + timedelta(days=7)
            else:
                return None
    
    def _parse_duration(self, duration_str: Optional[str]) -> Optional[timedelta]:
        """時間文字列をパース"""
        
        if not duration_str:
            return None
        
        # 時間のパターンマッチング
        import re
        hour_match = re.search(r'(\d+)時間', duration_str)
        minute_match = re.search(r'(\d+)分', duration_str)
        
        hours = int(hour_match.group(1)) if hour_match else 0
        minutes = int(minute_match.group(1)) if minute_match else 0
        
        if hours > 0 or minutes > 0:
            return timedelta(hours=hours, minutes=minutes)
        
        return None
    
    def _get_status_emoji(self, status: TaskStatus) -> str:
        """ステータス絵文字"""
        emoji_map = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.IN_PROGRESS: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.CANCELLED: "❌",
            TaskStatus.PAUSED: "⏸️"
        }
        return emoji_map.get(status, "📝")
    
    def _get_priority_emoji(self, priority: TaskPriority) -> str:
        """優先度絵文字"""
        emoji_map = {
            TaskPriority.LOW: "🟢",
            TaskPriority.MEDIUM: "🟡",
            TaskPriority.HIGH: "🟠",
            TaskPriority.URGENT: "🔴"
        }
        return emoji_map.get(priority, "⚪")
    
    async def get_task_analytics(self) -> Dict[str, Any]:
        """タスク分析情報を取得"""
        
        total_tasks = len(self.tasks)
        completed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED])
        pending_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING])
        in_progress_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS])
        
        # 優先度別統計
        priority_stats = {}
        for priority in TaskPriority:
            priority_stats[priority.value] = len([
                t for t in self.tasks.values() if t.priority == priority
            ])
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "in_progress_tasks": in_progress_tasks,
            "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "priority_distribution": priority_stats
        }