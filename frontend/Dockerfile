FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=/api
ARG VITE_OPERATION_TIMEZONE=America/Sao_Paulo
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_OPERATION_TIMEZONE=${VITE_OPERATION_TIMEZONE}

RUN npm run build

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
