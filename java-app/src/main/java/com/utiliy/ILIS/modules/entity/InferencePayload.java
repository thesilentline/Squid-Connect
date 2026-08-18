package com.utiliy.ILIS.modules.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "inference_payload")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class InferencePayload {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(columnDefinition = "TEXT")
    private String input;

    @Column(columnDefinition = "TEXT")
    private String output;

    @Column(columnDefinition = "TEXT")
    private String metadata;
}