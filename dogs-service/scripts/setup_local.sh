#!/usr/bin/env bash
# Bootstrap script to create local DynamoDB table and insert a sample item
# Usage: ./scripts/setup_local_dynamodb.sh

set -euo pipefail

# Config
TABLE_NAME=${TABLE_NAME:-local-dogs-db}
BUCKET_NAME=${BUCKET_NAME:-local-dogs-images}
ENDPOINT=${ENDPOINT:-http://localhost:4566}

# Ensure Docker container is running (use named container `localstack`)
echo "Ensuring localstack container is running..."
if command -v docker >/dev/null 2>&1; then
  if docker ps --filter "name=localstack" --filter "status=running" --format '{{.Names}}' | grep -q '^localstack$'; then
    echo "localstack is already running"
  else
    # Try to start an existing stopped container
    if docker ps -a --filter "name=localstack" --format '{{.Names}}' | grep -q '^localstack$'; then
      echo "Starting existing localstack container..."
      docker start localstack
    else
      echo "Creating and starting localstack container with named volume 'localstack_data'..."
      docker run -d --name localstack -p 4566:4566 -e SERVICES="s3,dynamodb" -v localstack_data:/home/localstack/data localstack/localstack
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

# Create S3 bucket
echo "Creating S3 bucket (if not exists)..."
if aws s3api head-bucket --bucket "$BUCKET_NAME" --endpoint-url "$ENDPOINT" 2>/dev/null; then
  echo "Bucket '$BUCKET_NAME' already exists - skipping create"
else
  echo "Bucket '$BUCKET_NAME' not found, creating..."
  aws s3api create-bucket \
    --bucket "$BUCKET_NAME" \
    --endpoint-url "$ENDPOINT" \
    --create-bucket-configuration LocationConstraint=eu-west-1
fi

# Check bucket creation
if aws s3api head-bucket --bucket "$BUCKET_NAME" --endpoint-url "$ENDPOINT" 2>/dev/null; then
  echo "Bucket '$BUCKET_NAME' is ready"
else
  echo "Failed to create or access bucket '$BUCKET_NAME'" >&2
  exit 1
fi

echo "Done. You can verify with: aws dynamodb list-tables --endpoint-url $ENDPOINT"
