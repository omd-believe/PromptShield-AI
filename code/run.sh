#!/usr/bin/env bash
# ==============================================================================
# PromptShield-AI — Unified Single Command Launcher
# ==============================================================================
# Usage:
#   ./run.sh          - Start all services (AI Service, Backend, Frontend) with live dashboard
#   ./run.sh start    - Start all services in foreground (Ctrl+C cleanly stops all)
#   ./run.sh start -d - Start all services in background (daemon mode)
#   ./run.sh stop     - Stop all running services
#   ./run.sh restart  - Restart all services
#   ./run.sh status   - Check health and port status of all services
#   ./run.sh logs     - View and tail combined logs (or ./run.sh logs [ai|backend|frontend])
#   ./run.sh test     - Run full test suite across AI service, backend, and frontend
# ==============================================================================

set -eo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_DIR="$ROOT_DIR/ai-service"
BACKEND_DIR="$ROOT_DIR/backend/promptshield"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOG_DIR="$ROOT_DIR/.logs"
PID_DIR="$ROOT_DIR/.pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

AI_PORT=8000
BACKEND_PORT=8080
FRONTEND_PORT=5173
POSTGRES_PORT=5433

# Load environment configuration
if [[ -f "$ROOT_DIR/.env" ]]; then
    # shellcheck disable=SC1091
    source "$ROOT_DIR/.env"
elif [[ -f "$ROOT_DIR/docker/.env" ]]; then
    # shellcheck disable=SC1091
    source "$ROOT_DIR/docker/.env"
fi

# Fallback defaults for local development
export POSTGRES_PORT="${POSTGRES_PORT:-5433}"
export POSTGRES_DB="${POSTGRES_DB:-promptshield_db}"
export POSTGRES_USER="${POSTGRES_USER:-postgres}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres_local_dev_only}"
export SPRING_DATASOURCE_URL="${SPRING_DATASOURCE_URL:-jdbc:postgresql://localhost:${POSTGRES_PORT}/${POSTGRES_DB}}"
export SPRING_DATASOURCE_USERNAME="${SPRING_DATASOURCE_USERNAME:-$POSTGRES_USER}"
export SPRING_DATASOURCE_PASSWORD="${SPRING_DATASOURCE_PASSWORD:-$POSTGRES_PASSWORD}"
export JWT_SECRET="${JWT_SECRET:-PromptShieldDevJwtSecretAtLeast32BytesLong!}"
export JWT_EXPIRATION="${JWT_EXPIRATION:-86400000}"
export AI_SERVICE_URL="${AI_SERVICE_URL:-http://localhost:${AI_PORT}}"
export AI_SERVICE_API_KEY="${AI_SERVICE_API_KEY:-}"
export COMPRESSION_ENGINE="${COMPRESSION_ENGINE:-auto}"
export LLMLINGUA_ENABLED="${LLMLINGUA_ENABLED:-true}"
export LLMLINGUA_USE_ONLINE_DOWNLOAD="${LLMLINGUA_USE_ONLINE_DOWNLOAD:-true}"

# Formatting & colors
BOLD="\033[1m"
GREEN="\033[32m"
BLUE="\033[34m"
CYAN="\033[36m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"

log_info() { echo -e "${CYAN}[INFO]${RESET} $*"; }
log_ok()   { echo -e "${GREEN}[ OK ]${RESET} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${RESET} $*"; }
log_err()  { echo -e "${RED}[ERR ]${RESET} $*"; }

is_port_in_use() {
    local port="$1"
    ss -tulpn 2>/dev/null | grep -q ":${port} " || lsof -i ":${port}" &>/dev/null
}

kill_port_process() {
    local port="$1"
    local name="$2"
    if is_port_in_use "$port"; then
        log_warn "Stopping existing process on port $port ($name)..."
        local pids
        pids=$(lsof -ti ":${port}" 2>/dev/null || fuser "${port}/tcp" 2>/dev/null || true)
        if [[ -n "$pids" ]]; then
            # shellcheck disable=SC2086
            kill -15 $pids 2>/dev/null || true
            sleep 1
            # shellcheck disable=SC2086
            kill -9 $pids 2>/dev/null || true
        fi
    fi
}

check_prerequisites() {
    log_info "Verifying prerequisites..."

    if ! command -v curl &>/dev/null; then
        log_err "curl is required but not installed."
        exit 1
    fi

    # Ensure PostgreSQL is running on POSTGRES_PORT
    if ! is_port_in_use "$POSTGRES_PORT"; then
        log_warn "PostgreSQL is not listening on port $POSTGRES_PORT. Attempting to start container..."
        local started=false

        if command -v podman &>/dev/null; then
            if podman container exists promptshield-postgres 2>/dev/null; then
                log_info "Starting existing podman container 'promptshield-postgres'..."
                podman start promptshield-postgres >/dev/null 2>&1 || true
                started=true
            fi
        fi

        if [[ "$started" == "false" ]] && command -v docker &>/dev/null; then
            if docker inspect promptshield-postgres >/dev/null 2>&1; then
                log_info "Starting existing docker container 'promptshield-postgres'..."
                docker start promptshield-postgres >/dev/null 2>&1 || true
                started=true
            fi
        fi

        # If not started, try creating container with podman or docker
        if [[ "$started" == "false" ]]; then
            local ctool=""
            if command -v podman &>/dev/null; then
                ctool="podman"
            elif command -v docker &>/dev/null; then
                ctool="docker"
            fi

            if [[ -n "$ctool" ]]; then
                log_info "Creating and starting '$ctool' container 'promptshield-postgres' on port $POSTGRES_PORT..."
                $ctool run -d --name promptshield-postgres \
                    --restart unless-stopped \
                    -p 127.0.0.1:${POSTGRES_PORT}:5432 \
                    -e POSTGRES_DB="${POSTGRES_DB:-promptshield_db}" \
                    -e POSTGRES_USER="${POSTGRES_USER:-postgres}" \
                    -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres_local_dev_only}" \
                    -v promptshield-postgres-data:/var/lib/postgresql/data \
                    docker.io/library/postgres:17-alpine >/dev/null 2>&1 || true
            fi
        fi

        # Wait for port to become active
        local count=0
        while ! is_port_in_use "$POSTGRES_PORT"; do
            sleep 1
            count=$((count + 1))
            if [[ $count -ge 15 ]]; then
                break
            fi
        done
    fi

    if is_port_in_use "$POSTGRES_PORT"; then
        log_ok "PostgreSQL port active ($POSTGRES_PORT)."
    else
        log_err "PostgreSQL is not listening on port $POSTGRES_PORT."
        log_err "Please ensure 'promptshield-postgres' container is running (podman start promptshield-postgres)."
        exit 1
    fi

    # Check AI Service venv
    if [[ ! -f "$AI_DIR/.venv/bin/uvicorn" ]]; then
        log_err "AI Service virtual environment missing ($AI_DIR/.venv/bin/uvicorn)."
        log_info "Create it with: cd ai-service && python -m venv .venv && .venv/bin/pip install -r requirements.txt"
        exit 1
    fi

    # Check Maven Wrapper
    if [[ ! -f "$BACKEND_DIR/mvnw" ]]; then
        log_err "Backend Maven wrapper missing ($BACKEND_DIR/mvnw)."
        exit 1
    fi

    # Check Frontend node_modules
    if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
        log_warn "Frontend node_modules missing. Running npm install..."
        (cd "$FRONTEND_DIR" && npm install)
    fi

    log_ok "All prerequisites verified."
}

stop_all() {
    log_info "Stopping PromptShield services..."
    
    # Read saved PIDs if available
    for pidfile in "$PID_DIR"/*.pid; do
        if [[ -f "$pidfile" ]]; then
            local pid
            pid=$(cat "$pidfile" 2>/dev/null || true)
            if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
                kill -15 "$pid" 2>/dev/null || true
            fi
            rm -f "$pidfile"
        fi
    done

    # Clean up by port if any process lingers
    kill_port_process "$FRONTEND_PORT" "Frontend (Vite)"
    kill_port_process "$BACKEND_PORT" "Backend (Spring Boot)"
    kill_port_process "$AI_PORT" "AI Service (FastAPI)"

    log_ok "All PromptShield services stopped."
}

wait_for_service() {
    local name="$1"
    local url="$2"
    local max_wait="$3"
    local count=0

    echo -n "Waiting for $name to be ready"
    while ! curl -s -f -m 2 "$url" &>/dev/null; do
        echo -n "."
        sleep 1
        count=$((count + 1))
        if [[ $count -ge $max_wait ]]; then
            echo ""
            log_err "$name failed to become healthy within $max_wait seconds."
            return 1
        fi
    done
    echo ""
    log_ok "$name is ready!"
    return 0
}

start_services() {
    local daemon_mode="${1:-false}"

    check_prerequisites

    log_info "Stopping any conflicting stale service processes..."
    kill_port_process "$AI_PORT" "AI Service"
    kill_port_process "$BACKEND_PORT" "Backend"
    kill_port_process "$FRONTEND_PORT" "Frontend"

    # 1. Start AI Service (FastAPI)
    log_info "Starting AI Service (FastAPI) on port $AI_PORT..."
    (
        cd "$AI_DIR"
        nohup env \
            COMPRESSION_ENGINE="$COMPRESSION_ENGINE" \
            LLMLINGUA_ENABLED="$LLMLINGUA_ENABLED" \
            LLMLINGUA_USE_ONLINE_DOWNLOAD="$LLMLINGUA_USE_ONLINE_DOWNLOAD" \
            .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$AI_PORT" \
            > "$LOG_DIR/ai-service.log" 2>&1 &
        echo $! > "$PID_DIR/ai-service.pid"
    )
    disown -a 2>/dev/null || true

    wait_for_service "AI Service" "http://localhost:${AI_PORT}/health" 30

    # 2. Start Backend (Spring Boot)
    log_info "Starting Backend (Spring Boot) on port $BACKEND_PORT..."
    (
        cd "$BACKEND_DIR"
        nohup env \
            SPRING_DATASOURCE_URL="$SPRING_DATASOURCE_URL" \
            SPRING_DATASOURCE_USERNAME="$SPRING_DATASOURCE_USERNAME" \
            SPRING_DATASOURCE_PASSWORD="$SPRING_DATASOURCE_PASSWORD" \
            JWT_SECRET="$JWT_SECRET" \
            JWT_EXPIRATION="$JWT_EXPIRATION" \
            AI_SERVICE_URL="$AI_SERVICE_URL" \
            ./mvnw spring-boot:run \
            > "$LOG_DIR/backend.log" 2>&1 &
        echo $! > "$PID_DIR/backend.pid"
    )
    disown -a 2>/dev/null || true

    wait_for_service "Spring Boot Backend" "http://localhost:${BACKEND_PORT}/v3/api-docs" 60

    # 3. Start Frontend (Vite React)
    log_info "Starting Frontend (Vite) on port $FRONTEND_PORT..."
    (
        cd "$FRONTEND_DIR"
        nohup npm run dev \
            > "$LOG_DIR/frontend.log" 2>&1 &
        echo $! > "$PID_DIR/frontend.pid"
    )
    disown -a 2>/dev/null || true

    wait_for_service "Frontend UI" "http://localhost:${FRONTEND_PORT}" 20

    print_dashboard

    if [[ "$daemon_mode" == "true" ]]; then
        log_info "Services are running in background daemon mode."
        log_info "Use './run.sh status' to inspect or './run.sh stop' to shut down."
        log_info "Use './run.sh logs' to follow live logs."
    else
        echo -e "${YELLOW}Press [Ctrl+C] to stop all services cleanly.${RESET}"
        trap 'echo ""; log_info "Shutdown signal received..."; stop_all; exit 0' INT TERM
        
        # Follow unified logs in foreground
        tail -n 20 -f "$LOG_DIR/ai-service.log" "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
    fi
}

print_dashboard() {
    echo ""
    echo -e "${BOLD}${GREEN}====================================================================${RESET}"
    echo -e "${BOLD}${GREEN}            🛡️  PromptShield-AI System is Active  🛡️                 ${RESET}"
    echo -e "${BOLD}${GREEN}====================================================================${RESET}"
    echo -e "  ${BOLD}Application URLs:${RESET}"
    echo -e "  🌐 ${CYAN}Frontend UI:${RESET}           ${BOLD}http://localhost:${FRONTEND_PORT}${RESET}"
    echo -e "  ⚙️  ${CYAN}Backend API:${RESET}           ${BOLD}http://localhost:${BACKEND_PORT}${RESET}"
    echo -e "  📖 ${CYAN}Swagger UI Docs:${RESET}       ${BOLD}http://localhost:${BACKEND_PORT}/swagger-ui.html${RESET}"
    echo -e "  🧠 ${CYAN}AI Microservice:${RESET}       ${BOLD}http://localhost:${AI_PORT}${RESET}"
    echo -e "  📑 ${CYAN}AI OpenAPI Docs:${RESET}       ${BOLD}http://localhost:${AI_PORT}/docs${RESET}"
    echo ""
    echo -e "  ${BOLD}Logs Directory:${RESET}           ${BLUE}$LOG_DIR${RESET}"
    echo -e "${BOLD}${GREEN}====================================================================${RESET}"
    echo ""
}

status_all() {
    echo -e "${BOLD}PromptShield-AI Service Status:${RESET}"
    echo "------------------------------------------------------------"
    printf "%-20s %-10s %-15s %-15s\n" "SERVICE" "PORT" "STATUS" "HEALTH"
    echo "------------------------------------------------------------"

    # PostgreSQL
    local pg_status="STOPPED"
    local pg_health="DOWN"
    if is_port_in_use "$POSTGRES_PORT"; then
        pg_status="RUNNING"
        pg_health="LISTENING"
    fi
    printf "%-20s %-10s %-15s %-15s\n" "PostgreSQL" "$POSTGRES_PORT" "$pg_status" "$pg_health"

    # AI Service
    local ai_status="STOPPED"
    local ai_health="DOWN"
    if is_port_in_use "$AI_PORT"; then
        ai_status="RUNNING"
        if curl -s -f "http://localhost:${AI_PORT}/health" &>/dev/null; then
            ai_health="HEALTHY (200)"
        else
            ai_health="UNHEALTHY"
        fi
    fi
    printf "%-20s %-10s %-15s %-15s\n" "AI Service" "$AI_PORT" "$ai_status" "$ai_health"

    # Backend
    local be_status="STOPPED"
    local be_health="DOWN"
    if is_port_in_use "$BACKEND_PORT"; then
        be_status="RUNNING"
        if curl -s -f "http://localhost:${BACKEND_PORT}/v3/api-docs" &>/dev/null; then
            be_health="HEALTHY (200)"
        else
            be_health="STARTING"
        fi
    fi
    printf "%-20s %-10s %-15s %-15s\n" "Backend API" "$BACKEND_PORT" "$be_status" "$be_health"

    # Frontend
    local fe_status="STOPPED"
    local fe_health="DOWN"
    if is_port_in_use "$FRONTEND_PORT"; then
        fe_status="RUNNING"
        if curl -s -f "http://localhost:${FRONTEND_PORT}" &>/dev/null; then
            fe_health="HEALTHY (200)"
        else
            fe_health="UNHEALTHY"
        fi
    fi
    printf "%-20s %-10s %-15s %-15s\n" "Frontend UI" "$FRONTEND_PORT" "$fe_status" "$fe_health"
    echo "------------------------------------------------------------"
}

view_logs() {
    local target="${1:-all}"
    case "$target" in
        ai|ai-service)
            tail -n 50 -f "$LOG_DIR/ai-service.log"
            ;;
        be|backend)
            tail -n 50 -f "$LOG_DIR/backend.log"
            ;;
        fe|frontend)
            tail -n 50 -f "$LOG_DIR/frontend.log"
            ;;
        all|*)
            tail -n 25 -f "$LOG_DIR/ai-service.log" "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
            ;;
    esac
}

run_tests() {
    log_info "Running AI Service pytest suite..."
    (cd "$AI_DIR" && .venv/bin/pytest tests/ -v)

    log_info "Running Spring Boot test suite..."
    (cd "$BACKEND_DIR" && ./mvnw test)

    log_info "Verifying Frontend production build..."
    (cd "$FRONTEND_DIR" && npm run build)

    log_ok "All test suites executed successfully!"
}

# ── Main Entrypoint ────────────────────────────────────────────────────────────
ACTION="${1:-start}"
shift || true

case "$ACTION" in
    start|dev)
        DAEMON="false"
        if [[ "${1:-}" == "-d" || "${1:-}" == "--daemon" ]]; then
            DAEMON="true"
        fi
        start_services "$DAEMON"
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 2
        start_services "false"
        ;;
    status)
        status_all
        ;;
    logs)
        view_logs "${1:-all}"
        ;;
    test|tests)
        run_tests
        ;;
    help|--help|-h)
        echo "Usage: ./run.sh [command]"
        echo ""
        echo "Commands:"
        echo "  ./run.sh          Start all services in interactive foreground mode (Ctrl+C cleanly stops)"
        echo "  ./run.sh start -d Start all services as background daemons"
        echo "  ./run.sh stop     Stop all running services"
        echo "  ./run.sh restart  Clean restart of all services"
        echo "  ./run.sh status   View status table and health of all components"
        echo "  ./run.sh logs     Tail combined logs (or ./run.sh logs [ai|backend|frontend])"
        echo "  ./run.sh test     Run full automated test suites across all 3 stacks"
        ;;
    *)
        log_err "Unknown command: '$ACTION'. Use './run.sh help' for options."
        exit 1
        ;;
esac
