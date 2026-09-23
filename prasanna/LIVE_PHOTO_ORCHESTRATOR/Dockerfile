FROM python:3.9
EXPOSE 8432
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["gunicorn", "--bind", "0.0.0.0:8432", "--timeout", "600","--workers", "10", "main:app"]