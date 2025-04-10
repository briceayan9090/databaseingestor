FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .

EXPOSE 8084

CMD ["streamlit", "run", "app.py", "--server.port", "8084"]
