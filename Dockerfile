FROM python:3.9.6-slim-buster

# Install git
RUN apt-get update && apt-get install git -y
# Install python deps
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
# Copy the script into the container
COPY src /src

ENTRYPOINT ["python", "/src/main.py"]
