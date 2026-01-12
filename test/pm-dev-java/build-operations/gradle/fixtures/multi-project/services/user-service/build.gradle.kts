plugins {
    `java-library`
}

group = "com.example.services"
version = "1.0.0"

dependencies {
    implementation(project(":core"))
    implementation(project(":services:auth-service"))
    implementation("org.springframework:spring-context:6.1.0")
}
