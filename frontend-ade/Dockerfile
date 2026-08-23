FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_ADE_UI_VERSION=""
ARG NEXT_PUBLIC_ADE_UI_BUILD=""
ENV NEXT_PUBLIC_ADE_UI_VERSION=${NEXT_PUBLIC_ADE_UI_VERSION}
ENV NEXT_PUBLIC_ADE_UI_BUILD=${NEXT_PUBLIC_ADE_UI_BUILD}
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
# This is read by the dynamic Next route at request time, never bundled for browsers.
ENV AGENT_PLATFORM_API_BASE_URL=http://agent_platform_api:8284
EXPOSE 3000
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
CMD ["node", "server.js"]
