FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_ADE_WEB_VERSION=""
ARG NEXT_PUBLIC_ADE_WEB_BUILD=""
ENV NEXT_PUBLIC_ADE_WEB_VERSION=${NEXT_PUBLIC_ADE_WEB_VERSION}
ENV NEXT_PUBLIC_ADE_WEB_BUILD=${NEXT_PUBLIC_ADE_WEB_BUILD}
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
# This is read by the dynamic Next route at request time, never bundled for browsers.
ENV ADE_API_BASE_URL=http://ade-api:8000
ENV ADE_NATIVE_API_BASE_URL=http://ade-native-api:8000
EXPOSE 3000
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
CMD ["node", "server.js"]
