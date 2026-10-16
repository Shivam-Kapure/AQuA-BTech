FROM node:20-slim

WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .

# 7860 is the Hugging Face Spaces default; set PORT to override.
ENV PORT=7860
USER node
EXPOSE 7860
CMD ["node", "server.js"]
