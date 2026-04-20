# Use Node.js latest stable (v20+)
FROM node:22-slim AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy application files
COPY . .

# Build the Next.js application
# Note: Ensure PUBLIC_NEXT_API_URL or similar vars are passed if needed at build time
RUN npm run build

# Stage 2: Serve the application
FROM node:22-slim AS runner

WORKDIR /app

ENV NODE_ENV=production

# Copy necessary files from builder
COPY --from=builder /app/next.config.ts ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000

# Start production server
CMD ["npm", "run", "start"]
