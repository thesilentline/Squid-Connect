package com.utiliy.ILIS.modules.dashboard.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DashboardResponse {
    private Instant startTime;
    private Instant endTime;
    private String bucketInterval;
    private DashboardSummaryResponse summary;
    private List<TimeBucketMetricsResponse> timeSeries;
}
