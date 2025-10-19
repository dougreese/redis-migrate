import redis
import time
import sys
import argparse

# --- CONFIGURATION ---
SOURCE_REDIS_PORT = 6379
SOURCE_REDIS_PASSWORD = None  # Set to 'your_password' if needed
SOURCE_REDIS_DB = 0           # Database number for standalone Redis

TARGET_VALKEY_PORT = 6379
TARGET_VALKEY_PASSWORD = None # Set to 'your_password' if needed

MIGRATE_TIMEOUT_MS = 5000  # Timeout for the MIGRATE command in milliseconds
CHUNK_SIZE = 1000          # Number of keys to fetch in each SCAN iteration

# --- CONNECTION SETUP ---
def setup_connections(source_host, target_host):
    """Initializes connections to Redis source and Valkey target."""
    print("🚀 Connecting to source Redis...")
    try:
        source = redis.StrictRedis(
            host=source_host,
            port=SOURCE_REDIS_PORT,
            password=SOURCE_REDIS_PASSWORD,
            db=SOURCE_REDIS_DB,
            decode_responses=False, # Keep keys/values as bytes for MIGRATE
            socket_timeout=10
        )
        source.ping()
        print(f"✅ Source Redis {source_host}:{SOURCE_REDIS_PORT} connected.")

    except Exception as e:
        print(f"❌ Error connecting to source Redis: {e}")
        sys.exit(1)

    print("🚀 Connecting to target Valkey...")
    try:
        target = redis.StrictRedis(
            host=target_host,
            port=TARGET_VALKEY_PORT,
            password=TARGET_VALKEY_PASSWORD,
            decode_responses=False, # Keep keys/values as bytes
        )
        target.ping()
        print("✅ Target Valkey connected.")

    except Exception as e:
        print(f"❌ Error connecting to target Valkey Cluster: {e}")
        # Note: If you get an error here, check if your cluster is healthy
        # and if you are using a Redis cluster client library.
        sys.exit(1)

    return source, target

# --- MIGRATION FUNCTION ---
def migrate_data(source, target, target_host, dry_run=False):
    """
    Scans keys from the source and migrates them to the target Valkey cluster
    without overwriting existing keys.
    """
    print(f"\nScanning keys from source Redis in chunks of {CHUNK_SIZE}...")

    migrated_count = 0
    skipped_count = 0
    cursor = b'0'

    while cursor != 0:
        # 1. SCAN for keys in the source Redis
        cursor, keys = source.scan(cursor=cursor, count=CHUNK_SIZE)

        if not keys:
            continue

        print(f"\n🔑 Processing {len(keys)} keys (Total Migrated: {migrated_count}, Skipped: {skipped_count})...")

        # 2. Iterate and Check/Migrate
        for key in keys:
            try:
                # Use a cluster-aware EXISTS check
                if target.exists(key):
                    print(f"   [SKIP] Key '{key.decode()}' exists in Valkey. Skipping to prevent overwrite.")
                    skipped_count += 1
                    continue

                if dry_run:
                    print(f"   [DRY RUN] Would migrate key '{key.decode()}'.")
                    migrated_count += 1
                    continue

                # 3. MIGRATE safely
                # MIGRATE host port key destination-db timeout [COPY] [AUTH password]
                # Note: We send MIGRATE to the source, which handles the dump/restore.
                # The target is an arbitrary Valkey node, as the cluster logic handles redirection.

                # We use the COPY option to keep the key in the source Redis
                # And we explicitly OMIT the REPLACE option to prevent overwrites.

                # NOTE: We use the *first* target node's details for the MIGRATE command
                # The Valkey Cluster client doesn't expose the underlying MIGRATE easily,
                # so we revert to the raw StrictRedis client associated with the source.

                # To ensure MIGRATE works in a cluster environment, you must have the
                # Valkey cluster running and accessible, and MIGRATE will target
                # a node that the client resolves. We use the details of a known node
                # and target DB 0 (which is the only DB in a cluster).

                result = source.migrate(
                    target_host,
                    TARGET_VALKEY_PORT,
                    key,
                    0, # DB 0 for cluster
                    MIGRATE_TIMEOUT_MS,
                    copy=True # Retain key in source Redis
                )

                if result == b'OK':
                    migrated_count += 1
                    print(f"   [MIGRATED] Key '{key.decode()}' successfully moved.")
                else:
                    # This happens if the key exists and REPLACE is not used,
                    # or for other transient errors. We classify it as skipped.
                    print(f"   [SKIP/ERR] Key '{key.decode()}' failed migration (Result: {result.decode() if isinstance(result, bytes) else result}).")
                    skipped_count += 1

            except Exception as e:
                print(f"   [ERROR] Failed to process key '{key.decode()}': {e}")
                skipped_count += 1

    print("\n--- MIGRATION COMPLETE ---")
    print(f"Total keys migrated: {migrated_count}")
    print(f"Total keys skipped (already existing/error): {skipped_count}")
    print("--------------------------")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: docker run --rm redis-migrate --source-host <source_ip> --target-host <target_ip>")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Migrate data from Redis to Valkey.")
    parser.add_argument("--source-host", required=True, help="Source Redis host")
    parser.add_argument("--target-host", required=True, help="Target Valkey host")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without actually migrating data.")
    args = parser.parse_args()

    source_conn, target_conn = setup_connections(args.source_host, args.target_host)
    migrate_data(source_conn, target_conn, args.target_host, dry_run=args.dry_run)
