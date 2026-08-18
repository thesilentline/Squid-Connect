package com.utiliy.ILIS.modules.repository;

import com.utiliy.ILIS.modules.dashboard.dto.DashboardSummaryProjection;
import com.utiliy.ILIS.modules.dashboard.dto.TimeBucketMetricsProjection;
import com.utiliy.ILIS.modules.entity.Inference;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface InferenceRepository extends JpaRepository<Inference, Long> {

    Optional<Inference> findByRequestId(String requestId);

    @Query(value = """
            SELECT
                date_bin(
                    CAST(:bucketInterval AS interval),
                    created_at,
                    TIMESTAMPTZ '2000-01-01 00:00:00+00'
                ) AS timeBucket,

                COUNT(*) AS totalRequests,

                COUNT(*) FILTER (WHERE status = 'SUCCESS') AS successfulRequests,

                COUNT(*) FILTER (WHERE status != 'SUCCESS') AS errorCount,

                ROUND(
                    (COUNT(*) FILTER (WHERE status != 'SUCCESS') * 100.0 / NULLIF(COUNT(*), 0))::numeric,
                    2
                ) AS errorRatePercent,

                ROUND(
                    AVG(COALESCE(latency_ms, EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000))::numeric,
                    2
                ) AS avgLatencyMs,

                ROUND(
                    PERCENTILE_CONT(0.50) WITHIN GROUP (
                        ORDER BY COALESCE(latency_ms, EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000)
                    )::numeric,
                    2
                ) AS p50LatencyMs,

                ROUND(
                    PERCENTILE_CONT(0.95) WITHIN GROUP (
                        ORDER BY COALESCE(latency_ms, EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000)
                    )::numeric,
                    2
                ) AS p95LatencyMs,

                ROUND(
                    PERCENTILE_CONT(0.99) WITHIN GROUP (
                        ORDER BY COALESCE(latency_ms, EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000)
                    )::numeric,
                    2
                ) AS p99LatencyMs,

                ROUND((COUNT(*) / :bucketSeconds)::numeric, 2) AS requestsPerSecond,

                COALESCE(SUM(total_tokens), 0) AS totalTokens,

                ROUND((COALESCE(SUM(total_tokens), 0) / :bucketSeconds)::numeric, 2) AS tokensPerSecond

            FROM inference
            WHERE created_at >= :startTime AND created_at <= :endTime
              AND (:model IS NULL OR model = :model)
              AND (:provider IS NULL OR provider = :provider)
            GROUP BY timeBucket
            ORDER BY timeBucket ASC
            """, nativeQuery = true)
    List<TimeBucketMetricsProjection> findTimeBucketMetrics(
            @Param("startTime") Instant startTime,
            @Param("endTime") Instant endTime,
            @Param("bucketInterval") String bucketInterval,
            @Param("bucketSeconds") double bucketSeconds,
            @Param("model") String model,
            @Param("provider") String provider
    );

    @Query(value = """
            SELECT
                COUNT(*) AS totalRequests,
                COUNT(*) FILTER (WHERE status = 'SUCCESS') AS successfulRequests,
                COUNT(*) FILTER (WHERE status != 'SUCCESS') AS errorCount,
                ROUND(
                    (COUNT(*) FILTER (WHERE status != 'SUCCESS') * 100.0 / NULLIF(COUNT(*), 0))::numeric,
                    2
                ) AS errorRatePercent,
                ROUND(
                    AVG(COALESCE(latency_ms, EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000))::numeric,
                    2
                ) AS avgLatencyMs,
                ROUND(
                    PERCENTILE_CONT(0.50) WITHIN GROUP (
                        ORDER BY COALESCE(latency_ms, EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000)
                    )::numeric,
                    2
                ) AS p50LatencyMs,
                ROUND(
                    PERCENTILE_CONT(0.95) WITHIN GROUP (
                        ORDER BY COALESCE(latency_ms, EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000)
                    )::numeric,
                    2
                ) AS p95LatencyMs,
                ROUND(
                    PERCENTILE_CONT(0.99) WITHIN GROUP (
                        ORDER BY COALESCE(latency_ms, EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000)
                    )::numeric,
                    2
                ) AS p99LatencyMs,
                COALESCE(SUM(total_tokens), 0) AS totalTokens,
                ROUND(
                    (COALESCE(SUM(total_tokens), 0) * 1.0 / NULLIF(COUNT(*), 0))::numeric,
                    2
                ) AS avgTokensPerRequest
            FROM inference
            WHERE created_at >= :startTime AND created_at <= :endTime
              AND (:model IS NULL OR model = :model)
              AND (:provider IS NULL OR provider = :provider)
            """, nativeQuery = true)
    DashboardSummaryProjection findDashboardSummary(
            @Param("startTime") Instant startTime,
            @Param("endTime") Instant endTime,
            @Param("model") String model,
            @Param("provider") String provider
    );
}
