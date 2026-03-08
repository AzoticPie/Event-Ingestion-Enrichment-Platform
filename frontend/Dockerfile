FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .

ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

ARG VITE_DEFAULT_INGEST_KEY=
ENV VITE_DEFAULT_INGEST_KEY=${VITE_DEFAULT_INGEST_KEY}

RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=20s --timeout=3s --retries=3 CMD wget -q -O - http://localhost/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]

