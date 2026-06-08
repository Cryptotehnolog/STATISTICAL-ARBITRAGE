FROM node:20-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates git chromium fonts-liberation libatk-bridge2.0-0 libatk1.0-0 \
        libcups2 libdrm2 libgbm1 libnss3 libxcomposite1 libxdamage1 libxrandr2 \
        xdg-utils \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/ForgetMeAI/FreeQwenApi.git /app

WORKDIR /app

RUN npm install --omit=dev --no-audit --no-fund

ENV NODE_ENV=production
ENV CHROME_PATH=/usr/bin/chromium
ENV PORT=3264
ENV HOST=0.0.0.0
ENV SKIP_ACCOUNT_MENU=true
ENV NON_INTERACTIVE=true

RUN mkdir -p /app/session /app/logs /app/uploads

VOLUME ["/app/session", "/app/logs", "/app/uploads"]

EXPOSE 3264

CMD ["node", "index.js"]
