package com.utiliy.ILIS.modules.parser;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.utiliy.ILIS.modules.entity.Inference;
import com.utiliy.ILIS.modules.entity.InferencePayload;
import lombok.AllArgsConstructor;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Slf4j
@Component
@AllArgsConstructor
public class InferenceEventParser {

    private final ObjectMapper objectMapper;

    public InferenceEventParser() {
        this.objectMapper = new ObjectMapper();
    }

    /**
     * Parses raw webhook payload into Inference and InferencePayload entities.
     */
    public ParsedInferenceRecord parse(String rawPayload) {
        if (rawPayload == null || rawPayload.isBlank()) {
            throw new IllegalArgumentException("Raw payload cannot be empty");
        }

        JsonNode rootNode = parseToJsonNode(rawPayload);
        if (rootNode == null || rootNode.isNull()) {
            throw new IllegalArgumentException("Failed to parse payload into JSON structure");
        }

        // If root is an array, take the first element if it's an object, or search inside
        if (rootNode.isArray() && !rootNode.isEmpty()) {
            rootNode = rootNode.get(0);
        }

        return extractRecord(rootNode);
    }

    private ParsedInferenceRecord extractRecord(JsonNode node) {
        // 1. Extract request ID
        String requestId = getText(node, "request_id", "requestId", "req_id", "id", "uuid", "eventId", "event_id", "conversation_id", "conversationId");
        if (requestId == null || requestId.isBlank()) {
            requestId = "req-" + UUID.randomUUID().toString();
        }

        // 2. Extract model & provider
        String model = getText(node, "model", "model_name", "modelName", "engine");
        String provider = getText(node, "provider", "provider_name", "providerName", "vendor", "source");

        // 3. Extract user ID
        Long userId = getLong(node, "user_id", "userId", "user", "customerId", "customer_id");

        // 4. Extract event_type & status & error details
        String eventType = getText(node, "event_type", "eventType", "type");
        String statusStr = getText(node, "status", "inference_status", "inferenceStatus", "state");
        Inference.InferenceStatus status = parseStatus(statusStr, eventType);

        String errorMessage = getText(node, "error_message", "errorMessage", "error", "error_description");
        String errorType = getText(node, "error_type", "errorType", "exception", "exception_type");

        // 5. Look for messages list if present
        JsonNode messagesNode = findNode(node, "conversation_history", "conversationHistory", "messages", "conversation", "history", "events", "chat");

        // If userId is still null, inspect messages for user id
        if (userId == null && messagesNode != null && messagesNode.isArray()) {
            for (JsonNode msg : messagesNode) {
                String role = getText(msg, "role");
                if ("user".equalsIgnoreCase(role)) {
                    Long msgUserId = getLong(msg, "user_id", "userId", "id");
                    if (msgUserId != null) {
                        userId = msgUserId;
                        break;
                    }
                }
            }
        }

        // If userId is still null, check conversation_id
        if (userId == null) {
            userId = getLong(node, "conversation_id", "conversationId");
        }

        // 6. Extract token counts
        Integer inputTokens = getInt(node, "input_tokens", "inputTokens", "prompt_tokens", "promptTokens");
        Integer outputTokens = getInt(node, "output_tokens", "outputTokens", "completion_tokens", "completionTokens");
        Integer totalTokens = getInt(node, "total_tokens", "totalTokens", "tokens_used", "tokensUsed");

        // If token counts are not at root, compute from messages
        if (messagesNode != null && messagesNode.isArray()) {
            int calculatedInput = 0;
            int calculatedOutput = 0;
            boolean hasCalculatedInput = false;
            boolean hasCalculatedOutput = false;

            for (JsonNode msg : messagesNode) {
                Integer tokens = getInt(msg, "tokens_used", "tokensUsed", "tokens", "token_count");
                if (tokens != null) {
                    String role = getText(msg, "role");
                    if ("assistant".equalsIgnoreCase(role) || "bot".equalsIgnoreCase(role) || "ai".equalsIgnoreCase(role) || "model".equalsIgnoreCase(role)) {
                        calculatedOutput += tokens;
                        hasCalculatedOutput = true;
                    } else {
                        calculatedInput += tokens;
                        hasCalculatedInput = true;
                    }
                }
            }

            if (inputTokens == null && hasCalculatedInput) {
                inputTokens = calculatedInput;
            }
            if (outputTokens == null && hasCalculatedOutput) {
                outputTokens = calculatedOutput;
            }
        }

        if (totalTokens == null) {
            if (inputTokens != null || outputTokens != null) {
                totalTokens = (inputTokens != null ? inputTokens : 0) + (outputTokens != null ? outputTokens : 0);
            }
        }

        // 7. Extract timestamps & latency
        Instant startedAt = parseDate(getText(node, "started_at", "startedAt", "start_time", "startTime"));
        Instant completedAt = parseDate(getText(node, "completed_at", "completedAt", "end_time", "endTime"));
        Instant rootTimestamp = parseDate(getText(node, "timestamp", "created_at", "createdAt", "time"));

        if (messagesNode != null && messagesNode.isArray() && !messagesNode.isEmpty()) {
            if (startedAt == null) {
                startedAt = parseDate(getText(messagesNode.get(0), "created_at", "createdAt", "timestamp"));
            }
            if (completedAt == null) {
                completedAt = parseDate(getText(messagesNode.get(messagesNode.size() - 1), "created_at", "createdAt", "timestamp"));
            }
        }

        if (completedAt == null && rootTimestamp != null) {
            completedAt = rootTimestamp;
        }
        if (startedAt == null && completedAt != null) {
            startedAt = completedAt;
        }

        Long latencyMs = getLong(node, "latency_ms", "latencyMs", "latency", "duration_ms", "duration");
        if (latencyMs == null && startedAt != null && completedAt != null) {
            latencyMs = Math.max(0, Duration.between(startedAt, completedAt).toMillis());
        }

        // 8. Extract input and output content for InferencePayload
        String inputContent = getText(node, "input", "prompt", "query", "user_input");
        String outputContent = getText(node, "output", "response", "completion", "result");

        if (messagesNode != null && messagesNode.isArray()) {
            List<String> userInputs = new ArrayList<>();
            List<String> assistantOutputs = new ArrayList<>();

            for (JsonNode msg : messagesNode) {
                String role = getText(msg, "role");
                String content = getText(msg, "content", "text", "message");
                if (content != null) {
                    if ("user".equalsIgnoreCase(role) || "system".equalsIgnoreCase(role) || "prompt".equalsIgnoreCase(role)) {
                        userInputs.add(content);
                    } else if ("assistant".equalsIgnoreCase(role) || "bot".equalsIgnoreCase(role) || "model".equalsIgnoreCase(role)) {
                        assistantOutputs.add(content);
                    } else {
                        userInputs.add(content);
                    }
                }
            }

            if (inputContent == null && !userInputs.isEmpty()) {
                inputContent = String.join("\n", userInputs);
            }
            if (outputContent == null && !assistantOutputs.isEmpty()) {
                outputContent = String.join("\n", assistantOutputs);
            }
            if (inputContent == null) {
                inputContent = messagesNode.toString();
            }
        }

        // For failed inference events without assistant output, record error details in output
        if ((outputContent == null || outputContent.isBlank()) && (errorMessage != null || errorType != null)) {
            if (errorType != null && errorMessage != null) {
                outputContent = errorType + ": " + errorMessage;
            } else if (errorMessage != null) {
                outputContent = errorMessage;
            } else {
                outputContent = errorType;
            }
        }

        // 9. Extract metadata & diagnostic error info
        JsonNode extraParamsNode = findNode(node, "extra_params", "extraParams", "metadata", "params", "options", "config");
        ObjectNode metadataObj = objectMapper.createObjectNode();

        if (extraParamsNode != null && extraParamsNode.isObject()) {
            metadataObj.setAll((ObjectNode) extraParamsNode);
        } else if (extraParamsNode != null && !extraParamsNode.isNull()) {
            metadataObj.set("extra_params", extraParamsNode);
        }

        if (eventType != null) metadataObj.put("event_type", eventType);
        if (errorType != null) metadataObj.put("error_type", errorType);
        if (errorMessage != null) metadataObj.put("error_message", errorMessage);
        Long conversationId = getLong(node, "conversation_id", "conversationId");
        if (conversationId != null) metadataObj.put("conversation_id", conversationId);
        String role = getText(node, "role");
        if (role != null) metadataObj.put("role", role);

        String metadataContent = metadataObj.isEmpty() ? null : metadataObj.toString();

        // Build entities
        Inference inference = Inference.builder()
                .requestId(requestId)
                .model(model)
                .provider(provider)
                .userId(userId)
                .status(status)
                .startedAt(startedAt)
                .completedAt(completedAt)
                .latencyMs(latencyMs)
                .inputTokens(inputTokens)
                .outputTokens(outputTokens)
                .totalTokens(totalTokens)
                .build();

        InferencePayload payload = InferencePayload.builder()
                .input(inputContent)
                .output(outputContent)
                .metadata(metadataContent)
                .build();

        return ParsedInferenceRecord.builder()
                .inference(inference)
                .inferencePayload(payload)
                .build();
    }

    private JsonNode parseToJsonNode(String raw) {
        try {
            return objectMapper.readTree(raw);
        } catch (Exception standardParseException) {
            log.debug("Standard JSON parse failed, attempting conversion from loose map/string format: {}", standardParseException.getMessage());
            try {
                Object looseObj = parseLooseStructure(raw);
                if (looseObj != null) {
                    return objectMapper.valueToTree(looseObj);
                }
            } catch (Exception looseParseException) {
                log.warn("Failed to parse loose format into structured node: {}", looseParseException.getMessage());
            }

            // Fallback object node containing the raw string as input
            ObjectNode fallback = objectMapper.createObjectNode();
            fallback.put("input", raw);
            fallback.put("request_id", "req-" + UUID.randomUUID().toString());
            return fallback;
        }
    }

    /**
     * Parses Java toString / Python dict / loose key=value formats into Map/List structure.
     */
    private Object parseLooseStructure(String raw) {
        String str = raw.trim();
        // If string is a fragment starting inside a list/map, auto-wrap
        if (!str.startsWith("{") && !str.startsWith("[")) {
            if (str.contains("created_at=") || str.contains("role=") || str.contains("content=")) {
                // If it looks like a list of message objects or message fragment
                if (str.contains("],") || str.contains("}")) {
                    str = "{messages=[{" + str;
                    if (!str.endsWith("}")) {
                        str = str + "}";
                    }
                } else {
                    str = "{" + str + "}";
                }
            } else {
                str = "{" + str + "}";
            }
        }
        int[] index = new int[]{0};
        return parseValue(str, index);
    }

    private Object parseValue(String s, int[] index) {
        skipWhitespace(s, index);
        if (index[0] >= s.length()) return null;

        char c = s.charAt(index[0]);
        if (c == '{') {
            return parseObject(s, index);
        } else if (c == '[') {
            return parseArray(s, index);
        } else {
            return parseScalar(s, index);
        }
    }

    private Map<String, Object> parseObject(String s, int[] index) {
        Map<String, Object> map = new LinkedHashMap<>();
        index[0]++; // skip '{'
        skipWhitespace(s, index);

        while (index[0] < s.length() && s.charAt(index[0]) != '}') {
            skipWhitespace(s, index);
            if (index[0] >= s.length() || s.charAt(index[0]) == '}') break;

            // read key
            int start = index[0];
            while (index[0] < s.length() && s.charAt(index[0]) != '=' && s.charAt(index[0]) != ':' && s.charAt(index[0]) != '}' && s.charAt(index[0]) != ',') {
                index[0]++;
            }
            String key = s.substring(start, index[0]).trim();
            if (key.startsWith("\"") && key.endsWith("\"") && key.length() >= 2) {
                key = key.substring(1, key.length() - 1);
            } else if (key.startsWith("'") && key.endsWith("'") && key.length() >= 2) {
                key = key.substring(1, key.length() - 1);
            }

            if (index[0] < s.length() && (s.charAt(index[0]) == '=' || s.charAt(index[0]) == ':')) {
                index[0]++; // skip '=' or ':'
                skipWhitespace(s, index);
                Object val = parseValue(s, index);
                if (!key.isEmpty()) {
                    map.put(key, val);
                }
            } else {
                if (!key.isEmpty()) {
                    map.put(key, null);
                }
            }

            skipWhitespace(s, index);
            if (index[0] < s.length() && s.charAt(index[0]) == ',') {
                index[0]++; // skip ','
                skipWhitespace(s, index);
            }
        }

        if (index[0] < s.length() && s.charAt(index[0]) == '}') {
            index[0]++; // skip '}'
        }
        return map;
    }

    private List<Object> parseArray(String s, int[] index) {
        List<Object> list = new ArrayList<>();
        index[0]++; // skip '['
        skipWhitespace(s, index);

        while (index[0] < s.length() && s.charAt(index[0]) != ']') {
            skipWhitespace(s, index);
            if (index[0] >= s.length() || s.charAt(index[0]) == ']') break;

            Object val = parseValue(s, index);
            list.add(val);

            skipWhitespace(s, index);
            if (index[0] < s.length() && s.charAt(index[0]) == ',') {
                index[0]++; // skip ','
                skipWhitespace(s, index);
            }
        }

        if (index[0] < s.length() && s.charAt(index[0]) == ']') {
            index[0]++; // skip ']'
        }
        return list;
    }

    private Object parseScalar(String s, int[] index) {
        int start = index[0];
        if (start >= s.length()) return null;

        char firstChar = s.charAt(start);
        boolean startsWithQuote = (firstChar == '"' || firstChar == '\'');
        char quoteChar = startsWithQuote ? firstChar : 0;

        int depthBrace = 0;
        int depthBracket = 0;
        boolean inQuotes = startsWithQuote;

        if (startsWithQuote) {
            index[0]++; // skip opening quote
            start = index[0];
            while (index[0] < s.length()) {
                char c = s.charAt(index[0]);
                if (c == quoteChar) {
                    // check for escaped quote
                    if (index[0] > 0 && s.charAt(index[0] - 1) == '\\') {
                        index[0]++;
                        continue;
                    }
                    String val = s.substring(start, index[0]);
                    index[0]++; // skip closing quote
                    return val;
                }
                index[0]++;
            }
            return s.substring(start, index[0]);
        }

        // Unquoted scalar
        while (index[0] < s.length()) {
            char c = s.charAt(index[0]);
            if (c == '{') {
                depthBrace++;
            } else if (c == '}') {
                if (depthBrace == 0) break;
                depthBrace--;
            } else if (c == '[') {
                depthBracket++;
            } else if (c == ']') {
                if (depthBracket == 0) break;
                depthBracket--;
            } else if (c == ',' && depthBrace == 0 && depthBracket == 0) {
                // Check if this comma is followed by a new key= or closing bracket
                if (isFieldOrElementSeparator(s, index[0] + 1)) {
                    break;
                }
            }
            index[0]++;
        }

        String raw = s.substring(start, index[0]).trim();

        if ("null".equalsIgnoreCase(raw)) return null;
        if ("true".equalsIgnoreCase(raw)) return Boolean.TRUE;
        if ("false".equalsIgnoreCase(raw)) return Boolean.FALSE;

        try {
            if (raw.matches("^-?\\d+$")) {
                return Long.parseLong(raw);
            } else if (raw.matches("^-?\\d+\\.\\d+$")) {
                return Double.parseDouble(raw);
            }
        } catch (Exception ignored) {
        }
        return raw;
    }

    private boolean isFieldOrElementSeparator(String s, int fromIndex) {
        int i = fromIndex;
        while (i < s.length() && Character.isWhitespace(s.charAt(i))) {
            i++;
        }
        if (i >= s.length()) return true;
        char c = s.charAt(i);
        if (c == '}' || c == ']' || c == '{' || c == '[') return true;

        // Check if next token is identifier followed by '=' or ':'
        int tokenStart = i;
        while (i < s.length() && (Character.isLetterOrDigit(s.charAt(i)) || s.charAt(i) == '_')) {
            i++;
        }
        if (i > tokenStart && i < s.length()) {
            while (i < s.length() && Character.isWhitespace(s.charAt(i))) {
                i++;
            }
            if (i < s.length() && (s.charAt(i) == '=' || s.charAt(i) == ':')) {
                return true;
            }
        }
        return false;
    }

    private void skipWhitespace(String s, int[] index) {
        while (index[0] < s.length() && Character.isWhitespace(s.charAt(index[0]))) {
            index[0]++;
        }
    }

    private Inference.InferenceStatus parseStatus(String statusStr, String eventType) {
        if (statusStr != null && !statusStr.isBlank()) {
            String clean = statusStr.trim().toUpperCase();
            return switch (clean) {
                case "SUCCESS", "COMPLETED", "OK", "200", "FINISH" -> Inference.InferenceStatus.SUCCESS;
                case "FAILED", "ERROR", "FAILURE", "500", "MESSAGE_FAILURE" -> Inference.InferenceStatus.FAILED;
                case "PROCESSING", "IN_PROGRESS", "RUNNING" -> Inference.InferenceStatus.PROCESSING;
                default -> Inference.InferenceStatus.RECEIVED;
            };
        }
        if (eventType != null && !eventType.isBlank()) {
            String cleanType = eventType.trim().toUpperCase();
            if (cleanType.contains("FAIL") || cleanType.contains("ERROR")) {
                return Inference.InferenceStatus.FAILED;
            }
        }
        return Inference.InferenceStatus.SUCCESS;
    }

    private Instant parseDate(String dateStr) {
        if (dateStr == null || dateStr.isBlank() || "null".equalsIgnoreCase(dateStr.trim())) {
            return null;
        }
        dateStr = dateStr.trim();
        try {
            if (dateStr.matches("^\\d+$")) {
                long epoch = Long.parseLong(dateStr);
                if (epoch > 100000000000L) {
                    return Instant.ofEpochMilli(epoch);
                } else {
                    return Instant.ofEpochSecond(epoch);
                }
            }
            return OffsetDateTime.parse(dateStr, DateTimeFormatter.ISO_DATE_TIME).toInstant();
        } catch (Exception e) {
            try {
                return Instant.parse(dateStr);
            } catch (Exception ex) {
                try {
                    return LocalDateTime.parse(dateStr, DateTimeFormatter.ISO_LOCAL_DATE_TIME).toInstant(ZoneOffset.UTC);
                } catch (Exception exc) {
                    log.debug("Could not parse date string '{}'", dateStr);
                    return null;
                }
            }
        }
    }

    private JsonNode findNode(JsonNode parent, String... possibleKeys) {
        if (parent == null || !parent.isObject()) {
            return null;
        }
        for (String key : possibleKeys) {
            if (parent.has(key)) {
                return parent.get(key);
            }
        }
        return null;
    }

    private String getText(JsonNode parent, String... possibleKeys) {
        JsonNode node = findNode(parent, possibleKeys);
        if (node != null && !node.isNull()) {
            if (node.isTextual()) {
                return node.asText();
            }
            return node.asText();
        }
        return null;
    }

    private Long getLong(JsonNode parent, String... possibleKeys) {
        JsonNode node = findNode(parent, possibleKeys);
        if (node != null && !node.isNull()) {
            if (node.isNumber()) {
                return Math.round(node.asDouble());
            }
            try {
                return Math.round(Double.parseDouble(node.asText().trim()));
            } catch (NumberFormatException ignored) {
            }
        }
        return null;
    }

    private Integer getInt(JsonNode parent, String... possibleKeys) {
        JsonNode node = findNode(parent, possibleKeys);
        if (node != null && !node.isNull()) {
            if (node.isNumber()) {
                return (int) Math.round(node.asDouble());
            }
            try {
                return (int) Math.round(Double.parseDouble(node.asText().trim()));
            } catch (NumberFormatException ignored) {
            }
        }
        return null;
    }
}
