package com.utiliy.ILIS.modules.parser;

import com.utiliy.ILIS.modules.entity.Inference;
import com.utiliy.ILIS.modules.entity.InferencePayload;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ParsedInferenceRecord {
    private Inference inference;
    private InferencePayload inferencePayload;
}
