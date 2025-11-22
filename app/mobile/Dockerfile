FROM node:18-alpine

WORKDIR /app

# copy only package files first for better caching
COPY app/mobile/package*.json ./
RUN npm ci

# copy source
COPY app/mobile ./

# Metro bundler and Expo/DevServer ports
EXPOSE 8081 19000

CMD ["npm", "start"]
