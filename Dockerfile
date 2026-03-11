FROM registry.access.redhat.com/ubi9/python-311
WORKDIR /app
COPY webhook/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY webhook/webhook.py .
USER 1001
CMD ["python", "webhook.py"]