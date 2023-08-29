FROM python:slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y chromium chromium-driver
RUN python -m pip install -r requirements.txt

COPY . .

EXPOSE 1275

CMD ["python", "fast_api.py"]

