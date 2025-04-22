FROM python:3.9-slim

# Создаем рабочую директорию
WORKDIR /app

# Копируем только requirements.txt сначала для использования кеша слоев Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все остальные файлы из текущей директории в /app
COPY . .

# Явно указываем, что запускаем bot.py из текущей директории
CMD ["python", "./bot.py"]