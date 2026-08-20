package com.utiliy.ILIS.modules.dashboard.controller;

import com.utiliy.ILIS.modules.dashboard.dto.DashboardResponse;
import com.utiliy.ILIS.modules.dashboard.dto.DashboardSummaryResponse;
import com.utiliy.ILIS.modules.dashboard.dto.TimeBucketMetricsResponse;
import com.utiliy.ILIS.modules.dashboard.service.DashboardService;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.List;

@RestController
@RequestMapping("/api/v1/dashboard")
@RequiredArgsConstructor
public class DashboardController {

    private final DashboardService dashboardService;

    @GetMapping("/metrics")
    public ResponseEntity<DashboardResponse> getMetrics(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant to,
            @RequestParam(defaultValue = "5 minutes") String interval,
            @RequestParam(required = false) String model,
            @RequestParam(required = false) String provider) {

        DashboardResponse response = dashboardService.getDashboardMetrics(from, to, interval, model, provider);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/timeseries")
    public ResponseEntity<List<TimeBucketMetricsResponse>> getTimeSeries(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant to,
            @RequestParam(defaultValue = "5 minutes") String interval,
            @RequestParam(required = false) String model,
            @RequestParam(required = false) String provider) {

        List<TimeBucketMetricsResponse> response = dashboardService.getTimeBucketMetrics(from, to, interval, model, provider);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/summary")
    public ResponseEntity<DashboardSummaryResponse> getSummary(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant to,
            @RequestParam(required = false) String model,
            @RequestParam(required = false) String provider) {

        DashboardSummaryResponse response = dashboardService.getDashboardSummary(from, to, model, provider);
        return ResponseEntity.ok(response);
    }
}
