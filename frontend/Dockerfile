FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci --silent

COPY . .

# Vite needs the env vars at BUILD time (not runtime). Pass via --build-arg.
ARG VITE_BACKEND_URL=http://localhost:8000
ARG VITE_N8N_WEBHOOK_URL=http://localhost:5678/webhook/finance-chat
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
ENV VITE_N8N_WEBHOOK_URL=$VITE_N8N_WEBHOOK_URL

RUN npm run build

# ---- Serve with nginx ----
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 5173
CMD ["nginx", "-g", "daemon off;"]
