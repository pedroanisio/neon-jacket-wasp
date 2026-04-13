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

RUN npm install -g serve@14

COPY --from=build /app/dist/ dist/
COPY index.html ./

EXPOSE 3000

CMD ["serve", ".", "-l", "3000", "-s"]
