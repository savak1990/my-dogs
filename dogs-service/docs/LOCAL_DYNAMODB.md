Local DynamoDB - bootstrap instructions
=====================================

This file describes how to run DynamoDB Local and create the `local-dogs-db` table used by the project during local development with `sam local`.

Prerequisites
-------------
- Docker installed and running
- AWS CLI v2 installed and configured (only for local DynamoDB commands we pass --endpoint-url)
- SAM CLI installed
- `env.json` present in the project root (this repo already includes one that points to `http://host.docker.internal:8000`)

1) Start DynamoDB Local (Docker)
--------------------------------
Run DynamoDB Local on port 8000. On macOS use `host.docker.internal` from inside containers so the Lambda can reach the host.

```bash
# simple (stateless)
docker run -d --name dynamodb_local -p 8000:8000 amazon/dynamodb-local

# optional: persist data across restarts
docker run -d --name dynamodb_local -p 8000:8000 -v dynamodb_local_data:/home/dynamodblocal/data amazon/dynamodb-local

docker ps --filter "name=dynamodb_local"
```

2) Create the local table (AWS CLI)
-----------------------------------
The project `env.json` uses the table name `local-dogs-db`. Create that table locally. The schema below is an example — adapt `AttributeDefinitions` and `KeySchema` to match your `template.yaml` / application model if different.

```bash
aws dynamodb create-table \
	--table-name local-dogs-db \
	--attribute-definitions AttributeName=PK,AttributeType=S AttributeName=SK,AttributeType=S AttributeName=user_id,AttributeType=S \
	--key-schema AttributeName=pk,KeyType=HASH AttributeName=sk,KeyType=RANGE \
	--billing-mode PAY_PER_REQUEST \
	--global-secondary-indexes '[{"IndexName":"user_id-index","KeySchema":[{"AttributeName":"user_id","KeyType":"HASH"},{"AttributeName":"sk","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":1,"WriteCapacityUnits":1}}]' \
	--endpoint-url http://localhost:8000 \
	--region us-east-1
```

If your CloudFormation defines a different primary key or GSIs, change `pk`, `sk`, and the GSI definitions above accordingly.

3) Verify the table exists
--------------------------

```bash
aws dynamodb describe-table --table-name local-dogs-db --endpoint-url http://localhost:8000 --region us-east-1
```

4) Insert a test item (optional)
--------------------------------
Use `put-item` to add a sample record that your local Lambda can read when you invoke it.

```bash
aws dynamodb put-item \
	--table-name local-dogs-db \
	--item '{
		"pk": {"S":"USER#11111111-1111-1111-1111-111111111111"},
		"sk": {"S":"DOG#22222222-2222-2222-2222-222222222222"},
		"dog_id": {"S":"22222222-2222-2222-2222-222222222222"},
		"user_id": {"S":"11111111-1111-1111-1111-111111111111"},
		"name": {"S":"Fido"},
		"breed": {"S":"Beagle"},
		"created_at": {"S":"2025-09-26T12:00:00Z"}
	}' \
	--endpoint-url http://localhost:8000 \
	--region us-east-1

# verify
aws dynamodb get-item --table-name local-dogs-db --key '{"pk":{"S":"USER#11111111-1111-1111-1111-111111111111"},"sk":{"S":"DOG#22222222-2222-2222-2222-222222222222"}}' --endpoint-url http://localhost:8000 --region us-east-1
```

5) Run SAM local (use `env.json`)
---------------------------------
Start the API or invoke a single function and pass the env file so the Lambda container uses the local DynamoDB endpoint.

```bash
# start REST API (recommended)
sam local start-api --env-vars env.json

# or invoke single function (uses env.json too)
sam local invoke DogsServiceFunction --env-vars env.json --event events/200_get_dogs_ev.json
```

Notes and troubleshooting
-------------------------
- `env.json` (passed to `--env-vars`) overrides environment variables declared in `template.yaml` for local runs. Keep `DYNAMODB_ENDPOINT` in `env.json` (pointing to `http://host.docker.internal:8000`) and do not hardcode a local endpoint in `template.yaml`.
- If DynamoDB Local is run in Docker (as above) you can use `host.docker.internal` in `env.json` so the Lambda container can reach the host. If you run DynamoDB Local in another container, consider creating a Docker network and starting both containers in the same network and using container hostnames.
- Reduce boto3/client retries and timeouts when developing locally if you see long waits while debugging. Use `botocore.config.Config(retries={"max_attempts":2}, connect_timeout=2, read_timeout=5)` when creating the client in `db.py`.
- Persisting DynamoDB Local data: use the `-v dynamodb_local_data:/home/dynamodblocal/data` volume option in the `docker run` above.
- If you plan to commit `env.json` to the repo, remove any secrets; otherwise add `env.json` to `.gitignore`.

Stop / start and persistence
----------------------------
If you want to stop DynamoDB Local temporarily and keep your tables, use `docker stop` and `docker start` (these preserve the container filesystem and data):

```bash
docker stop dynamodb_local
# later
docker start dynamodb_local
```

If you remove the container (`docker rm`) the data stored in the container's writable layer is lost unless you used a named volume. To persist table data across container removal, run DynamoDB Local with a named volume and reattach it when you recreate the container:

```bash
# create/run with a named volume (persists data independently of the container)
docker run -d --name dynamodb_local -p 8000:8000 -v dynamodb_local_data:/home/dynamodblocal/data amazon/dynamodb-local

# remove container but keep named volume
docker stop dynamodb_local
docker rm dynamodb_local

# recreate and reattach the same named volume
docker run -d --name dynamodb_local -p 8000:8000 -v dynamodb_local_data:/home/dynamodblocal/data amazon/dynamodb-local
```

Avoid `docker rm -v dynamodb_local` (or removing anonymous volumes) if you want to keep the data. If you originally started the container without a named volume and you want to preserve existing data, do not remove the container; instead stop/start it.

Backup / restore (optional)
---------------------------
You can export table contents before removing the container and re-import later. For small datasets a simple scan + batch-write works:

```bash
# export
aws dynamodb scan --table-name local-dogs-db --endpoint-url http://localhost:8000 --region us-east-1 --output json > local-dogs-db-scan.json

# restore (example - use a small script to batch-write items from the JSON)
```

Advanced alternatives
---------------------
- LocalStack: emulate many AWS services (including DynamoDB) and optionally run CloudFormation locally to create tables automatically.
- Provision the real DynamoDB table in AWS (via `sam deploy`) and point your local tests at it — not recommended for routine dev because it uses real AWS resources.

If you'd like, I can add a small `scripts/setup_local_dynamodb.sh` script with these commands and/or create a repo `Makefile` entry to automate it.

Bootstrap script
----------------
There's a convenience script at `scripts/setup_local_dynamodb.sh` that creates the table and inserts a sample item. Make it executable and run it after DynamoDB Local is running:

```bash
chmod +x scripts/setup_local_dynamodb.sh
./scripts/setup_local_dynamodb.sh
```

