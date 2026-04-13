# ── Build stage ──
FROM node:22-alpine AS build

WORKDIR /app

# Copy shell package files
COPY packages/shell/package.json packages/shell/
RUN cd packages/shell && npm install

# Copy frontend sources (the JSX components)
COPY frontend/ frontend/

# Copy shell app sources + config
COPY packages/shell/ packages/shell/

# Build the Vite production bundle
RUN cd packages/shell && npx vite build

# ── Serve stage ──
FROM node:22-alpine

WORKDIR /app

ARG APP_PORT=4000
ENV APP_PORT=${APP_PORT}

RUN npm install -g serve@14

COPY --from=build /app/packages/shell/dist/ dist/

EXPOSE ${APP_PORT}

CMD ["sh", "-c", "serve dist -l ${APP_PORT} -s"]
