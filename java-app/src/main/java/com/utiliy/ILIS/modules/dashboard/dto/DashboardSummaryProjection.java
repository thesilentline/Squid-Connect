package com.utiliy.ILIS.modules.dashboard.dto;

public interface DashboardSummaryProjection {
    Long getTotalRequests();
    Long getSuccessfulRequests();
    Long getErrorCount();
    Double getErrorRatePercent();
    Double getAvgLatencyMs();
    Double getP50LatencyMs();
    Double getP95LatencyMs();
    Double getP99LatencyMs();
    Long getTotalTokens();
    Double getAvgTokensPerRequest();
}
