# Redis to Valkey Migration Script

This script migrates Redis or Valkey data from one instance to another. It was created to migrate all data from a Redis instance to a Valkey instance, but the source and target are interchangeable. This is better than moving a 'dump' file around if there is existing data in the target instance.

## Building the Docker Image

To build the Docker image, run the following command in the root of the project:

```bash
docker build -t redis-migrate .
```

## Running the Migration

To run the migration, use the `docker run` command with the following parameters:

- `--source-host`: The IP address of the source Redis instance.
- `--target-host`: The IP address of the target Valkey instance.
- `--dry-run`: (Optional) Perform a dry run without actually migrating any data.

### Example

```bash
docker run --rm redis-migrate --source-host 192.168.1.10 --target-host 192.168.1.11
```

### Dry Run Example

```bash
docker run --rm redis-migrate --source-host 192.168.1.10 --target-host 192.168.1.11 --dry-run
```

## Interactive Usage (redis-cli)

To use `redis-cli` interactively within the container, you can start a shell inside the container by overriding the entrypoint:

```bash
docker run -it --entrypoint /bin/bash redis-migrate
```

Once inside the container, you can use `redis-cli` to connect to your instances:

```bash
# Connect to the source Redis instance
redis-cli -h <source_ip>

# Connect to the target Valkey instance
redis-cli -h <target_ip>
```
