ProQuiz is a trivia game, pretty much like _Who want to be a millionaire_.

### Glimpse of history

I started this project with the idea to create a multistage simple interview quiz. Nothing new on the horizon. Something I would develop in my free time and I wanted to propose to my company. I quickly realized that this idea would not be suitable for the context so I decide to make a turn and develop something I always to built.
There are plenty of similar solutions out there.

It absolutely doesn't want to be something innovative. I just wanted to implement it and learn something new while doing something funny.

### Technologies

When I started working on the quiz I opted for Pyramid because I wanted to learn this framework. So I completed the v.0.1 using Pyramid (plus many other libraries).

Although Pyramid is more a Model-View-Template tool, I developed my solution using a standard REST CRUD approach. A set of endpoints mapped to a set of entities (aka `models`) with a simple validation mechanism in between, plus the _play_ logic.

When the development of the first version, driven by tests (TDD), was completed I started pursuing the idea to develop the Frontend too, or at least make it feasible for someone (most likely a friend) to jump in and code.

### FastAPI

I began to issue some real test HTTP requests and I encountered some challenges and I noticed that the framework I choose _isn't on top the rankings_. Moreover I thought: if I want to grow this project or keep working the way I have in mind, maybe is suitable to switch to a more reliable framework.

So I decided to port the project to FastAPI, a library I heard of the first time, last year and seemed to fit better for a purely API based Backend, with the addition of having a wider adoption.

### Different architecture

##### Diagram [photo]

This project still preserve the monolith structure. FastAPI and its  intense adoption of the dependency injection pattern force me to rethink the structure and more specifically where the logic ORM logic resides.

Still driven by the existing test suite I developed the new version as it is now. The test suite required a small initial effort to work, due to the way database session objects are fetched when a request reaches the endpoint. Things started to work quickly after.

In the new architecture I emptied the entities class of any logic but the simple properties used to return some internal date in a more comfortable mode. Moved the interface to the ORM to a new set of `classes` called `DataTransferObject`(`DTO`).

### Validation

To ease testing also the validation mechanism is structured into two components: `syntax` and `logical`. The former, as the terms indicates, verifies that the incoming data respects the expected data types.

The latter verifies that the objects of the `Entities` involved, actually exists and can be manipulated.

So the former one doesn't need a testing DB, the former one does.

### Play

Probably the most interesting component of the project. The idea is simple:

the user starts a match and plays against the system. At each question the user either answers or skips the challenge. Still the `reaction` is recorded. After the last question of the last `game` the `match` is over and a final score is computed.

A match can be stopped and resumed. Can contain N games each one having M questions.

Currently the interface consists of three methods:

- `start`: start the match
- `next`: move to the next question
- `react`: answer the current question
