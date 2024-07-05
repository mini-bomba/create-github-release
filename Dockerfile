FROM python:3.12-alpine
LABEL org.opencontainers.image.source=https://github.com/mini-bomba/create-github-release

# Install git
RUN apk add --no-cache git
# Install python deps
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
# Copy the script into the container
COPY src /src

ENTRYPOINT ["python", "/src/main.py"]
