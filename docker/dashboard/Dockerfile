# docker/dashboard/Dockerfile
# Self-building Next.js image (ADR-081; cleanroom fix F19).
# Stage 1 runs `npm ci && npm run build` inside the container — a fresh clone
# needs no host Node and no pre-built .next/ (which is gitignored and only
# ever existed on the maintainer's machine). Stage 2 is the slim runtime.
# Context: src/dashboard/ (see docker-compose.yml); .dockerignore keeps
# host node_modules/.next out of the build context.
# Maintainer flow (make dashboard-deploy) is unchanged: it rsyncs the context
# and runs `docker compose build lex-dashboard` — the build now happens here.

FROM node:20-alpine AS builder
WORKDIR /app

# Dependency layer first — caches across rebuilds while package-lock is stable
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine
RUN addgroup -S app && adduser -S app -G app
WORKDIR /app

# Production dependencies only
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# Built output and static assets from the builder stage
COPY --from=builder /app/.next ./.next
COPY public ./public
COPY next.config.js ./

USER app
EXPOSE 3000
CMD ["npx", "next", "start", "-p", "3000"]
