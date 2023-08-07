from fastapi import FastAPI, Depends
from app.metadata import *
from sqlmodel.ext.asyncio.session import AsyncSession

# videos = ["https://www.youtube.com/watch?v=0J2QdDbelmY"]

CSV_FILENAME = "app/storage.csv"

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
@app.get("/api/v1/videos_csv/")
async def get_videos_csv():
    if database.videos is not None:
            return [row for _, row in database.videos.iterrows()]
    else:
        raise HTTPException(status_code = 200, detail = "No videos available")

@app.get("/api/v1/videos/")
async def get_videos(session: AsyncSession = Depends(get_session)):
    await init_db()
    
    result = await session.execute(select(Video))

    videos = result.scalars().all()

    return videos

# download new video
@app.get("/api/v1/video_csv/")
async def add_video(video_url: str):
    # get video data
    video = database.get_video(video_url)
    
    audio_file = video.download_audio()

    await video.recognize(audio_file)

    # finally insert video in database object, this will also update the csv file
    return database.insert(video)

# download new video
@app.get("/api/v1/video/")
async def add_video(video_url: str, session: AsyncSession = Depends(get_session)):
    await init_db()
    
    # we have to check if there is already in database
    query = select(Video).where(Video.url == video_url)
    result = await session.execute(query)

    # get all scalar results in a list
    filtered = result.scalars().all()

    # if we have results, this mean the video already exists in database
    if len(filtered) > 0:
        raise HTTPException(status_code = 404, detail = "Video already exists")

    # create video instance
    try:
        video = Video(video_url = video_url, yt_api = database.yt_api)
    except Exception as error:
        raise HTTPException(status_code = 404, detail = str(error))

    if video is None:
        raise HTTPException(status_code = 404, detail = "Error: handle better!!")

    # download audion and find in in shazam
    audio_file = video.download_audio()

    # find video using shazamIO api
    await video.recognize(audio_file)

    # use session to add video in database
    session.add(video)

    await session.commit()
    await session.refresh(video)

    return video

# delete downloaded video
@app.delete("/api/v1/video_csv/")
async def delete_video(video_id: str):
    return database.drop(video_id)