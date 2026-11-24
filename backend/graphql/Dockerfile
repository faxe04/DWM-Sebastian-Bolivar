FROM node:24-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY server.js services.js limits.js ./
USER node
ENV HOST=0.0.0.0
CMD ["node", "server.js"]
