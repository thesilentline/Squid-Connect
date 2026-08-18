package com.utiliy.ILIS;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@EnableScheduling
@SpringBootApplication
public class IlisApplication {

	public static void main(String[] args) {
		SpringApplication.run(IlisApplication.class, args);
	}

}
