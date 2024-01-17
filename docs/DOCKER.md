# Docker

Docker is one of way to run the project. It is preferred way for running the project for its simplicity and portability.
Project contains main image called `charlie-mnemonic`, which contains all the code and dependencies.
Optionally, there is also `psdb` image, which contains postgres database.
Otherwise, you can use sqlite or postgres database that is running somewhere else.

Everything is orchestrated by `docker-compose.yml` file, which is used to start the project.

