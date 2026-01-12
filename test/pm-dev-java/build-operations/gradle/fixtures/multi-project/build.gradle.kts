plugins {
    `java-library` apply false
}

subprojects {
    apply(plugin = "java-library")

    repositories {
        mavenCentral()
    }
}
