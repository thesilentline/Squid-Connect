package com.utiliy.ILIS.modules.webhook;

import com.utiliy.ILIS.modules.injection.InjectionService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequiredArgsConstructor
@Tag(name = "Webhook Ingestion", description = "Endpoints for collecting raw LLM inference events and message logs")
public class WebhookController {

    private final InjectionService injectionService;

    @Operation(
            summary = "Ingest LLM Inference / Webhook Event",
            description = "Captures raw inference logging events (both successful and failed responses), queues them in the webhook buffer with PENDING status, and initiates asynchronous parsing into relational database tables."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Event successfully captured and queued",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = Map.class),
                            examples = @ExampleObject(
                                    name = "Success Acknowledgment",
                                    value = """
                                            {
                                              "status": "SUCCESS",
                                              "webhookId": 101,
                                              "eventStatus": "PENDING",
                                              "message": "Event captured successfully and queued for processing"
                                            }
                                            """
                            )
                    )
            ),
            @ApiResponse(responseCode = "400", description = "Invalid request payload or formatting")
    })
    @PostMapping("/api/v1/collectionEvent")
    public ResponseEntity<?> collectionEvent(
            @Parameter(description = "Event classification type (e.g. INFERENCE_LOGGING, MESSAGE_FAILURE)", example = "INFERENCE_LOGGING")
            @RequestParam(required = false) String type,

            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "Raw JSON or Map event containing messages, model, token usage, latency, or failure metadata",
                    required = true,
                    content = @Content(
                            mediaType = "application/json",
                            examples = {
                                    @ExampleObject(
                                            name = "Successful Inference Event",
                                            summary = "Standard LLM interaction log",
                                            value = """
                                                    {
                                                      "request_id": "req-101",
                                                      "model": "gpt-4o",
                                                      "provider": "openai",
                                                      "user_id": 26,
                                                      "messages": [
                                                        {
                                                          "id": 25,
                                                          "role": "assistant",
                                                          "content": "How's your day going? Anything fun planned?",
                                                          "tokens_used": 329,
                                                          "created_at": "2026-08-16T05:42:13.069718+00:00"
                                                        },
                                                        {
                                                          "id": 26,
                                                          "role": "user",
                                                          "content": "i need a little help",
                                                          "tokens_used": null,
                                                          "created_at": "2026-08-16T05:42:22.840509+00:00"
                                                        }
                                                      ],
                                                      "extra_params": {
                                                        "temperature": 0.7
                                                      },
                                                      "timestamp": "2026-08-16T05:42:22.844892+00:00"
                                                    }
                                                    """
                                    ),
                                    @ExampleObject(
                                            name = "Failed Inference Event",
                                            summary = "Message failure log with error diagnostic information",
                                            value = """
                                                    {
                                                      "event_type": "MESSAGE_FAILURE",
                                                      "status": "FAILED",
                                                      "conversation_id": 1,
                                                      "role": "assistant",
                                                      "error_message": "Incorrect API key provided: sk-invalid...",
                                                      "error_type": "AuthenticationError",
                                                      "provider": "openai",
                                                      "model": "gpt-4o",
                                                      "conversation_history": [
                                                        {
                                                          "id": 101,
                                                          "role": "user",
                                                          "content": "Generate a neural network in Python",
                                                          "tokens_used": null,
                                                          "created_at": "2026-08-18T21:40:00+00:00"
                                                        }
                                                      ],
                                                      "latency_ms": 412.35,
                                                      "timestamp": "2026-08-18T21:40:00.412350+00:00"
                                                    }
                                                    """
                                    )
                            }
                    )
            )
            @RequestBody Object request) {
        return ResponseEntity.ok(injectionService.inject(type, request));
    }
}
