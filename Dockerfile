FROM python:3.11

WORKDIR /usr/src/chatweb3

COPY ./requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . ./
EXPOSE 9999

ENTRYPOINT ./start.sh
