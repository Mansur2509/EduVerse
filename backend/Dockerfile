FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system uniway && adduser --system --ingroup uniway uniway

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R uniway:uniway /app

USER uniway
EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

