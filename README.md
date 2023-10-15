# Coding challenge: YouTube Video Downloader, Audio Converter, and Metadata Extractor Web Service
FastApi based we service which used Youtube Data API to fetch the metadata of the videos, with the ability to download the video, convert the video to an audio file with pytube library, recognizing videos with ShazamIO library and saving metadata in a csv file. 
This application works in two ways:

* It can run locally with the storage being the csv file, videos and audio are saved under the streams folder
* It can also run inside the provided docker container, the csv metadata storage is still working, on top of that the metadata are handled by the local Postgresql service

# Setup Youtube api 
(https://developers.google.com/youtube/v3/getting-started)

- Login to google developers page
- connect with a google account (google account is required)
- Create project
- Explore & Enable APIs.
- Enable API: YouTube Data API v3
- Create a credential
- Get the API key and use it in the rest api application

The api key can be set locally in a virual environment by adding it in the bin/activate file. In the docker it can be configured in docker-compose.yml file under environment section

# Start import docker images from local folder
```sh
$ cd fastapi-sqlmodel-alembic-videos/
$ docker-compose up -d --build
$ docker-compose exec web alembic upgrade head
```

# How to access docker containers
sudo docker exec -it container_id bash

# add the following requirements in file requirements.txt
```
alembic==1.11.1
asyncpg==0.28.0
fastapi==0.100.0
sqlmodel==0.0.8
uvicorn==0.22.0
google-api-python-client==2.95.0
pandas==2.0.3
pytube==15.0.0
shazamio==0.4.0.1
ffmpeg==1.4
ffprobe==0.5
```

# Change file: docker-compose.yml
```
version: '3.8'

services:

  web:
    build: ./project
    command: uvicorn app.main:app --reload --workers 1 --host 0.0.0.0 --port 8000
    volumes:
      - ./project:/usr/src/app
    ports:
      - 8004:8000
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/videos
      - API_KEY=AIzaSyCL3GkqDDazOscVPwP8dRsj84o_0X2S6WY
    depends_on:
      - db

  db:
    image: postgres:15.3
    expose:
      - 5432
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=videos
```

# Change the following line in file: project/alembic.ini

```
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@db:5432/videos
```

# Include also ffmpeg in install commmand in file: project/Dockerfile

```
# install system dependencies
RUN apt-get update \
  && apt-get -y install netcat gcc postgresql ffmpeg\
  && apt-get clean
```

# Commands to stop/start (build) the docker containers
```sh
$ docker-compose down -v
$ docker-compose up -d --build
```

# Application requests when application is running from the docker: 
* Documentation: [http://localhost:8004/docs](http://localhost:8004/docs)
* Get all videos: [http://localhost:8004/api/v1/videos](http://localhost:8004/api/v1/videos)

```sh
curl -X 'GET' \
  'http://localhost:8080/api/v1/videos/' \
  -H 'accept: application/json'
```

* Download a video

```sh
curl -X 'GET' \
  'http://localhost:8080/api/v1/video/?video_url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D0J2QdDbelmY' \
  -H 'accept: application/json'
```

* Delete a video: 

```sh
curl -X 'DELETE' \
  'http://localhost:8080/api/v1/video/?video_id=0J2QdDbelmY' \
  -H 'accept: application/json'
```

# Install python libraries - dependencies in a local virual environment
```sh
.venv/bin/pip3 install pytube
.venv/bin/pip3 install shazamio
.venv/bin/pip3 install "fastapi[all]"
.venv/bin/pip3 install google-api-python-client
.venv/bin/pip3 install pandas
.venv/bin/pip3 install sqlmodel
.venv/bin/pip3 install ffmpeg
```

# Application local execution (csv file as local storage)
```sh
$ source .venv/bin/activate
$ uvicorn main:app --workers 1 --reload --port 8080
```
