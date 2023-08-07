from fastapi import FastAPI
from metadata import *

CSV_FILENAME = "storage.csv"

# create local object as database
database = Database(CSV_FILENAME)

# create fast api
app = FastAPI()

# define root url
@app.get("/")
async def root():
    return {"message": "Coding Challenge: Videos downloaded from Youtube api"}

# define ping url
@app.get("/ping/")
async def ping():
    return {"message": "Coding Challenge: Access was successful"}

# get all videos 
@app.get("/api/v1/videos/")
async def get_videos():
    if database.videos is not None:
        return [row for _, row in database.videos.iterrows()]
    else:
        raise HTTPException(status_code = 200, detail = "No videos available")

# download new video
@app.get("/api/v1/video/")
async def add_video(video_url: str):
    # get video data
    video = database.get_video(video_url)
    audio_file = video.audio_file

    await video.recognize(audio_file)

    # finally insert video in database object, this will also update the csv file
    return database.insert(video)

# delete downloaded video
@app.delete("/api/v1/video/")
async def delete_video(video_id: str):
    return database.drop(video_id)