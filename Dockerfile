FROM python:3.11-slim
WORKDIR /app
COPY main.py /app/
COPY requirements.txt /app/
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["python", "main.py"]