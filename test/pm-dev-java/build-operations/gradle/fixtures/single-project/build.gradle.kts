plugins {
    `java-library`
}

group = "com.example"
version = "1.0.0"

repositories {
    mavenCentral()
}

dependencies {
    implementation("org.slf4j:slf4j-api:2.0.9")
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.0")
}
