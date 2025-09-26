#!/usr/bin/env bash
# Bootstrap script to create local DynamoDB table and insert a sample item
# Usage: ./scripts/setup_local_dynamodb.sh

set -euo pipefail

# Config
TABLE_NAME=${TABLE_NAME:-local-dogs-db}
ENDPOINT=${ENDPOINT:-http://localhost:8000}

# Ensure Docker container is running (use named container `dynamodb_local`)
echo "Ensuring DynamoDB Local container is running..."
if command -v docker >/dev/null 2>&1; then
  if docker ps --filter "name=dynamodb_local" --filter "status=running" --format '{{.Names}}' | grep -q '^dynamodb_local$'; then
    echo "dynamodb_local is already running"
  else
    # Try to start an existing stopped container
    if docker ps -a --filter "name=dynamodb_local" --format '{{.Names}}' | grep -q '^dynamodb_local$'; then
      echo "Starting existing dynamodb_local container..."
      docker start dynamodb_local
    else
      echo "Creating and starting dynamodb_local container with named volume 'dynamodb_local_data'..."
      docker run -d --name dynamodb_local -p 8000:8000 -v dynamodb_local_data:/home/dynamodblocal/data amazon/dynamodb-local
    fi
  fi
else
  echo "docker not found in PATH. Please install docker or start DynamoDB Local manually." >&2
  exit 1
fi

echo "Using table: $TABLE_NAME"

echo "Creating table (if not exists)..."
# Only create the table if it doesn't already exist to avoid ResourceInUseException
if aws dynamodb describe-table --table-name "$TABLE_NAME" --endpoint-url "$ENDPOINT" >/dev/null 2>&1; then
  echo "Table '$TABLE_NAME' already exists - skipping create"
else
  echo "Table '$TABLE_NAME' not found, creating..."
  aws dynamodb create-table \
    --table-name "$TABLE_NAME" \
    --attribute-definitions AttributeName=PK,AttributeType=S AttributeName=SK,AttributeType=S \
    --key-schema AttributeName=PK,KeyType=HASH AttributeName=SK,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --endpoint-url "$ENDPOINT"
fi

# Wait for table to become active (poll)
echo "Waiting for table to become ACTIVE..."
for i in {1..30}; do
  status=$(aws dynamodb describe-table --table-name "$TABLE_NAME" --endpoint-url "$ENDPOINT" --query "Table.TableStatus" --output text 2>/dev/null || true)
  if [[ "$status" == "ACTIVE" ]]; then
    echo "Table is ACTIVE"
    break
  fi
  echo "  waiting... ($i)"
  sleep 1
done

echo "Done. You can verify with: aws dynamodb list-tables --endpoint-url $ENDPOINT"
