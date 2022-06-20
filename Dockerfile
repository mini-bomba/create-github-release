FROM python:3.9.6-slim-buster
LABEL org.opencontainers.image.source=https://github.com/mini-bomba/create-github-release

# Install git
RUN apt-get update && apt-get install git -y --no-install-recommends
# Install python deps
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
# Copy the script into the container
COPY src /src

ENTRYPOINT ["python", "/src/main.py"]
