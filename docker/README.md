# PostgreSQL + pgvector Local Docker

## Start

```powershell
cd D:\PycharmProjects\NeoDev
docker compose up -d
```

## Connection

| Item | Value |
| --- | --- |
| Host | localhost |
| Port | 5432 |
| User | postgres |
| Pass | postgres |
| DB | neodev |

Connection string: `postgresql://postgres:postgres@localhost:5432/neodev`

## Schema Initialization

The PostgreSQL image runs a single initialization file on first database creation:

```text
docker/init.sql
```

Do not add incremental SQL migration files for the current storage rebuild. Update `docker/init.sql` directly when the initial schema changes.

For an existing local database volume, recreate the volume before validating schema changes:

```powershell
docker compose down -v
docker compose up -d --build
```

## Stop And Clean Up

```powershell
docker compose down
docker compose down -v
```
