FROM python:3.12

WORKDIR /app

ADD . /app

RUN apt-get update

RUN apt-get install libasound-dev libportaudio2 libportaudiocpp0 portaudio19-dev -y

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "./src/client_cli.py"]
