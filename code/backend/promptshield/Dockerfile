# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Build — compile the Spring Boot JAR
# ─────────────────────────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jdk AS builder

WORKDIR /app

# Copy Maven wrapper and dependency manifest first for better layer caching
COPY .mvn/ .mvn/
COPY mvnw pom.xml ./

RUN chmod +x mvnw
# Download all dependencies in a separate layer so they are only re-downloaded
# when pom.xml changes, not on every source code change.
RUN ./mvnw dependency:go-offline -B

# Copy application source
COPY src ./src

# Build the fat JAR — skip tests (they run in CI, not Docker build)
RUN ./mvnw clean package -DskipTests -B

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime — lightweight JRE image
# ─────────────────────────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jre

# Run as a dedicated non-root user for security
RUN groupadd --system --gid 1001 promptshield && \
    useradd --system --uid 1001 --gid promptshield --no-create-home promptshield

WORKDIR /app

COPY --from=builder /app/target/*.jar app.jar

# Transfer ownership to non-root user
RUN chown promptshield:promptshield app.jar
USER promptshield

EXPOSE 8080

# Health check: Render and Docker Compose both use this.
# Calls the Spring Boot /api/v1/health endpoint added in HealthController.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -sf http://localhost:${PORT:-8080}/api/v1/health || exit 1

# JVM flags tuned for small cloud instances (Render free: 512MB RAM):
#   -XX:+UseContainerSupport    — read cgroup memory limits automatically
#   -XX:MaxRAMPercentage=75.0   — cap heap at 75% of available container RAM
#   -XX:+ExitOnOutOfMemoryError — crash fast rather than thrashing
#   -Djava.security.egd=...     — faster startup using /dev/urandom
# Spring Boot automatically reads server.port=${PORT:8080} from application.properties.
ENTRYPOINT ["java", \
  "-XX:+UseContainerSupport", \
  "-XX:MaxRAMPercentage=75.0", \
  "-XX:+ExitOnOutOfMemoryError", \
  "-Djava.security.egd=file:/dev/./urandom", \
  "-jar", "app.jar"]