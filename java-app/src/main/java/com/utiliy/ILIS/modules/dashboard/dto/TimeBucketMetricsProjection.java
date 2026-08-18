package com.utiliy.ILIS.modules.dashboard.dto;

import java.time.Instant;

public interface TimeBucketMetricsProjection {
    Instant getTimeBucket();
    Long getTotalRequests();
    Long getSuccessfulRequests();
    Long getErrorCount();
    Double getErrorRatePercent();
    Double getAvgLatencyMs();
    Double getP50LatencyMs();
    Double getP95LatencyMs();
    Double getP99LatencyMs();
    Double getRequestsPerSecond();
    Long getTotalTokens();
    Double getTokensPerSecond();
}
