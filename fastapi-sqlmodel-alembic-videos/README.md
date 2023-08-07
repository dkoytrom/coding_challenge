# RnD sample template

FastAPI project that uses async SQLAlchemy, SQLModel, Postgres, Alembic, and Docker.

## Start this project

```sh
$ docker-compose up -d --build
$ docker-compose exec web alembic upgrade head
```

See the docs in: [http://localhost:8000/docs](http://localhost:8000/docs)

Sanity check: [http://localhost:8004/ping](http://localhost:8004/ping)

Add a song:

```sh
$ curl -d '{"name":"Test name", "artist":"Test Artist", "year":"2023"}' -H "Content-Type: application/json" -X POST http://localhost:8004/songs
```

Get all songs: [http://localhost:8004/songs](http://localhost:8004/songs)

