package com.utiliy.ILIS.modules.repository;

import com.utiliy.ILIS.modules.entity.WebhookData;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface WebhookDataRepository extends JpaRepository<WebhookData, Long> {
    List<WebhookData> findTop50ByStatusOrderByIdAsc(WebhookData.WebhookStatus status);
    List<WebhookData> findByStatusOrderByIdAsc(WebhookData.WebhookStatus status);
}
