FROM python:3.12-slim

COPY . .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

VOLUME [ "/resources", "/logs" ]

EXPOSE 8000

CMD ["python", "run.py"]
