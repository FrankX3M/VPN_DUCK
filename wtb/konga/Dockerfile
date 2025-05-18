FROM pantsel/konga:0.14.9

# Удалите проблемную версию sails-postgresql
RUN rm -rf /app/node_modules/sails-postgresql

# Установите совместимую версию
WORKDIR /app
RUN npm install sails-postgresql@1.0.2-10

# Запустите konga
CMD ["npm", "start"]
