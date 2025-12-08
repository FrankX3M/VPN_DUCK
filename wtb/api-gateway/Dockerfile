FROM kong:3.9-ubuntu

# Установка пакетов с фиксированными DNS
RUN echo "nameserver [jg:ip_address_192]" > /etc/resolv.conf &&     echo "nameserver [jg:ip_address_193]" >> /etc/resolv.conf &&     apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout="10" &&     apt-get install -y --no-install-recommends curl postgresql-client jq &&     rm -rf /var/lib/apt/lists/*

EXPOSE 8000 8001 8443 8444

CMD ["kong", "docker-start"]
