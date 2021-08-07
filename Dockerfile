FROM python:3.9.6-slim-buster

COPY requirements.txt /requirements.txt
COPY src /src

RUN pip install -r /requirements.txt
RUN apt-get update
RUN apt-get install git -y

ENTRYPOINT ["python", "/src/main.py"]
