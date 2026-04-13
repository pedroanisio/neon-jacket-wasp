# ── Build stage ──
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json tsconfig.json ./
RUN npm install

COPY src/ src/
RUN npx tsc

# ── Serve stage ──
FROM node:22-alpine

WORKDIR /app

ARG APP_PORT=3000
ENV APP_PORT=${APP_PORT}

RUN npm install -g serve@14

COPY --from=build /app/dist/ dist/
COPY index.html ./

EXPOSE ${APP_PORT}

CMD ["sh", "-c", "serve . -l ${APP_PORT} -s"]
