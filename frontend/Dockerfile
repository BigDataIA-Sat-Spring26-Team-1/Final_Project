# syntax=docker/dockerfile:1.7
# ------------------------------------------------------------------------------
# CurateAI Frontend — Cloud Run production image.
#
# Design goals:
#   1. Three-stage build. `deps` resolves node_modules once; `builder` runs
#      `next build`; `runner` ships only the Next.js standalone output so the
#      final image stays small (~150 MB vs ~800 MB with full node_modules).
#   2. Build-time baking of NEXT_PUBLIC_API_URL. Next.js inlines every
#      NEXT_PUBLIC_* variable into the client bundle during `next build` — so
#      the backend URL must be known at build time, not runtime. We accept it
#      as a --build-arg so Cloud Build can set it per environment.
#   3. Cloud Run contract — listen on $PORT (default 8080), run as non-root,
#      forward SIGTERM cleanly via exec-form CMD.
# ------------------------------------------------------------------------------

# ---------- Stage 1: deps ------------------------------------------------------
FROM node:22-slim AS deps

WORKDIR /app

# Copy only lockfile + manifest first so this layer caches across code edits.
COPY package.json package-lock.json ./

# `npm ci` is deterministic: it refuses to run if the lockfile would have to
# be modified, which catches drift before it ever reaches production.
RUN npm ci --no-audit --no-fund


# ---------- Stage 2: builder ---------------------------------------------------
FROM node:22-slim AS builder

WORKDIR /app

# Bring the resolved node_modules over from the deps stage.
COPY --from=deps /app/node_modules ./node_modules

# Copy the rest of the source. `.dockerignore` trims tests, .next, node_modules
# etc. before they hit this COPY so the build context stays tight.
COPY . .

# Accept the backend URL from the caller. NEXT_PUBLIC_API_URL is read by
# src/lib/api.ts and inlined into the client bundle — changing it after this
# point requires a rebuild. Default points at local dev for bare `docker build`.
ARG NEXT_PUBLIC_API_URL=http://localhost:8080
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Disable Next.js telemetry for reproducible, network-independent builds.
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build


# ---------- Stage 3: runner ----------------------------------------------------
FROM node:22-slim AS runner

# Non-root user — matches the backend image for consistency.
RUN groupadd --system --gid 1001 nodejs \
    && useradd  --system --uid 1001 --gid nodejs --home /app --shell /usr/sbin/nologin nextjs

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=8080 \
    HOSTNAME=0.0.0.0

# `output: 'standalone'` in next.config.ts produces this tree — it contains a
# trimmed node_modules + a minimal server.js. Public and static assets ship
# separately because the standalone copy intentionally omits them.
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 8080

# server.js is emitted by the standalone build; it reads $PORT and $HOSTNAME
# from the env vars set above. `exec` keeps Node as PID 1 so Cloud Run's
# SIGTERM during draining lands on Node directly.
CMD ["node", "server.js"]
