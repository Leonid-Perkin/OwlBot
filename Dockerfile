FROM python:3.11-slim
WORKDIR /app
COPY main.py /app/
COPY requirements.txt /app/
RUN pip install -r requirements.txt
RUN playwright install
CMD ["python", "main.py"]