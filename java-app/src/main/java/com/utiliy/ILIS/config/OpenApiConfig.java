package com.utiliy.ILIS.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.servers.Server;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI ilisOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("Inference Logging & Ingestion System (ILIS) API")
                        .description("High-performance event collection, LLM inference logging ingestion pipeline, and real-time analytics dashboard API.")
                        .version("1.0.0")
                        .contact(new Contact()
                                .name("ILIS Engineering Team")
                                .email("support@ilis.local"))
                        .license(new License()
                                .name("Apache 2.0")
                                .url("https://www.apache.org/licenses/LICENSE-2.0")))
                .servers(List.of(
                        new Server().url("/ilis").description("Current Server Context")
                ));
    }
}
