FROM node:26-slim@sha256:3a771f83944bb763050c23c0225c260638c4b7899e7a72485ef75e5e570499e5 AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund

COPY . .
RUN npm run check && npm run build

FROM nginx:alpine@sha256:62ff2089abf5a9ed33bd232895bef5e22f7bb4b200675cec49a5ebc48e3d4ac8

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
