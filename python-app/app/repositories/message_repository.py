from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


class MessageRepository:
    """Repository handling Message persistence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        tokens_used: Optional[int] = None,
    ) -> Message:
        """Create and persist a new chat message."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_messages_by_conversation(
        self,
        conversation_id: int,
        limit: int = 5,
    ) -> List[Message]:
        """
        Fetch the latest N messages for a conversation ordered chronologically (oldest to newest).
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        messages = list(result.scalars().all())
        # Reverse to return in chronological order (oldest to newest)
        messages.reverse()
        return messages
