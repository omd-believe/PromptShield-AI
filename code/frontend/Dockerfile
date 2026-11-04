
# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Build — compiles the Vite/React app into static files
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer-cached unless package files change)
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# VITE_API_BASE_URL is a build-time ARG because Vite inlines env vars at build.
# Inside the Docker network, frontend talks to the "backend" service by name.
ARG VITE_API_BASE_URL=http://localhost:8080/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Serve — lightweight nginx to serve the compiled static files
# ─────────────────────────────────────────────────────────────────────────────
FROM nginx:stable-alpine

# Remove default nginx page
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config for React Router (SPA fallback to index.html)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
