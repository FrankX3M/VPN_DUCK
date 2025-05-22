# konga/Dockerfile - альтернативная версия
FROM node:14-alpine

# Устанавливаем git и другие зависимости
RUN apk add --no-cache git python3 make g++

# Создаем пользователя konga
RUN addgroup -g 1001 konga && \
    adduser -D -s /bin/sh -u 1001 -G konga konga

# Создаем директорию приложения
WORKDIR /app

# Клонируем Konga из официального репозитория
RUN git clone https://github.com/pantsel/konga.git .

# Устанавливаем зависимости
RUN npm install --production

# Меняем владельца файлов на пользователя konga
RUN chown -R konga:konga /app

USER konga

EXPOSE 1337

CMD ["npm", "start"]