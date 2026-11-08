# ==============================================================================
# Vedantu Online Coding Assessment Platform - Next.js Production Dockerfile
# Multi-stage build for minimal image footprint and hardened container security
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Base image definition
# ------------------------------------------------------------------------------
FROM node:22-alpine AS base
WORKDIR /app

# Install libc6-compat for compatibility with Alpine Linux musl libc
RUN apk add --no-cache libc6-compat

# Avoid OpenSSL 3.x AES-GCM stream cipher acceleration bug in containerized musl environments
ENV OPENSSL_ia32cap="~0x200000200000000"

# ------------------------------------------------------------------------------
# 2. Dependencies installation stage (reproducible with npm ci)
# ------------------------------------------------------------------------------
FROM base AS deps
WORKDIR /app

# Copy dependency manifests
COPY package.json package-lock.json ./

# Install production and development dependencies deterministically
RUN npm ci

# ------------------------------------------------------------------------------
# 3. Production build stage
# ------------------------------------------------------------------------------
FROM base AS builder
WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy full frontend application source
COPY . .

# Build arguments for public client environment variables
ARG NEXT_PUBLIC_API_BASE_URL=/api/v1
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

# Optimize build execution
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Compile Next.js standalone bundle with Turbopack
RUN npm run build

# ------------------------------------------------------------------------------
# 4. Production runner stage (minimal, secure, non-root)
# ------------------------------------------------------------------------------
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Create dedicated non-root system user and group
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Prepare .next directory with correct ownership for cache writes
RUN mkdir .next && chown nextjs:nodejs .next

# Copy public static assets and standalone server output
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Switch to non-root user
USER nextjs

# Expose standard Next.js port
EXPOSE 3000

# Health check using built-in busybox wget
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:3000/ || exit 1

# Start self-contained standalone server
CMD ["node", "server.js"]
