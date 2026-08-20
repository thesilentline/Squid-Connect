package com.utiliy.ILIS.modules.webhook;

import com.utiliy.ILIS.modules.injection.InjectionService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
public class WebhookController {

    private final InjectionService injectionService;

    @PostMapping("/api/v1/collectionEvent")
    public ResponseEntity<?> collectionEvent(
            @RequestParam(required = false) String type,
            @RequestBody Object request) {
        return ResponseEntity.ok(injectionService.inject(type, request));
    }
}
