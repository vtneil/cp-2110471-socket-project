FROM python:3.12

WORKDIR /app

RUN apt-get update

RUN apt-get install libasound-dev libportaudio2 libportaudiocpp0 portaudio19-dev -y

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .
