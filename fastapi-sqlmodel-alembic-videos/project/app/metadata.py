from __future__ import annotations
from typing import Optional
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pytube import YouTube, extract
from shazamio import Shazam
from sqlmodel import Field, SQLModel
import pandas as pd
from fastapi import HTTPException
from sqlmodel import select, create_engine, Session
from pathlib import Path

# YouTube API key must be set as environmental variable (both in local and in docker cases)
API_KEY = os.environ.get("API_KEY")

if API_KEY is None:
    raise Exception("Error: API_KEY for youtube api must be set as an environmental variable")

# get the database url from the environment variable
DATABASE_URL = os.environ.get("DATABASE_URL")

# check if DATABASE_URL isset
if DATABASE_URL is not None:
    from app.db import get_session, init_db
else:
    raise Exception("Error: DATABASE_URL for the postgresql service must be set as an environmental variable")

"""
NAME: shazam_recognize
DESC: finds the song from the shazam api
PRMS: -
RTRN: -
"""
async def shazam_recognize(video: Video, audio_file: str):   
    try:
        shazam = Shazam()
        out = await shazam.recognize_song(audio_file)
    except Exception as e:
        raise HTTPException(status_code = 200, detail = str(e))

    matches = out['matches']

    if len(matches) == 0:
        raise HTTPException(status_code = 200, detail = "Audio not recognized in shazam")

    # get track data
    video.audio_title = out['track']['title']
    video.audio_subtitle = out['track']['subtitle']

"""
NAME: Database
DESC: Class which handles the storage and the interaction with the csv file, it reads
      data from csv and updates csv files in case of new insert or deletion
"""
class Database():
    def __init__(self, csv_filename: str) -> None:       
        # read already downloaded videos from csv file
        self.csv_filename = csv_filename

        # create the YouTube application using the API key
        yt_api = build("youtube", "v3", developerKey = API_KEY)

        # set it as a class variable
        self.yt_api = yt_api

        # first we need to check if file exists, if not we can create it
        if not os.path.exists(csv_filename):
            try:
                csv_file = Path(csv_filename)
                csv_file.touch(exist_ok = True)

                self.videos = pd.DataFrame()
            except:
                raise Exception("Error: cannot create csv file")

        elif os.stat(csv_filename).st_size > 0:
            self.read_from_csv(csv_filename)
        else:
            self.videos = pd.DataFrame(columns = ['id', 'url', 'title', 'viewCount', 'publishedAt', 'audio_title', 'audio_subtitle'])

    """
    NAME: insert
    DESC: Get a Video class instance and save the data in local storage and in csv
    PRMS: video: Video
    RTRN: str
    """
    def insert(self, video: Video) -> str:
        self.videos = self.videos._append(video.get_metadata(), ignore_index = True)

        # after insert we have to update csv file
        self.save_in_csv(self.csv_filename)

        return {"success": True, "id": video.id}

    """
    NAME: get_video
    DESC: Get Video class instance based on the given url
    PRMS: video_url: str
    RTRN: Video
    """
    def get_video(self, video_url: str) -> Video:
        # check if video url already exists
        filter_result = self.videos[self.videos['url'] == video_url]

        if filter_result.empty:
            video = Video(video_url, self.yt_api)

            return video
        else:
            raise HTTPException(status_code = 404, detail = "Video already exists")

    """
    NAME: read_from_csv
    DESC: Read already saved videos in the csv and load them into the memory using a pandas dataftame
    PRMS: filename
    RTRN: -
    """
    def read_from_csv(self, filename: str) -> None:
        # read file from the csv, using the pandas library
        try:
            self.videos = pd.read_csv(filename)
        except IOError as error:
            raise Exception(str(error))

    """
    NAME: save_in_csv
    DESC: Save records in the csv file
    PRMS: - 
    RTRN: None
    """
    def save_in_csv(self, filename: str) -> None:
        # if there are any videos in the dataframe, we can write it in the csv
        if self.videos is not None:
            try:
                self.videos.to_csv(filename, index=False)
            except IOError as error:
                raise Exception(str(error))

    """
    NAME: drop
    DESC: frop record from local db / dataframe
    PRMS: video_id
    RTRN: string for the api resonse
    """
    def drop(self, video_id: str) -> str:
        videos = self.videos

        filter_result = videos[videos['id'] == video_id]

        try:
            if not filter_result.empty:
                # drop record from the dataframe
                videos.drop(videos[videos['id'] == video_id].index, inplace = True)

                # update csv file after the deletion
                self.save_in_csv(self.csv_filename)

                return {"success": True, "msg": "Video dropped"}
            else:
                raise HTTPException(status_code = 404, detail = f"Error: Video with id {video_id} not found")
        except:
            raise HTTPException(status_code = 404, detail = f"Error: Video with id {video_id} not found")

"""
NAME: Video
DESC: Class to download, hold and handle data of an individual video from youtube
      It also inherits SQLModel so that we can directly connect the class instance with a sql database
"""
class Video(SQLModel, table = True):
    id: Optional[str] = Field(primary_key = True)
    url: str = Field(index = True) # we search by url, so index will speedup our search in database
    title: str
    viewCount: str
    publishedAt: str
    audio_title: str = Field(default = None)
    audio_subtitle: str = Field(default = None)

    """
    NAME: __init__
    DESC: Class constructor method, Video is also a structured as a binary tree (maybe not needed in case of database), so that search is faster, also there will be no duplicates
    PRMS: api, video_url
    RTRN: None
    """
    def __init__(self, video_url: str, yt_api) -> None:
        self._retrieve_data(video_url, yt_api)

    """
    NAME: retrieve_data:
    DESC: Gets the video url as an input and fills the class variables with the data retrieved from the api
    ARGS: api, video_url
    RETN: None
    """
    def _retrieve_data(self, video_url, yt_api):
        # extract video id from the url
        try:
            video_id = extract.video_id(video_url)
        except: 
            print("Error: url is not valid")
            raise Exception("Error: url is not valid")

        # use yt api to get video statistics and snippet
        try:
            response = yt_api.videos().list(
                part = 'statistics,snippet',
                id = video_id
            ).execute()
        except HttpError as e:
            if e.error_details[0]['reason'] == "rateLimitExceeded":
                raise HTTPException(status_code = 404, detail = "Too many requests. Rate limit exceeded")
            elif e.error_details[0]['reason'] == "quotaExceeded":
                raise HTTPException(status_code = 404, detail = "Quota have been exceeded")
            elif e.error_details[0]['reason'] == "forbidden":
                raise HTTPException(status_code = 404, detail = "Access is forbidden. Please check your google developers page or your API KEY")
            else:
                raise HTTPException(status_code = 404, detail = "Error: could not retrieve data from YouTube Data API")

        # if there are not items found, then the video url was not found
        if len(response['items']) == 0:
            raise HTTPException(status_code = 404, detail = "Error: Could not retrieve data from YouTube Data API for this url")

        info = response['items'][0]
        statistics = info['statistics']
        snippet = info['snippet']

        # fill class variable with the data retrieved
        self.id = video_id
        self.url = video_url
        self.title = snippet['title']
        self.viewCount = statistics['viewCount']
        self.publishedAt = snippet['publishedAt']

        # download video and audio
        self.download_video()

    """
    NAME: get_metadata:
    DESC: Return video info in a dictionary
    ARGS: - 
    RETN: dict
    """
    def get_metadata(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "viewCount": self.viewCount,
            "publishedAt": self.publishedAt,
            "audio_title": self.audio_title,
            "audio_subtitle": self.audio_subtitle
        }
    
    """
    NAME: download_video
    DESC: Download the video using pytube library
    ARGS: - 
    RETN: -
    """
    def download_video(self) -> None:
        try:
            # download the video url
            yt = YouTube(self.url)

            # download video
            yt.streams\
                .filter(progressive = True, file_extension = 'mp4')\
                .order_by('resolution').desc()\
                .first()\
                .download(output_path = "streams")
        except:
            raise HTTPException(status_code = 404, detail = "Error: Cannot download video")
        
    """
    NAME: download_audio
    DESC: Download the audio using pytube library
    ARGS: - 
    RETN: -
    """
    def download_audio(self) -> None:
        try:
            # download the video url
            yt = YouTube(self.url)

            # download audio
            audio_file = yt.streams\
                .filter(only_audio = True, file_extension = 'webm')\
                .order_by('abr').desc()\
                .first()\
                .download(output_path = "streams")
        except:
            raise HTTPException(status_code = 404, detail = "Error: Cannot download audio")
        
        return audio_file
        
    """
    NAME: recognize
    DESC: Finds the song by the audio using the shazam api
    PRMS: - 
    RTRN: -
    """
    async def recognize(self, audio_file: str) -> None:
        # recognize song
        await shazam_recognize(self, audio_file)