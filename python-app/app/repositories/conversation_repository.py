from typing import Any, Dict, List, Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation


class ConversationRepository:
    """Repository handling universal conversation sessions and history."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conversation(
        self,
            title: str = "New Chat",
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Conversation:
        """Create and initialize a new conversation session."""
        conversation = Conversation(
            title=title,
            provider=provider,
            model=model,
        )
        self.session.add(conversation)
        try:
            await self.session.commit()
            return await self.get_by_id(conversation.id) or conversation
        except Exception:
            await self.session.rollback()
            raise

    async def get_by_id(self, conversation_id: int) -> Optional[Conversation]:
        """Fetch a conversation with its messages eager-loaded in chronological order."""
        query = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 50) -> List[Conversation]:
        """List conversation sessions with messages eagerly loaded."""
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_summaries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List past conversations with message counts and last message previews for sidebar display."""
        conversations = await self.list_all(limit=limit)
        summaries = []
        for conv in conversations:
            messages = conv.messages or []
            last_msg = messages[-1].content if messages else None
            if last_msg and len(last_msg) > 80:
                last_msg = last_msg[:80] + "..."
            
            summaries.append({
                "id": conv.id,
                "title": conv.title,
                "provider": conv.provider,
                "model": conv.model,
                "message_count": len(messages),
                "last_message_preview": last_msg,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
            })
        return summaries

    async def update_title(
        self,
        conversation_id: int,
        title: str,
    ) -> Optional[Conversation]:
        """Rename a conversation title."""
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(title=title, updated_at=func.now())
        )
        await self.session.commit()
        return await self.get_by_id(conversation_id)

    async def delete_conversation(self, conversation_id: int) -> bool:
        """Delete a conversation session and all its associated messages."""
        conv = await self.get_by_id(conversation_id)
        if conv:
            await self.session.delete(conv)
            await self.session.commit()
            return True
        return False
