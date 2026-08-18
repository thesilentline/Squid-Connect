package com.utiliy.ILIS.modules.dashboard.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DashboardSummaryResponse {
    private Long totalRequests;
    private Long successfulRequests;
    private Long errorCount;
    private Double errorRatePercent;
    private Double avgLatencyMs;
    private Double p50LatencyMs;
    private Double p95LatencyMs;
    private Double p99LatencyMs;
    private Long totalTokens;
    private Double avgTokensPerRequest;

    public static DashboardSummaryResponse fromProjection(DashboardSummaryProjection proj) {
        if (proj == null) {
            return DashboardSummaryResponse.builder()
                    .totalRequests(0L)
                    .successfulRequests(0L)
                    .errorCount(0L)
                    .errorRatePercent(0.0)
                    .avgLatencyMs(0.0)
                    .p50LatencyMs(0.0)
                    .p95LatencyMs(0.0)
                    .p99LatencyMs(0.0)
                    .totalTokens(0L)
                    .avgTokensPerRequest(0.0)
                    .build();
        }
        return DashboardSummaryResponse.builder()
                .totalRequests(proj.getTotalRequests() != null ? proj.getTotalRequests() : 0L)
                .successfulRequests(proj.getSuccessfulRequests() != null ? proj.getSuccessfulRequests() : 0L)
                .errorCount(proj.getErrorCount() != null ? proj.getErrorCount() : 0L)
                .errorRatePercent(proj.getErrorRatePercent() != null ? proj.getErrorRatePercent() : 0.0)
                .avgLatencyMs(proj.getAvgLatencyMs() != null ? proj.getAvgLatencyMs() : 0.0)
                .p50LatencyMs(proj.getP50LatencyMs() != null ? proj.getP50LatencyMs() : 0.0)
                .p95LatencyMs(proj.getP95LatencyMs() != null ? proj.getP95LatencyMs() : 0.0)
                .p99LatencyMs(proj.getP99LatencyMs() != null ? proj.getP99LatencyMs() : 0.0)
                .totalTokens(proj.getTotalTokens() != null ? proj.getTotalTokens() : 0L)
                .avgTokensPerRequest(proj.getAvgTokensPerRequest() != null ? proj.getAvgTokensPerRequest() : 0.0)
                .build();
    }
}
