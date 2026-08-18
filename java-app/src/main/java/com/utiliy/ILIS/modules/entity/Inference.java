package com.utiliy.ILIS.modules.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

@Entity
@Table(name = "inference")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Inference {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String requestId;
    private String model;
    private String provider;

    private Long userId;

    @Enumerated(EnumType.STRING)
    private InferenceStatus status;
    private Instant startedAt;
    private Instant completedAt;
    private Long latencyMs;
    private Integer inputTokens;
    private Integer outputTokens;
    private Integer totalTokens;
    private Instant createdAt;
    private Long inferencePayloadId;

    @PrePersist
    protected void onCreate() {
        createdAt = Instant.now();
    }

    public enum InferenceStatus {
        RECEIVED, PROCESSING, SUCCESS, FAILED
    }
}
