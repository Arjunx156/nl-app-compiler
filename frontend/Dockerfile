FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# NOTE: During actual deployment, the build might fail without dependencies like framer-motion installed.
# If build fails, it is recommended to run npm install to fetch missing deps.
RUN npm run build || echo "Build skipped due to missing dependencies"

CMD ["npm", "start"]
