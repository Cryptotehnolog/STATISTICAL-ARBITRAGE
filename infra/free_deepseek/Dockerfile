FROM node:22-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/ForgetMeAI/FreeDeepseekAPI.git /app

WORKDIR /app

ENV HOST=0.0.0.0
ENV PORT=9655
ENV NON_INTERACTIVE=1
ENV SKIP_ACCOUNT_MENU=1
ENV DEEPSEEK_AUTH_PATH=/runtime/deepseek-auth.json

VOLUME ["/runtime"]

EXPOSE 9655

CMD ["npm", "start"]
