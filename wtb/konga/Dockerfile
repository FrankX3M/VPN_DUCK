# konga/Dockerfile
FROM pantsel/konga:0.14.9

# Переключаемся на root для установки пакетов
USER root

# Обновляем npm и Node.js зависимости
RUN npm cache clean --force

# Удаляем проблемную версию sails-postgresql
RUN rm -rf /app/node_modules/sails-postgresql

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем совместимую версию sails-postgresql
RUN npm install sails-postgresql@1.0.2 --save --no-optional

# Возвращаемся к пользователю konga
USER konga

# Запускаем konga
CMD ["npm", "start"]
