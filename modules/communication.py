"""
Personal AI Agent - コミュニケーション支援モジュール
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class CommunicationType(Enum):
    """コミュニケーションタイプ"""
    EMAIL = "email"
    CHAT = "chat"
    MEMO = "memo"
    REPORT = "report"
    PROPOSAL = "proposal"

class ToneStyle(Enum):
    """文体・トーン"""
    FORMAL = "formal"
    CASUAL = "casual"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    CONCISE = "concise"

@dataclass
class CommunicationTemplate:
    """コミュニケーションテンプレート"""
    template_id: str
    name: str
    type: CommunicationType
    tone: ToneStyle
    template: str
    placeholders: List[str]
    usage_count: int

class CommunicationModule:
    """
    コミュニケーション支援システム
    
    メール・チャット・文書の草案作成と
    コミュニケーション最適化機能を提供
    """
    
    def __init__(self, llm_provider):
        self.llm_provider = llm_provider
        
        # テンプレート管理
        self.templates: Dict[str, CommunicationTemplate] = {}
        self._initialize_templates()
        
        # 学習したパターン
        self.communication_patterns: Dict[str, Any] = {}
        
        logger.info("CommunicationModule initialized")
    
    def _initialize_templates(self) -> None:
        """デフォルトテンプレートの初期化"""
        
        templates = [
            {
                "template_id": "email_formal_request",
                "name": "正式な依頼メール",
                "type": CommunicationType.EMAIL,
                "tone": ToneStyle.FORMAL,
                "template": """件名: {subject}

{recipient_name}様

いつもお世話になっております。
{sender_name}です。

{main_content}

ご多忙の中恐縮ですが、{deadline}までにご回答をいただけますと幸いです。

何かご不明な点がございましたら、お気軽にお申し付けください。

よろしくお願いいたします。

{sender_name}""",
                "placeholders": ["subject", "recipient_name", "sender_name", "main_content", "deadline"]
            },
            {
                "template_id": "email_thank_you",
                "name": "お礼メール",
                "type": CommunicationType.EMAIL,
                "tone": ToneStyle.PROFESSIONAL,
                "template": """件名: {subject}

{recipient_name}様

{sender_name}です。

{occasion}の件では、大変お世話になりました。
{specific_thanks}

今後ともどうぞよろしくお願いいたします。

{sender_name}""",
                "placeholders": ["subject", "recipient_name", "sender_name", "occasion", "specific_thanks"]
            },
            {
                "template_id": "chat_status_update",
                "name": "進捗報告チャット",
                "type": CommunicationType.CHAT,
                "tone": ToneStyle.CASUAL,
                "template": """{project_name}の進捗です！

✅ 完了: {completed_items}
🔄 進行中: {in_progress_items}
📋 予定: {planned_items}

{additional_notes}

何か質問があればお気軽に！""",
                "placeholders": ["project_name", "completed_items", "in_progress_items", "planned_items", "additional_notes"]
            }
        ]
        
        for template_data in templates:
            template = CommunicationTemplate(
                template_id=template_data["template_id"],
                name=template_data["name"],
                type=template_data["type"],
                tone=template_data["tone"],
                template=template_data["template"],
                placeholders=template_data["placeholders"],
                usage_count=0
            )
            self.templates[template.template_id] = template
    
    async def generate_draft(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """コミュニケーション草案の生成"""
        
        # 意図とタイプを分析
        comm_analysis = await self._analyze_communication_intent(user_input)
        
        if comm_analysis["use_template"]:
            # テンプレートベース生成
            return await self._generate_from_template(user_input, comm_analysis, context)
        else:
            # LLMベース生成
            return await self._generate_with_llm(user_input, comm_analysis, context)
    
    async def _analyze_communication_intent(self, user_input: str) -> Dict[str, Any]:
        """コミュニケーション意図の分析"""
        
        user_input_lower = user_input.lower()
        
        # コミュニケーションタイプの判定
        if any(word in user_input_lower for word in ["メール", "email", "連絡", "送信"]):
            comm_type = CommunicationType.EMAIL
        elif any(word in user_input_lower for word in ["チャット", "chat", "メッセージ", "slack"]):
            comm_type = CommunicationType.CHAT
        elif any(word in user_input_lower for word in ["メモ", "memo", "記録", "控え"]):
            comm_type = CommunicationType.MEMO
        elif any(word in user_input_lower for word in ["報告", "レポート", "report"]):
            comm_type = CommunicationType.REPORT
        elif any(word in user_input_lower for word in ["提案", "proposal", "企画"]):
            comm_type = CommunicationType.PROPOSAL
        else:
            comm_type = CommunicationType.EMAIL  # デフォルト
        
        # トーンの判定
        if any(word in user_input_lower for word in ["正式", "formal", "丁寧", "フォーマル"]):
            tone = ToneStyle.FORMAL
        elif any(word in user_input_lower for word in ["カジュアル", "casual", "気軽", "フランク"]):
            tone = ToneStyle.CASUAL
        elif any(word in user_input_lower for word in ["フレンドリー", "friendly", "親しみ"]):
            tone = ToneStyle.FRIENDLY
        elif any(word in user_input_lower for word in ["簡潔", "concise", "短く", "要点"]):
            tone = ToneStyle.CONCISE
        else:
            tone = ToneStyle.PROFESSIONAL  # デフォルト
        
        # テンプレート使用判定
        use_template = any(word in user_input_lower for word in [
            "テンプレート", "定型", "フォーマット", "雛形"
        ])
        
        return {
            "type": comm_type,
            "tone": tone,
            "use_template": use_template,
            "confidence": 0.8
        }
    
    async def _generate_from_template(self, 
                                    user_input: str, 
                                    comm_analysis: Dict[str, Any], 
                                    context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """テンプレートからの草案生成"""
        
        # 適切なテンプレートを選択
        suitable_templates = [
            template for template in self.templates.values()
            if template.type == comm_analysis["type"] and template.tone == comm_analysis["tone"]
        ]
        
        if not suitable_templates:
            # 該当するテンプレートがない場合はLLM生成にフォールバック
            return await self._generate_with_llm(user_input, comm_analysis, context)
        
        # 使用頻度順でソート
        selected_template = sorted(suitable_templates, key=lambda t: t.usage_count, reverse=True)[0]
        
        # プレースホルダーの値を抽出
        placeholder_values = await self._extract_placeholder_values(user_input, selected_template, context)
        
        # テンプレート適用
        try:
            generated_content = selected_template.template.format(**placeholder_values)
            selected_template.usage_count += 1
            
            return {
                "content": generated_content,
                "type": comm_analysis["type"].value,
                "tone": comm_analysis["tone"].value,
                "template_used": selected_template.template_id,
                "confidence": 0.9,
                "suggestions": [
                    "内容を調整しますか？",
                    "トーンを変更しますか？",
                    "他のテンプレートを試しますか？"
                ]
            }
            
        except KeyError as e:
            logger.warning(f"Template placeholder missing: {e}")
            return await self._generate_with_llm(user_input, comm_analysis, context)
    
    async def _generate_with_llm(self, 
                               user_input: str, 
                               comm_analysis: Dict[str, Any], 
                               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """LLMを使用した草案生成"""
        
        # プロンプト構築
        generation_prompt = self._build_generation_prompt(user_input, comm_analysis, context)
        
        try:
            llm_response = await self.llm_provider.generate_response(generation_prompt, context)
            
            return {
                "content": llm_response["content"],
                "type": comm_analysis["type"].value,
                "tone": comm_analysis["tone"].value,
                "template_used": None,
                "confidence": llm_response.get("confidence", 0.7),
                "suggestions": [
                    "内容を修正しますか？",
                    "長さを調整しますか？",
                    "トーンを変更しますか？"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to generate communication with LLM: {e}")
            return {
                "content": "申し訳ありません。草案の生成に失敗しました。",
                "type": comm_analysis["type"].value,
                "error": str(e),
                "suggestions": ["もう一度お試しください"]
            }
    
    def _build_generation_prompt(self, 
                               user_input: str, 
                               comm_analysis: Dict[str, Any], 
                               context: Optional[Dict[str, Any]] = None) -> str:
        """生成用プロンプトの構築"""
        
        type_descriptions = {
            CommunicationType.EMAIL: "ビジネスメール",
            CommunicationType.CHAT: "チャットメッセージ",
            CommunicationType.MEMO: "メモ・記録",
            CommunicationType.REPORT: "報告書",
            CommunicationType.PROPOSAL: "提案書"
        }
        
        tone_descriptions = {
            ToneStyle.FORMAL: "正式で丁寧な",
            ToneStyle.CASUAL: "カジュアルで親しみやすい",
            ToneStyle.FRIENDLY: "フレンドリーで温かい",
            ToneStyle.PROFESSIONAL: "プロフェッショナルな",
            ToneStyle.CONCISE: "簡潔で要点を押さえた"
        }
        
        prompt = f"""
        以下の要件に基づいて{type_descriptions[comm_analysis['type']]}を作成してください：
        
        要求内容: {user_input}
        
        スタイル: {tone_descriptions[comm_analysis['tone']]}文体
        
        以下の点に注意してください：
        - 相手への配慮を忘れない
        - 目的を明確にする
        - 適切な敬語を使用する
        - 読みやすい構成にする
        """
        
        # コンテキスト情報の追加
        if context:
            if context.get("user_state", {}).get("current_focus"):
                prompt += f"\n現在の関心事: {context['user_state']['current_focus']}"
            
            if context.get("environment", {}).get("time_of_day"):
                prompt += f"\n時間帯: {context['environment']['time_of_day']}"
        
        return prompt
    
    async def _extract_placeholder_values(self, 
                                        user_input: str, 
                                        template: CommunicationTemplate,
                                        context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """テンプレートのプレースホルダー値を抽出"""
        
        # LLMを使用して構造化データを抽出
        extraction_prompt = f"""
        以下のユーザー入力から、テンプレートに必要な情報を抽出してください：
        
        入力: {user_input}
        
        必要な項目: {', '.join(template.placeholders)}
        
        JSON形式で返してください。情報が不足している場合は適切なデフォルト値を使用してください。
        """
        
        try:
            llm_response = await self.llm_provider.generate_response(extraction_prompt, context)
            import json
            extracted_data = json.loads(llm_response["content"])
            
            # デフォルト値の設定
            defaults = {
                "sender_name": "送信者",
                "recipient_name": "受信者",
                "subject": "件名",
                "deadline": "適宜",
                "main_content": "内容を記載してください",
                "project_name": "プロジェクト",
                "completed_items": "完了項目",
                "in_progress_items": "進行中項目",
                "planned_items": "予定項目",
                "additional_notes": "追加事項なし"
            }
            
            # デフォルト値でマージ
            result = defaults.copy()
            result.update(extracted_data)
            
            # 必要なプレースホルダーのみ返す
            return {key: result.get(key, f"[{key}]") for key in template.placeholders}
            
        except Exception as e:
            logger.error(f"Failed to extract placeholder values: {e}")
            # フォールバック: デフォルト値を返す
            return {key: f"[{key}]" for key in template.placeholders}
    
    async def refine_communication(self, 
                                 original_content: str, 
                                 refinement_request: str,
                                 context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """コミュニケーション内容の改良"""
        
        refinement_prompt = f"""
        以下の文章を改良してください：
        
        元の文章:
        {original_content}
        
        改良要求: {refinement_request}
        
        改良された文章を返してください。
        """
        
        try:
            llm_response = await self.llm_provider.generate_response(refinement_prompt, context)
            
            return {
                "refined_content": llm_response["content"],
                "changes_made": "内容を改良しました",
                "confidence": llm_response.get("confidence", 0.8),
                "suggestions": [
                    "さらに調整しますか？",
                    "他の改良点はありますか？"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to refine communication: {e}")
            return {
                "refined_content": original_content,
                "error": str(e),
                "suggestions": ["もう一度お試しください"]
            }
    
    async def analyze_tone(self, content: str) -> Dict[str, Any]:
        """文章のトーン分析"""
        
        analysis_prompt = f"""
        以下の文章のトーンを分析してください：
        
        文章: {content}
        
        以下の項目を JSON 形式で返してください：
        {{
            "tone": "formal/casual/friendly/professional/concise",
            "politeness_level": 1-5,
            "emotion": "positive/neutral/negative",
            "clarity": 1-5,
            "suggestions": ["改善提案1", "改善提案2"]
        }}
        """
        
        try:
            llm_response = await self.llm_provider.generate_response(analysis_prompt)
            import json
            analysis_result = json.loads(llm_response["content"])
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Failed to analyze tone: {e}")
            return {
                "tone": "unknown",
                "error": str(e)
            }
    
    def get_template_suggestions(self, comm_type: CommunicationType) -> List[Dict[str, str]]:
        """利用可能なテンプレートの提案"""
        
        suitable_templates = [
            template for template in self.templates.values()
            if template.type == comm_type
        ]
        
        return [
            {
                "template_id": template.template_id,
                "name": template.name,
                "tone": template.tone.value,
                "usage_count": template.usage_count
            }
            for template in sorted(suitable_templates, key=lambda t: t.usage_count, reverse=True)
        ]
    
    async def create_custom_template(self, 
                                   name: str,
                                   comm_type: CommunicationType,
                                   tone: ToneStyle,
                                   template_content: str) -> str:
        """カスタムテンプレートの作成"""
        
        import uuid
        template_id = f"custom_{uuid.uuid4().hex[:8]}"
        
        # プレースホルダーを自動抽出
        import re
        placeholders = re.findall(r'{(\w+)}', template_content)
        
        custom_template = CommunicationTemplate(
            template_id=template_id,
            name=name,
            type=comm_type,
            tone=tone,
            template=template_content,
            placeholders=placeholders,
            usage_count=0
        )
        
        self.templates[template_id] = custom_template
        
        logger.info(f"Custom template created: {template_id} - {name}")
        return template_id
    
    def get_communication_stats(self) -> Dict[str, Any]:
        """コミュニケーション統計"""
        
        total_templates = len(self.templates)
        total_usage = sum(template.usage_count for template in self.templates.values())
        
        type_stats = {}
        for comm_type in CommunicationType:
            type_stats[comm_type.value] = len([
                t for t in self.templates.values() if t.type == comm_type
            ])
        
        most_used = max(self.templates.values(), key=lambda t: t.usage_count) if self.templates else None
        
        return {
            "total_templates": total_templates,
            "total_usage": total_usage,
            "type_distribution": type_stats,
            "most_used_template": {
                "name": most_used.name,
                "usage_count": most_used.usage_count
            } if most_used else None
        }