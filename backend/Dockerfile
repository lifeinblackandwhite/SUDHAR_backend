FROM python:3.11-bookworm

WORKDIR /code

COPY requirements.txt /code/
RUN pip install --no-cache-dir -r /code/requirements.txt

COPY ./app /code/app
COPY ./dynamicranking /code/dynamicranking

ENV PYTHONPATH=/code

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
