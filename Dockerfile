FROM python:3.10

ARG ENV_TAG
ENV ENV_TAG=$ENV_TAG

# On cloud build, things run by default at /root, but this changes to /home
# on cloud run. This means we can't find certain things like Chrome that
# got installed. So we fix the default location used by the installers here.
ENV XDG_CONFIG_HOME=/root/.config
ENV XDG_CACHE_HOME=/root/.cache

WORKDIR /usr/src/chatweb3

COPY ./requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
RUN playwright install
RUN playwright install-deps
RUN apt install xauth xvfb

COPY . ./
EXPOSE 9999

ENTRYPOINT ./start.sh
