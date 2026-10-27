FROM node:22-alpine AS build

RUN corepack enable && corepack prepare pnpm@10.30.3 --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/shared-types/package.json packages/shared-types/package.json
RUN pnpm install --frozen-lockfile

COPY apps/web apps/web
COPY packages/shared-types packages/shared-types
RUN pnpm --filter @my-agent/web build

FROM nginx:1.27-alpine

COPY deploy/nginx/web.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/web/dist /usr/share/nginx/html

EXPOSE 80
