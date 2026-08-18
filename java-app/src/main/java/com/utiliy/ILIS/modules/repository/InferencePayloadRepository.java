package com.utiliy.ILIS.modules.repository;

import com.utiliy.ILIS.modules.entity.InferencePayload;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface InferencePayloadRepository extends JpaRepository<InferencePayload, Long> {
}
