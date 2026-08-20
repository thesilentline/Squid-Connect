package com.utiliy.ILIS.modules.dashboard.service;

import com.utiliy.ILIS.modules.dashboard.dto.*;
import com.utiliy.ILIS.modules.repository.InferenceRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Service
@RequiredArgsConstructor
public class DashboardService {

    private final InferenceRepository inferenceRepository;

    private static final Pattern INTERVAL_PATTERN = Pattern.compile("^\\s*(\\d+)\\s*([a-zA-Z]+)\\s*$");

    @Transactional(readOnly = true)
    public DashboardResponse getDashboardMetrics(Instant startTime,
                                                 Instant endTime,
                                                 String bucketInterval,
                                                 String model,
                                                 String provider) {
        Instant effectiveEndTime = endTime != null ? endTime : Instant.now();
        Instant effectiveStartTime = startTime != null ? startTime : effectiveEndTime.minus(Duration.ofHours(24));
        String effectiveInterval = (bucketInterval != null && !bucketInterval.isBlank()) ? bucketInterval.trim() : "5 minutes";
        double bucketSeconds = calculateBucketSeconds(effectiveInterval);

        log.info("Fetching dashboard metrics from {} to {} with bucket interval '{}' ({}s)",
                effectiveStartTime, effectiveEndTime, effectiveInterval, bucketSeconds);

        List<TimeBucketMetricsProjection> bucketProjections = inferenceRepository.findTimeBucketMetrics(
                effectiveStartTime,
                effectiveEndTime,
                effectiveInterval,
                bucketSeconds,
                (model != null && !model.isBlank()) ? model.trim() : null,
                (provider != null && !provider.isBlank()) ? provider.trim() : null
        );

        DashboardSummaryProjection summaryProjection = inferenceRepository.findDashboardSummary(
                effectiveStartTime,
                effectiveEndTime,
                (model != null && !model.isBlank()) ? model.trim() : null,
                (provider != null && !provider.isBlank()) ? provider.trim() : null
        );

        List<TimeBucketMetricsResponse> timeSeries = bucketProjections.stream()
                .map(TimeBucketMetricsResponse::fromProjection)
                .toList();

        DashboardSummaryResponse summary = DashboardSummaryResponse.fromProjection(summaryProjection);

        return DashboardResponse.builder()
                .startTime(effectiveStartTime)
                .endTime(effectiveEndTime)
                .bucketInterval(effectiveInterval)
                .summary(summary)
                .timeSeries(timeSeries)
                .build();
    }

    @Transactional(readOnly = true)
    public List<TimeBucketMetricsResponse> getTimeBucketMetrics(Instant startTime,
                                                               Instant endTime,
                                                               String bucketInterval,
                                                               String model,
                                                               String provider) {
        Instant effectiveEndTime = endTime != null ? endTime : Instant.now();
        Instant effectiveStartTime = startTime != null ? startTime : effectiveEndTime.minus(Duration.ofHours(24));
        String effectiveInterval = (bucketInterval != null && !bucketInterval.isBlank()) ? bucketInterval.trim() : "5 minutes";
        double bucketSeconds = calculateBucketSeconds(effectiveInterval);

        List<TimeBucketMetricsProjection> bucketProjections = inferenceRepository.findTimeBucketMetrics(
                effectiveStartTime,
                effectiveEndTime,
                effectiveInterval,
                bucketSeconds,
                (model != null && !model.isBlank()) ? model.trim() : null,
                (provider != null && !provider.isBlank()) ? provider.trim() : null
        );

        return bucketProjections.stream()
                .map(TimeBucketMetricsResponse::fromProjection)
                .toList();
    }

    @Transactional(readOnly = true)
    public DashboardSummaryResponse getDashboardSummary(Instant startTime,
                                                        Instant endTime,
                                                        String model,
                                                        String provider) {
        Instant effectiveEndTime = endTime != null ? endTime : Instant.now();
        Instant effectiveStartTime = startTime != null ? startTime : effectiveEndTime.minus(Duration.ofHours(24));

        DashboardSummaryProjection summaryProjection = inferenceRepository.findDashboardSummary(
                effectiveStartTime,
                effectiveEndTime,
                (model != null && !model.isBlank()) ? model.trim() : null,
                (provider != null && !provider.isBlank()) ? provider.trim() : null
        );

        return DashboardSummaryResponse.fromProjection(summaryProjection);
    }

    public double calculateBucketSeconds(String intervalStr) {
        if (intervalStr == null || intervalStr.isBlank()) {
            return 300.0;
        }
        Matcher matcher = INTERVAL_PATTERN.matcher(intervalStr.trim().toLowerCase());
        if (!matcher.matches()) {
            return 300.0;
        }

        try {
            long count = Long.parseLong(matcher.group(1));
            String unit = matcher.group(2).toLowerCase();

            if (unit.startsWith("sec") || unit.equals("s")) {
                return Math.max(1.0, count);
            } else if (unit.startsWith("min") || unit.equals("m")) {
                return Math.max(1.0, count * 60.0);
            } else if (unit.startsWith("hour") || unit.startsWith("hr") || unit.equals("h")) {
                return Math.max(1.0, count * 3600.0);
            } else if (unit.startsWith("day") || unit.equals("d")) {
                return Math.max(1.0, count * 86400.0);
            }
        } catch (Exception ignored) {
        }
        return 300.0;
    }
}
