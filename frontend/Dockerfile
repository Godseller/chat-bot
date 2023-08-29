FROM python:slim

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install -r requirements.txt

COPY . .

CMD ["python", "telegram_bot.py"]