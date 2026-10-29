# syntax=docker/dockerfile:1
# spring-petclinic publishes no image; this one is ours (kept current by the dockerfile ecosystem).
FROM eclipse-temurin:17-jdk-noble@sha256:78dde986267ae7cac62fe7ef624c2a5cee2036b6822933d39fd3870618b91526 AS build
WORKDIR /src
COPY . .
# collectReachabilityMetadata (GraalVM native-image metadata, downloaded from GitHub) isn't needed for a JVM image
RUN --mount=type=cache,target=/root/.gradle \
    ./gradlew --no-daemon bootJar -x test -x collectReachabilityMetadata && cp build/libs/spring-petclinic-*.jar /tmp/app.jar

FROM eclipse-temurin:17-jre-noble@sha256:b3e1d0486f09293b2455aed02d396d4b6b5ea9b0e8c7c065c297cfef453b0116
COPY --from=build /tmp/app.jar /app/app.jar
USER 1000:1000
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
