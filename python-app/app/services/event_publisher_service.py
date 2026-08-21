from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from typing import Any, Dict, List, Optional, Union
import uuid
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class InferenceStatus(str, Enum):
    """Lifecycle status matching Java com.utiliy.ILIS.modules.entity.Inference.InferenceStatus."""
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


def format_instant(dt: Optional[datetime]) -> Optional[str]:
    """
    Format a Python datetime to standard ISO-8601 Instant format (e.g. 2026-08-18T04:21:30.123456Z)
    fully compatible with Java java.time.Instant.parse() and Jackson JavaTimeModule.
    """
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    iso = dt.astimezone(timezone.utc).isoformat()
    if iso.endswith("+00:00"):
        iso = iso[:-6] + "Z"
    elif not iso.endswith("Z"):
        if "+" in iso:
            iso = iso.split("+")[0] + "Z"
        elif iso.count("-") > 2:
            iso = iso.rsplit("-", 1)[0] + "Z"
    return iso


def stringify_metadata(metadata: Optional[Any]) -> Optional[str]:
    """Ensure metadata is formatted as a JSON string for Java TEXT column."""
    if metadata is None:
        return None
    if isinstance(metadata, str):
        return metadata
    try:
        return json.dumps(metadata, default=str)
    except Exception:
        return str(metadata)


class EventPublisherService:
    """
    Asynchronous event publisher service that dispatches LLM inference events to the
    ILIS event ingestion endpoint (POST /api/v1/collectionEvent?type={status}).

    The dispatched payload maps 1:1 to:
      1. com.utiliy.ILIS.modules.entity.Inference
         - requestId (String)
         - model (String)
         - provider (String)
         - userId (Long)
         - status (InferenceStatus: RECEIVED, PROCESSING, SUCCESS, FAILED)
         - startedAt (Instant / ISO-8601)
         - completedAt (Instant / ISO-8601)
         - latencyMs (Long)
         - inputTokens (Integer)
         - outputTokens (Integer)
         - totalTokens (Integer)
         - inferencePayloadId (Long)

      2. com.utiliy.ILIS.modules.entity.InferencePayload
         - input (TEXT String)
         - output (TEXT String)
         - metadata (TEXT String / JSON)
    """

    def __init__(self):
        self.endpoint_url = settings.COLLECTION_EVENT_URL
        self.is_enabled = settings.COLLECTION_EVENT_ENABLED
        self.timeout = settings.COLLECTION_EVENT_TIMEOUT_SECONDS

    async def publish_event(self, event_type: str, request_payload: Dict[str, Any]) -> None:
        """
        Send an asynchronous HTTP POST request to the collectionEvent endpoint.
        Logs the dispatch and silently catches connection errors to ensure main chat availability.
        """
        if not self.is_enabled or not self.endpoint_url:
            logger.debug(f"Event publishing skipped (enabled={self.is_enabled}, endpoint={self.endpoint_url})")
            return

        params = {}
        if event_type:
            params["type"] = event_type

        req_id = request_payload.get("requestId") or request_payload.get("request_id")
        logger.info(f"📤 [EVENT DISPATCH] Sending '{event_type}' (requestId={req_id}) to {self.endpoint_url} ...")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.endpoint_url,
                    params=params,
                    json=request_payload,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code >= 400:
                    logger.warning(
                        f"⚠️ [EVENT DELIVERY FAILED] '{event_type}' (requestId={req_id}) to {self.endpoint_url} returned HTTP {response.status_code}: {response.text}"
                    )
                else:
                    logger.info(
                        f"✅ [EVENT DELIVERED] '{event_type}' (requestId={req_id}) successfully sent to {self.endpoint_url} (HTTP {response.status_code})"
                    )
        except Exception as ex:
            logger.warning(
                f"❌ [EVENT DELIVERY ERROR] Could not reach {self.endpoint_url} for '{event_type}' (requestId={req_id}): {str(ex)}"
            )

    def dispatch_background_event(self, event_type: str, request_payload: Dict[str, Any]) -> None:
        """Fire-and-forget background event publishing using asyncio task."""
        if not self.is_enabled:
            return
        try:
            asyncio.create_task(self.publish_event(event_type, request_payload))
        except Exception as e:
            logger.warning(f"Could not spawn background event task: {e}")

    async def publish_inference_event(
        self,
        request_id: str,
        model: str,
        provider: str,
        status: Union[InferenceStatus, str],
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        latency_ms: Optional[Union[int, float]] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        user_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        inference_payload_id: Optional[int] = None,
        input_text: Optional[str] = None,
        output_text: Optional[str] = None,
        metadata: Optional[Any] = None,
        event_type: Optional[str] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
    ) -> None:
        status_val = status.value if isinstance(status, InferenceStatus) else str(status)
        started_at_str = format_instant(started_at)
        completed_at_str = format_instant(completed_at)
        lat_ms_val = int(round(latency_ms)) if latency_ms is not None else None
        meta_str = stringify_metadata(metadata)

        payload_data = {
            "input": input_text,
            "output": output_text,
            "metadata": meta_str,
        }

        event_body: Dict[str, Any] = {
            "requestId": request_id,
            "model": model,
            "provider": provider,
            "userId": user_id,
            "conversationId": conversation_id,
            "status": status_val,
            "startedAt": started_at_str,
            "completedAt": completed_at_str,
            "latencyMs": lat_ms_val,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "totalTokens": total_tokens,
            "inferencePayloadId": inference_payload_id,
            "errorMessage": error_message,
            "errorType": error_type,

            "input": input_text,
            "output": output_text,
            "metadata": meta_str,
            "inferencePayload": payload_data,
            "payload": payload_data,

            "request_id": request_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "started_at": started_at_str,
            "completed_at": completed_at_str,
            "latency_ms": lat_ms_val,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "inference_payload_id": inference_payload_id,
            "error_message": error_message,
            "error_type": error_type,
            "error": error_message,
            "event_type": event_type or status_val,
        }

        dispatch_type = event_type or status_val

        logger.info(
            f"⚡ [EVENT TRIGGERED] type='{dispatch_type}' | status='{status_val}' | requestId='{request_id}' | model='{model}' | provider='{provider}' | latency={lat_ms_val}ms | tokens={total_tokens}\n"
            f"📄 Event Payload:\n{json.dumps(event_body, indent=2, default=str)}"
        )

        self.dispatch_background_event(dispatch_type, event_body)

    async def publish_inference_received(
        self,
        request_id: str,
        model: str,
        provider: str,
        input_text: str,
        user_id: Optional[int] = None,
        started_at: Optional[datetime] = None,
        metadata: Optional[Any] = None,
    ) -> None:
        """Publish and log RECEIVED inference status event."""
        await self.publish_inference_event(
            request_id=request_id,
            model=model,
            provider=provider,
            status=InferenceStatus.RECEIVED,
            started_at=started_at or datetime.now(timezone.utc),
            input_text=input_text,
            user_id=user_id,
            metadata=metadata,
            event_type="RECEIVED",
        )

    async def publish_inference_processing(
        self,
        request_id: str,
        model: str,
        provider: str,
        input_text: str,
        user_id: Optional[int] = None,
        started_at: Optional[datetime] = None,
        metadata: Optional[Any] = None,
    ) -> None:
        """Publish and log PROCESSING inference status event."""
        await self.publish_inference_event(
            request_id=request_id,
            model=model,
            provider=provider,
            status=InferenceStatus.PROCESSING,
            started_at=started_at or datetime.now(timezone.utc),
            input_text=input_text,
            user_id=user_id,
            metadata=metadata,
            event_type="PROCESSING",
        )

    async def publish_inference_success(
        self,
        request_id: str,
        model: str,
        provider: str,
        input_text: str,
        output_text: str,
        started_at: datetime,
        completed_at: datetime,
        latency_ms: Union[int, float],
        conversation_id: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        user_id: Optional[int] = None,
        metadata: Optional[Any] = None,
    ) -> None:
        await self.publish_inference_event(
            request_id=request_id,
            model=model,
            provider=provider,
            status=InferenceStatus.SUCCESS,
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=latency_ms,
            conversation_id=conversation_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            input_text=input_text,
            output_text=output_text,
            user_id=user_id,
            metadata=metadata,
            event_type="SUCCESS",
        )

    async def publish_inference_failed(
        self,
        request_id: str,
        model: str,
        provider: str,
        input_text: str,
        error_message: str,
        started_at: datetime,
        completed_at: datetime,
        conversation_id: Optional[int] = None,
        input_tokens: Optional[int] = None,
        latency_ms: Optional[Union[int, float]] = None,
        user_id: Optional[int] = None,
        metadata: Optional[Any] = None,
        error_type: Optional[str] = None,
    ) -> None:
        meta_dict = {}
        if isinstance(metadata, dict):
            meta_dict = dict(metadata)
        meta_dict["error"] = error_message
        if error_type:
            meta_dict["error_type"] = error_type

        await self.publish_inference_event(
            request_id=request_id,
            model=model,
            provider=provider,
            status=InferenceStatus.FAILED,
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=latency_ms,
            conversation_id=conversation_id,
            input_tokens=input_tokens,
            input_text=input_text,
            output_text=f"ERROR: {error_message}",
            user_id=user_id,
            metadata=meta_dict,
            event_type="FAILED",
            error_message=error_message,
            error_type=error_type,
        )

    async def publish_message_request(
        self,
        conversation_id: int,
        message: str,
        provider: str,
        model: str,
        request_id: Optional[str] = None,
        user_id: Optional[int] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        started_at: Optional[datetime] = None,
    ) -> None:
        """Publish request event mapped to Inference + InferencePayload format."""
        req_id = request_id or str(uuid.uuid4())
        now = started_at or datetime.now(timezone.utc)
        meta = {
            "conversation_id": conversation_id,
            "system_prompt": system_prompt,
            "conversation_history": conversation_history or [],
            "extra_params": extra_params or {},
        }
        await self.publish_inference_event(
            request_id=req_id,
            model=model,
            provider=provider,
            user_id=user_id,
            status=InferenceStatus.PROCESSING,
            started_at=now,
            input_text=message,
            metadata=meta,
            event_type="MESSAGE_REQUEST",
        )

    async def publish_message_response(
        self,
        conversation_id: int,
        response_content: str,
        provider: str,
        model: str,
        request_id: Optional[str] = None,
        user_id: Optional[int] = None,
        input_text: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        tokens_prompt: Optional[int] = None,
        tokens_completion: Optional[int] = None,
        tokens_total: Optional[int] = None,
        finish_reason: Optional[str] = None,
        latency_ms: Optional[Union[float, int]] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> None:
        """Publish response event mapped to Inference + InferencePayload format."""
        req_id = request_id or str(uuid.uuid4())
        now = completed_at or datetime.now(timezone.utc)
        lat_ms = int(round(latency_ms)) if latency_ms is not None else None
        meta = {
            "conversation_id": conversation_id,
            "finish_reason": finish_reason,
            "conversation_history": conversation_history or [],
        }
        await self.publish_inference_event(
            request_id=req_id,
            model=model,
            provider=provider,
            user_id=user_id,
            status=InferenceStatus.SUCCESS,
            started_at=started_at or now,
            completed_at=now,
            latency_ms=lat_ms,
            input_tokens=tokens_prompt,
            output_tokens=tokens_completion,
            total_tokens=tokens_total,
            input_text=input_text,
            output_text=response_content,
            metadata=meta,
            event_type="MESSAGE_RESPONSE",
        )


event_publisher = EventPublisherService()
