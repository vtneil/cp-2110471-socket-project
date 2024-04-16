FROM python:3.12

ARG SERVER_NAME

ENV SERVER_NAME=$SERVER_NAME

WORKDIR /app

ADD . /app

RUN apt-get update

RUN apt-get install libasound-dev libportaudio2 libportaudiocpp0 portaudio19-dev -y

RUN pip install --no-cache-dir -r requirements.txt

CMD python -m app.server 0.0.0.0:50000 $SERVER_NAME
