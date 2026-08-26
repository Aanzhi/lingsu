ARG NODE_IMAGE=node:22-alpine
ARG NGINX_IMAGE=nginx:1.27-alpine
ARG NPM_REGISTRY=https://registry.npmmirror.com
FROM ${NODE_IMAGE} AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm config set registry "${NPM_REGISTRY}" && npm ci
COPY frontend/ ./
RUN npm run build

FROM ${NGINX_IMAGE}
COPY infra/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-build /frontend/dist /usr/share/nginx/html
EXPOSE 80
