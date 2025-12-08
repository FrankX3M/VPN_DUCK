FROM pantsel/konga:0.14.9

USER root

RUN npm cache clean --force
RUN rm -rf /app/node_modules/sails-postgresql

WORKDIR /app

RUN npm install sails-postgresql@1.0.2 --save --no-optional

# Создаем startup скрипт с sh вместо bash
RUN echo '#!/bin/sh\ncd /app\nnpm start' > /start.sh && chmod +x /start.sh

USER konga

CMD ["/bin/sh", "/start.sh"]
