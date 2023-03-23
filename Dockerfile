FROM python:3.8

ARG ENV_TAG
ENV ENV_TAG=$ENV_TAG

WORKDIR /usr/src/chatweb3

COPY ./requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . ./
EXPOSE 9999

ENTRYPOINT ./start.sh
