FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install -U .

COPY start.sh /start.sh
RUN chmod +x /start.sh
CMD ["/start.sh"]
