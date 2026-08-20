package com.utiliy.ILIS.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI ilisOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("ILIS API")
                        .version("1.0.0"));
    }
}
