package com.utiliy.ILIS.modules.injection;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class InjectionScheduler {

    private final InjectionService injectionService;

    /**
     * Periodically polls pending webhook events, updates status, and processes them.
     */
    @Scheduled(fixedDelayString = "${ilis.scheduler.fixed-delay-ms:5000}")
    public void scheduleWebhookProcessing() {
        try {
            injectionService.processPendingWebhooks();
        } catch (Exception e) {
            log.error("Error during scheduled webhook processing: {}", e.getMessage(), e);
        }
    }
}