## ProQuiz

ProQuiz is a trivia game, pretty much like _Who wants to be a millionaire_.

### Glimpse of history

I started this project with the idea to create a multistage simple interview quiz. Nothing new on the horizon. Something I would develop in my free time and I wanted to propose to my company. I quickly realised that this idea would not be suitable for the context so I decided to make a U turn and develop something a bit different.

There are plenty of similar solutions out there. Absolutely doesn't want to be something innovative. I just wanted to implement it and learn while doing something funny.

### Technologies

When I started working on the quiz I opted for [Pyramid](https://docs.pylonsproject.org/projects/pyramid/en/latest/) because I wanted to learn this framework. So I completed [v.0.1](https://github.com/mp-83/proquiz-v0.1) using Pyramid (plus many other libraries). Although it is more a Model-View-Template tool, I developed my solution using a standard REST CRUD approach. A set of endpoints mapped to a set of entities (aka `models`) with a simple validation mechanism in between, plus the _play_ logic.

When the development of the first version, driven by tests (TDD), was completed, I started pursuing the idea to develop the Frontend too, or at least make it feasible for someone (most likely a friend) to jump in and code.

![Diagram version 1](docs/pyramid-diagram.png "Diagram v.1")

### FastAPI

Moreover I thought: if I want to grow this project or keep working the way I have in mind, maybe it is suitable to switch to a more adopted framework. I decided to port the project to [FastAPI](https://fastapi.tiangolo.com/) as it seemed to fit better for a purely API based Backend.

### Different structure

This project still preserves the monolithic architecture. FastAPI and its intense adoption of the dependency injection pattern forced me to rethink the structure and more specifically where the ORM logic resides.

Driven by the existing test suite I developed the new current version. The test suite required a small initial effort to work, due to the way database session objects are fetched when a request reaches the endpoint. Things started to work quickly after

In the new structure I emptied the `entities` class of any logic but the simple properties used to return some internal data in a more comfortable mode. Moved the interface to the ORM to a new set of `classes` called `DataTransferObject`(`DTO`).

![Diagram version 2](docs/fastapi-diagram.png "Diagram v.2")

### Validation

To ease testing also the validation mechanism is structured into two components: `syntax` and `logical`. The former, as the terms indicates, verifies that the incoming data respects the expected data types.

The latter verifies that the objects of the `Entities` involved, actually exist and can be manipulated in the sense that some logical constraints are respected.

The syntax check is purely a type verification. The second one interacts with the database to retrieve the object.

### Play

Probably the most interesting part of the project is gaming logic. The idea is simple:

the user starts a match and plays against the system. At each question the user either answers or skips. Still the `reaction` will be recorded. After the last question of the last `game`, the `match` is over and a final score is computed.

A match can be stopped and resumed.

Currently the *play* interface consists of three methods:

- `start`: start the match
- `next`: move to the next question
- `react`: answer the current question

there is also the `previous` method, which is not used at the moment.

#### Hash or Code

A match can be alternatively identified by its `hash` or its numeric `code`. The two options where thought to offer different ways to identify a match. These logs clearly show that the difference is merely the starting url.

```
"POST /api/v1/play/h/NDfCN HTTP/1.1" 200 OK
"POST /api/v1/play/start HTTP/1.1" 200 OK
"POST /api/v1/play/next HTTP/1.1" 200 OK
....
```

```
"POST /api/v1/play/code HTTP/1.1" 200 OK
"POST /api/v1/play/start HTTP/1.1" 200 OK
"POST /api/v1/play/next HTTP/1.1" 200 OK
....
```

The `code` is more handy if you want to share it as you just need to share a numerical code, say `6238`, while the `hash` url has the main advantage of uniquely identifying the match.

#### Restricted or not

A match can also be `restricted` or not. If a match belongs to the first category, it is protected by a password. The solely reason behind restricting its access is to protect the content, *i.e* the questions and answers, from being visible by anyone.

#### Players

A match can be played by signed and unsigned users. These two terms are just synonyms of authenticated/unauthenticated users. The *signed* term stems from the fact the system does not directly uses the email and birth date of the user, but *signs* these values to authenticate the user. Therefore no authentic data is used in the `User` table. The univocity of the email, granted by the email providers, guarantees the uniqueness of the user.

The reason behind this mechanism stems from a friend of mine, very privacy addicted, that initially I figured out as a potential contributor to this project.

#### Games and Questions

A match can contain N games each one having M questions. Each question can have X answers. No upper limit is set.

Questions can be created one by one, or imported via .yaml file. The file must be structured as follows:
```
questions:
  - text:
  - time:
  - answers:
      -
      -
      -
```
Questions can be timed or not.

#### Editable but no deletion yet

Matches, questions, as well answers can be edited but nothing can be deleted yet. Being still at a very early stage, I focused more on the play logic than offering a fully capable match/question management interface.

### Compose

This project requires [Docker](https://www.docker.com/) to be already installed in the system. It was tested on Mac.

To start the application is enough to
```
docker-compose up -d
```

while to reset the environment (this also deletes the DB)
```
docker-compose rm -fs && docker-compose down -v && docker-compose up -d
```

while to run the tests
```
docker-compose exec backend sh tests-start.sh -vv
```

To start and fill in the database with some initial data
```
docker-compose exec backend sh prestart.sh
```

To generate one new migration
```
docker-compose exec backend alembic revision --autogenerate -m "give a name to the migration here"
```

To apply one migration
```
docker-compose exec backend alembic upgrade head
```

To revert one migration
```
docker-compose exec backend alembic downgrade -1
```

### PgAdmin

Once the containers are started, you can navigate to the [PgAdmin Panel](http://localhost:5050/browser/) and access with the PGADMIN credentials stored in the `.env` file

Once logged in, these are the steps to follow to access the DB:
- click on `Add New Server`
- give it a name (ex: `LocalDB`)
- within the same popup/modal, move to the `Connection` tab and
    - insert `quizdb` (or the name you assigned to the database service in the docker-compose file)
	- leave the default port
	- username is the `POSTGRES_USER` as specified in the `.env` file
	- password is the `POSTGRES_PASSWORD` as specified in the `.env` file
- click `SAVE`

To browse the DB tables, this would be the path
```
LocalDB ==> app ==> Schemas ==> public ==> tables
```

Google *PgAdmin tutorial* for more info

### Interaction

There is a composed command that mimics the basic interaction a user might perform using a GUI. This command can be started via
```
docker-compose exec backend sh gui.sh
```

### Contributing

This project was developed during my freetime (snapshots of the design & development phase, using the old *pen and paper* approach, are available [here](https://photos.app.goo.gl/2nQmgMT5WSuZwSrF6)). It is currently a library not a fully fledged application. It totally misses the GUI so there is no way to display anything but using the `gui.sh` script.

Once you set up the project locally, as explained above, you can contribute either reporting bugs (which I expect to be many at this stage) or proposing improvements. I am the only maintainer of this project therefore contributions are welcome.

I do have plans to introduce new functionalities in the next version as well as it would be nice to develop the FrontEnd (this might be a good contribution). To browse the APIs, the swagger page can be found at http://localhost:7070/docs.

### License

This project is licensed under the terms of the MIT license.
