# -*- coding: utf-8 -*-
"""
Personal AI Agent - Task Management Module
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import re

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class TaskPriority(Enum):
    """Task priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class Task:
    """Task data class"""
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
    dependencies: List[str]  # Dependent task IDs
    subtasks: List[str]      # Subtask IDs
    metadata: Dict[str, Any]

class TaskManager:
    """
    Task Management System
    
    Provides natural language task creation and management
    with intelligent task suggestion features
    """
    
    def __init__(self, memory_system, llm_provider):
        self.memory_system = memory_system
        self.llm_provider = llm_provider
        
        # Task storage (use database in actual implementation)
        self.tasks: Dict[str, Task] = {}
        
        # Task analysis patterns
        self.priority_keywords = {
            TaskPriority.URGENT: ["urgent", "asap", "immediately", "critical"],
            TaskPriority.HIGH: ["important", "priority", "high", "soon"],
            TaskPriority.MEDIUM: ["normal", "medium", "standard"],
            TaskPriority.LOW: ["later", "low", "when_possible", "someday"]
        }
        
        logger.info("TaskManager initialized")
    
    async def process_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process task-related requests from user"""
        
        # Intent analysis
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
        """Analyze task-related intent"""
        
        user_input_lower = user_input.lower()
        
        # Action determination
        if any(word in user_input_lower for word in ["create", "add", "new", "register", "todo"]):
            action = "create"
        elif any(word in user_input_lower for word in ["list", "show", "display", "view"]):
            action = "list"
        elif any(word in user_input_lower for word in ["update", "change", "modify", "edit"]):
            action = "update"
        elif any(word in user_input_lower for word in ["complete", "finish", "done"]):
            action = "complete"
        elif any(word in user_input_lower for word in ["delete", "remove", "cancel"]):
            action = "delete"
        else:
            action = "general"
        
        # Filter extraction
        filters = {}
        
        # Priority filter
        for priority, keywords in self.priority_keywords.items():
            if any(keyword in user_input_lower for keyword in keywords):
                filters["priority"] = priority
                break
        
        # Status filter
        if "in progress" in user_input_lower or "working" in user_input_lower:
            filters["status"] = TaskStatus.IN_PROGRESS
        elif "completed" in user_input_lower:
            filters["status"] = TaskStatus.COMPLETED
        elif "pending" in user_input_lower or "remaining" in user_input_lower:
            filters["status"] = [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
        
        # Due date filter
        if "today" in user_input_lower:
            filters["due_date"] = "today"
        elif "tomorrow" in user_input_lower:
            filters["due_date"] = "tomorrow"
        elif "this week" in user_input_lower:
            filters["due_date"] = "this_week"
        
        return {
            "action": action,
            "filters": filters,
            "confidence": 0.8
        }
    
    async def _create_task_from_input(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create task from user input"""
        
        # Extract task information using LLM
        extraction_prompt = f"""
        Extract task information from the following user input:
        
        Input: {user_input}
        
        Return JSON in the following format:
        {{
            "title": "Task title",
            "description": "Detailed description (if any)",
            "priority": "low/medium/high/urgent",
            "due_date": "YYYY-MM-DD (if explicit date given)",
            "tags": ["tag1", "tag2"],
            "estimated_duration": "duration (e.g., 2 hours, 30 minutes)"
        }}
        """
        
        try:
            llm_response = await self.llm_provider.generate_response(extraction_prompt, context)
            import json
            task_info = json.loads(llm_response["content"])
            
            # Create task
            task = await self.create_task(
                title=task_info.get("title", "New Task"),
                description=task_info.get("description"),
                priority=TaskPriority(task_info.get("priority", "medium")),
                due_date=self._parse_due_date(task_info.get("due_date")),
                tags=task_info.get("tags", []),
                estimated_duration=self._parse_duration(task_info.get("estimated_duration"))
            )
            
            return {
                "message": f"Created task: {task.title}",
                "task_id": task.id,
                "actions": ["task_created"],
                "suggestions": [
                    "Would you like to add more details?",
                    "Set dependencies or deadline?"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to create task from input: {e}")
            return {
                "message": "Failed to create task. Please try again.",
                "error": str(e),
                "actions": [],
                "suggestions": ["Please provide specific task details"]
            }
    
    async def create_task(self, 
                         title: str,
                         description: Optional[str] = None,
                         priority: TaskPriority = TaskPriority.MEDIUM,
                         due_date: Optional[datetime] = None,
                         tags: Optional[List[str]] = None,
                         estimated_duration: Optional[timedelta] = None) -> Task:
        """Create a new task"""
        
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
        
        # Store in memory system
        await self.memory_system.store_knowledge(
            knowledge=f"Task created: {title}",
            source="task_manager",
            tags=["task", "created"] + (tags or []),
            metadata={"task_id": task_id, "priority": priority.value}
        )
        
        logger.info(f"Task created: {task_id} - {title}")
        return task
    
    async def _list_tasks(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get task list"""
        
        filtered_tasks = []
        
        for task in self.tasks.values():
            # Apply filters
            if not self._task_matches_filters(task, filters):
                continue
            filtered_tasks.append(task)
        
        # Sort by priority and due date
        filtered_tasks.sort(key=lambda t: (
            t.priority.value,
            t.due_date or datetime.max,
            t.created_at
        ))
        
        # Format results
        if not filtered_tasks:
            message = "No matching tasks found."
        else:
            task_list = []
            for task in filtered_tasks[:10]:  # Max 10 items
                due_str = task.due_date.strftime("%m/%d") if task.due_date else "No deadline"
                status_emoji = self._get_status_emoji(task.status)
                priority_emoji = self._get_priority_emoji(task.priority)
                
                task_list.append(f"{status_emoji} {priority_emoji} {task.title} (Due: {due_str})")
            
            message = f"Task List ({len(filtered_tasks)} items):\n" + "\n".join(task_list)
        
        return {
            "message": message,
            "task_count": len(filtered_tasks),
            "actions": ["tasks_listed"],
            "suggestions": [
                "Check specific task details?",
                "Add a new task?"
            ]
        }
    
    async def complete_task(self, task_id: str) -> bool:
        """Complete a task"""
        
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.updated_at = datetime.now()
        
        # Calculate actual duration
        if task.status == TaskStatus.IN_PROGRESS:
            # Since start time is not recorded, use estimate
            task.actual_duration = datetime.now() - task.updated_at
        
        logger.info(f"Task completed: {task_id} - {task.title}")
        return True
    
    async def _update_task_from_input(self, user_input: str, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Update task from user input"""
        
        # Identify task
        task = await self._identify_task_from_input(user_input)
        if not task:
            return {
                "message": "Could not identify task to update. Please specify task name clearly.",
                "actions": [],
                "suggestions": ["Check existing task list?"]
            }
        
        # Extract update content
        updates = await self._extract_task_updates(user_input)
        
        # Update task
        original_title = task.title
        updated_fields = []
        
        if "title" in updates:
            task.title = updates["title"]
            updated_fields.append("title")
        
        if "description" in updates:
            task.description = updates["description"]
            updated_fields.append("description")
        
        if "priority" in updates:
            task.priority = TaskPriority(updates["priority"])
            updated_fields.append("priority")
        
        if "due_date" in updates:
            task.due_date = self._parse_due_date(updates["due_date"])
            updated_fields.append("due_date")
        
        if "status" in updates:
            task.status = TaskStatus(updates["status"])
            updated_fields.append("status")
        
        task.updated_at = datetime.now()
        
        return {
            "message": f"Updated task '{original_title}': {', '.join(updated_fields)}",
            "task_id": task.id,
            "actions": ["task_updated"],
            "suggestions": ["Any other updates needed?"]
        }
    
    async def _complete_task_from_input(self, user_input: str, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Process task completion"""
        
        task = await self._identify_task_from_input(user_input)
        if not task:
            return {
                "message": "Could not identify task to complete.",
                "actions": [],
                "suggestions": ["Tell me which task to complete"]
            }
        
        # Complete task
        await self.complete_task(task.id)
        
        return {
            "message": f"Completed task: {task.title}! Great job!",
            "task_id": task.id,
            "actions": ["task_completed"],
            "suggestions": [
                "Any other completed tasks?",
                "Add a new task?"
            ]
        }
    
    async def _general_task_assistance(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """General task assistance"""
        
        # Generate task analysis and advice
        analysis_prompt = f"""
        Task-related question from user: {user_input}
        
        Considering current task situation, generate useful advice or suggestions.
        """
        
        try:
            llm_response = await self.llm_provider.generate_response(analysis_prompt, context)
            
            return {
                "message": llm_response["content"],
                "actions": ["general_assistance"],
                "suggestions": [
                    "Need help with specific task creation or management?",
                    "Check today's tasks?"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to provide general task assistance: {e}")
            return {
                "message": "How can I help you with tasks?",
                "actions": [],
                "suggestions": [
                    "Create a new task",
                    "Check existing tasks",
                    "Get task management advice"
                ]
            }
    
    async def _identify_task_from_input(self, user_input: str) -> Optional[Task]:
        """Identify task from user input"""
        
        # Partial matching with task titles
        for task in self.tasks.values():
            if task.title.lower() in user_input.lower() or user_input.lower() in task.title.lower():
                return task
        
        return None
    
    async def _extract_task_updates(self, user_input: str) -> Dict[str, Any]:
        """Extract update content"""
        
        updates = {}
        user_input_lower = user_input.lower()
        
        # Priority updates
        for priority, keywords in self.priority_keywords.items():
            if any(keyword in user_input_lower for keyword in keywords):
                updates["priority"] = priority.value
                break
        
        # Status updates
        if "start" in user_input_lower or "begin" in user_input_lower:
            updates["status"] = TaskStatus.IN_PROGRESS.value
        elif "complete" in user_input_lower:
            updates["status"] = TaskStatus.COMPLETED.value
        elif "pause" in user_input_lower or "hold" in user_input_lower:
            updates["status"] = TaskStatus.PAUSED.value
        
        return updates
    
    def _task_matches_filters(self, task: Task, filters: Dict[str, Any]) -> bool:
        """Check if task matches filter conditions"""
        
        # Priority filter
        if "priority" in filters and task.priority != filters["priority"]:
            return False
        
        # Status filter
        if "status" in filters:
            if isinstance(filters["status"], list):
                if task.status not in filters["status"]:
                    return False
            elif task.status != filters["status"]:
                return False
        
        # Due date filter
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
        """Parse due date string"""
        
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            # Handle relative dates
            today = datetime.now()
            if "today" in date_str:
                return today
            elif "tomorrow" in date_str:
                return today + timedelta(days=1)
            elif "next week" in date_str:
                return today + timedelta(days=7)
            else:
                return None
    
    def _parse_duration(self, duration_str: Optional[str]) -> Optional[timedelta]:
        """Parse duration string"""
        
        if not duration_str:
            return None
        
        # Pattern matching for duration
        import re
        hour_match = re.search(r'(\d+)\s*hour', duration_str)
        minute_match = re.search(r'(\d+)\s*minute', duration_str)
        
        hours = int(hour_match.group(1)) if hour_match else 0
        minutes = int(minute_match.group(1)) if minute_match else 0
        
        if hours > 0 or minutes > 0:
            return timedelta(hours=hours, minutes=minutes)
        
        return None
    
    def _get_status_emoji(self, status: TaskStatus) -> str:
        """Get status emoji"""
        emoji_map = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.IN_PROGRESS: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.CANCELLED: "❌",
            TaskStatus.PAUSED: "⏸️"
        }
        return emoji_map.get(status, "📝")
    
    def _get_priority_emoji(self, priority: TaskPriority) -> str:
        """Get priority emoji"""
        emoji_map = {
            TaskPriority.LOW: "🟢",
            TaskPriority.MEDIUM: "🟡",
            TaskPriority.HIGH: "🟠",
            TaskPriority.URGENT: "🔴"
        }
        return emoji_map.get(priority, "⚪")
    
    async def get_task_analytics(self) -> Dict[str, Any]:
        """Get task analytics information"""
        
        total_tasks = len(self.tasks)
        completed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED])
        pending_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING])
        in_progress_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS])
        
        # Priority statistics
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