# Persistence

This document describes how to persist data in Charlie Mnemonic when using docker.
For more information about docker, see [docker documentation](https://docs.docker.com/).
For more information about docker in Charlie Mnemonic, see our [docker documentation](DOCKER.md).

## User data

All persistent data are in "/app/users" directory. If the directory is mounted to the docker container, the data is
persistent.
Otherwise, the data are lost when the container is stopped.
This is automatically taken care of by the docker-compose.yml file.

The volume is mounted from `${HOME}/AppData/Roaming/charlie-mnemonic/users` in Windows, otherwise it depends on specific
docker-compose.yml.
It can be relative path when developing or `.charlie-mnemonic/users` in Linux.
Deleting this directory deletes all the user data (except for the database).

## Database

When using relational postgres database, the data are stored in the database. Again, this is automatically taken care of
by the docker-compose.yml file.
All the data are saved in volume named "postgres-data". If you want to delete the data, you can delete the volume using
the following command:

```bash
docker volume rm postgres-data
```

If sqlite is used, the data are stored in the user data above.

## Links

- [docker volumes](https://docs.docker.com/storage/volumes/).