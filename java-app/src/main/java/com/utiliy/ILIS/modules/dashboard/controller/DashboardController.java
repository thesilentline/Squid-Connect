package com.utiliy.ILIS.modules.dashboard.controller;

import com.utiliy.ILIS.modules.dashboard.dto.DashboardResponse;
import com.utiliy.ILIS.modules.dashboard.dto.DashboardSummaryResponse;
import com.utiliy.ILIS.modules.dashboard.dto.TimeBucketMetricsResponse;
import com.utiliy.ILIS.modules.dashboard.service.DashboardService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
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
@Tag(name = "Analytics & Dashboard", description = "Real-time performance analytics, time-bucketed aggregation, latency percentiles (P50/P95/P99), error rates, and token throughput")
public class DashboardController {

    private final DashboardService dashboardService;

    @Operation(
            summary = "Get Full Dashboard Metrics (Summary + Time-Series)",
            description = "Computes aggregated inference metrics across the specified window alongside time-bucketed statistics (requests, latency percentiles P50/P95/P99, error rates, and token throughput) using PostgreSQL date_bin."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Dashboard metrics calculated successfully",
                    content = @Content(mediaType = "application/json", schema = @Schema(implementation = DashboardResponse.class))
            )
    })
    @GetMapping("/metrics")
    public ResponseEntity<DashboardResponse> getMetrics(
            @Parameter(description = "Start timestamp (ISO-8601 UTC). Defaults to 24 hours prior to endTime.", example = "2026-08-18T00:00:00Z")
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant from,

            @Parameter(description = "End timestamp (ISO-8601 UTC). Defaults to current instant.", example = "2026-08-19T00:00:00Z")
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant to,

            @Parameter(description = "Time-bin stride interval (e.g. '1 minute', '5 minutes', '15 minutes', '1 hour', '1 day')", example = "5 minutes")
            @RequestParam(defaultValue = "5 minutes") String interval,

            @Parameter(description = "Optional filter by model name (e.g. 'gpt-4o', 'claude-3-opus')", example = "gpt-4o")
            @RequestParam(required = false) String model,

            @Parameter(description = "Optional filter by provider (e.g. 'openai', 'anthropic', 'google')", example = "openai")
            @RequestParam(required = false) String provider) {

        DashboardResponse response = dashboardService.getDashboardMetrics(from, to, interval, model, provider);
        return ResponseEntity.ok(response);
    }

    @Operation(
            summary = "Get Time-Series Bucketed Metrics",
            description = "Returns an array of time-bucket records with request volumes, latency distributions, error rates, and token consumption."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Time-series records retrieved successfully",
                    content = @Content(mediaType = "application/json", array = @ArraySchema(schema = @Schema(implementation = TimeBucketMetricsResponse.class)))
            )
    })
    @GetMapping("/timeseries")
    public ResponseEntity<List<TimeBucketMetricsResponse>> getTimeSeries(
            @Parameter(description = "Start timestamp (ISO-8601 UTC). Defaults to 24 hours prior to endTime.", example = "2026-08-18T00:00:00Z")
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant from,

            @Parameter(description = "End timestamp (ISO-8601 UTC). Defaults to current instant.", example = "2026-08-19T00:00:00Z")
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant to,

            @Parameter(description = "Time-bin stride interval (e.g. '5 minutes')", example = "5 minutes")
            @RequestParam(defaultValue = "5 minutes") String interval,

            @Parameter(description = "Optional filter by model name", example = "gpt-4o")
            @RequestParam(required = false) String model,

            @Parameter(description = "Optional filter by provider", example = "openai")
            @RequestParam(required = false) String provider) {

        List<TimeBucketMetricsResponse> response = dashboardService.getTimeBucketMetrics(from, to, interval, model, provider);
        return ResponseEntity.ok(response);
    }

    @Operation(
            summary = "Get Overall Summary KPI Metrics",
            description = "Returns summary statistics across the whole selected time window."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Summary metrics retrieved successfully",
                    content = @Content(mediaType = "application/json", schema = @Schema(implementation = DashboardSummaryResponse.class))
            )
    })
    @GetMapping("/summary")
    public ResponseEntity<DashboardSummaryResponse> getSummary(
            @Parameter(description = "Start timestamp (ISO-8601 UTC). Defaults to 24 hours prior to endTime.", example = "2026-08-18T00:00:00Z")
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant from,

            @Parameter(description = "End timestamp (ISO-8601 UTC). Defaults to current instant.", example = "2026-08-19T00:00:00Z")
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant to,

            @Parameter(description = "Optional filter by model name", example = "gpt-4o")
            @RequestParam(required = false) String model,

            @Parameter(description = "Optional filter by provider", example = "openai")
            @RequestParam(required = false) String provider) {

        DashboardSummaryResponse response = dashboardService.getDashboardSummary(from, to, model, provider);
        return ResponseEntity.ok(response);
    }
}
