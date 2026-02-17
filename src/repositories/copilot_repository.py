from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.copilot import CopilotConversation, CopilotMessage
from src.repositories.base import BaseRepository


class CopilotConversationRepository(BaseRepository[CopilotConversation]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, CopilotConversation)

    async def get_by_identity(
        self,
        incident_id: Optional[UUID],
        user_id: Optional[str],
        channel_id: Optional[str],
        source: str,
    ) -> CopilotConversation | None:
        filters = [
            CopilotConversation.source == source,
            CopilotConversation.user_id.is_(None) if user_id is None else CopilotConversation.user_id == user_id,
            CopilotConversation.channel_id.is_(None) if channel_id is None else CopilotConversation.channel_id == channel_id,
            CopilotConversation.incident_id.is_(None) if incident_id is None else CopilotConversation.incident_id == incident_id,
        ]
        result = await self.session.execute(select(CopilotConversation).where(*filters))
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        incident_id: Optional[UUID],
        user_id: Optional[str],
        channel_id: Optional[str],
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CopilotConversation:
        conversation = await self.get_by_identity(incident_id, user_id, channel_id, source)
        if conversation:
            if metadata:
                await self.update_metadata(conversation, metadata)
            return conversation

        conversation = CopilotConversation(
            incident_id=incident_id,
            user_id=user_id,
            channel_id=channel_id,
            source=source,
            extra_data=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await self.create(conversation)
        return conversation

    async def append_message(
        self,
        conversation: CopilotConversation,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CopilotMessage:
        message = CopilotMessage(
            conversation_id=conversation.id,
            role=role,
            content=content,
            extra_data=metadata or {},
            created_at=datetime.utcnow(),
        )
        self.session.add(message)
        conversation.updated_at = datetime.utcnow()
        await self.session.flush()
        return message

    async def list_recent_messages(
        self,
        conversation_id: UUID,
        limit: int = 12,
    ) -> List[CopilotMessage]:
        result = await self.session.execute(
            select(CopilotMessage)
            .where(CopilotMessage.conversation_id == conversation_id)
            .order_by(CopilotMessage.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages))

    async def update_summary(self, conversation: CopilotConversation, summary: str) -> None:
        conversation.latest_summary = summary
        conversation.updated_at = datetime.utcnow()
        await self.session.flush()

    async def update_metadata(
        self,
        conversation: CopilotConversation,
        metadata: Dict[str, Any],
    ) -> None:
        merged = {**(conversation.extra_data or {}), **metadata}
        conversation.extra_data = merged
        conversation.updated_at = datetime.utcnow()
        await self.session.flush()
