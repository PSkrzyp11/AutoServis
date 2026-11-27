FROM node:24-alpine AS base
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm install --global pnpm@12.23.0
WORKDIR /app

FROM base AS dependencies
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM dependencies AS development
COPY . .
EXPOSE 3000
CMD ["pnpm", "dev", "--hostname", "0.0.0.0"]

FROM dependencies AS build
COPY . .
ARG BACKEND_INTERNAL_URL=http://backend:8000
ENV BACKEND_INTERNAL_URL=${BACKEND_INTERNAL_URL}
RUN pnpm build

FROM node:24-alpine AS production
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
WORKDIR /app
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
