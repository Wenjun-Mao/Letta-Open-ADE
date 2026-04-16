FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install

FROM node:20-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_ADE_UI_VERSION=""
ARG NEXT_PUBLIC_ADE_UI_BUILD=""
ENV NEXT_PUBLIC_ADE_UI_VERSION=${NEXT_PUBLIC_ADE_UI_VERSION}
ENV NEXT_PUBLIC_ADE_UI_BUILD=${NEXT_PUBLIC_ADE_UI_BUILD}
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
CMD ["node", "server.js"]
