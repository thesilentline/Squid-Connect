from typing import List, Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message


class MessageRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        tokens_used: Optional[int] = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
        )
        self.session.add(message)
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=func.now())
        )
        await self.session.commit()
        await self.session.refresh(message, ["id", "conversation_id", "role", "content", "tokens_used", "created_at"])
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
        messages.reverse()
        return messages
