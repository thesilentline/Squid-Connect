package com.utiliy.ILIS.modules.injection;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.utiliy.ILIS.modules.entity.Inference;
import com.utiliy.ILIS.modules.entity.InferencePayload;
import com.utiliy.ILIS.modules.entity.WebhookData;
import com.utiliy.ILIS.modules.parser.InferenceEventParser;
import com.utiliy.ILIS.modules.parser.ParsedInferenceRecord;
import com.utiliy.ILIS.modules.repository.InferencePayloadRepository;
import com.utiliy.ILIS.modules.repository.InferenceRepository;
import com.utiliy.ILIS.modules.repository.WebhookDataRepository;
import lombok.AllArgsConstructor;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class InjectionService {

    private final WebhookDataRepository webhookDataRepository;
    private final InferenceRepository inferenceRepository;
    private final InferencePayloadRepository inferencePayloadRepository;
    private final InferenceEventParser inferenceEventParser;
    private ObjectMapper objectMapper = new ObjectMapper();

    /**
     * Captures incoming raw webhook event and stores it in webhook_data table with PENDING status.
     */
    @Transactional
    public Map<String, Object> inject(String type, Object request) {
        log.info("Capturing webhook event of type '{}'", type);

        String payloadStr;
        try {
            if (request instanceof String str) {
                payloadStr = str;
            } else {
                payloadStr = objectMapper.writeValueAsString(request);
            }
        } catch (Exception e) {
            log.error("Failed to serialize request payload: {}", e.getMessage(), e);
            payloadStr = String.valueOf(request);
        }

        WebhookData webhookData = WebhookData.builder()
                .type(type != null ? type : "INFERENCE_LOGGING")
                .payload(payloadStr)
                .status(WebhookData.WebhookStatus.PENDING)
                .build();

        WebhookData saved = webhookDataRepository.save(webhookData);
        log.info("Successfully queued webhook event with ID: {}", saved.getId());

        Map<String, Object> response = new HashMap<>();
        response.put("status", "SUCCESS");
        response.put("message", "Event captured successfully and queued for processing");
        response.put("webhookId", saved.getId());
        response.put("eventStatus", saved.getStatus().name());
        return response;
    }

    /**
     * Processes pending webhook records. Called by InjectionScheduler.
     */
    public void processPendingWebhooks() {
        List<WebhookData> pendingList = webhookDataRepository.findTop50ByStatusOrderByIdAsc(WebhookData.WebhookStatus.PENDING);
        if (pendingList.isEmpty()) {
            return;
        }

        log.info("Found {} pending webhook event(s) to process", pendingList.size());
        for (WebhookData webhookData : pendingList) {
            try {
                processSingleWebhook(webhookData);
            } catch (Exception e) {
                log.error("Unexpected failure while processing webhook ID {}: {}", webhookData.getId(), e.getMessage(), e);
            }
        }
    }

    /**
     * Parses and persists a single webhook record into Inference & InferencePayload entities.
     */
    @Transactional
    public void processSingleWebhook(WebhookData webhookData) {
        log.info("Processing webhook event ID: {}", webhookData.getId());
        webhookData.setStatus(WebhookData.WebhookStatus.PROCESSING);
        webhookDataRepository.save(webhookData);

        try {
            // 1. Parse raw payload
            ParsedInferenceRecord parsed = inferenceEventParser.parse(webhookData.getPayload());

            // 2. Persist InferencePayload
            InferencePayload savedPayload = inferencePayloadRepository.save(parsed.getInferencePayload());

            // 3. Link InferencePayload ID to Inference and persist Inference
            Inference inference = parsed.getInference();
            inference.setInferencePayloadId(savedPayload.getId());
            Inference savedInference = inferenceRepository.save(inference);

            // 4. Update WebhookData to COMPLETED
            webhookData.setStatus(WebhookData.WebhookStatus.COMPLETED);
            webhookData.setErrorMessage(null);
            webhookDataRepository.save(webhookData);

            log.info("Successfully processed webhook ID: {} -> Inference ID: {}, Payload ID: {}",
                    webhookData.getId(), savedInference.getId(), savedPayload.getId());
        } catch (Exception e) {
            log.error("Failed to parse and store webhook ID {}: {}", webhookData.getId(), e.getMessage(), e);
            webhookData.setStatus(WebhookData.WebhookStatus.FAILED);
            webhookData.setErrorMessage(e.getMessage() != null ? e.getMessage() : e.getClass().getSimpleName());
            webhookData.setRetryCount(webhookData.getRetryCount() + 1);
            webhookDataRepository.save(webhookData);
        }
    }
}
