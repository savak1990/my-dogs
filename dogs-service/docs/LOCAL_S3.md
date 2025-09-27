# Local S3 Development Setup

This document explains how to set up and use LocalStack S3 for local development of the dogs-service.

## Prerequisites

- Docker installed and running
- AWS CLI installed and configured
- SAM CLI installed

## Starting LocalStack S3

### Option 1: Using Docker directly

```bash
# Start LocalStack with S3 service
docker run -d \
  --name localstack \
  -p 4566:4566 \
  -e SERVICES=s3 \
  -e DEBUG=1 \
  localstack/localstack

# Verify it's running
docker ps | grep localstack
```

### Option 2: Using Docker Compose (Recommended)

Create a `docker-compose.yml` file in your project root:

```yaml
version: '3.8'
services:
  localstack:
    image: localstack/localstack
    container_name: localstack
    ports:
      - "4566:4566"
    environment:
      - SERVICES=s3
      - DEBUG=1
    volumes:
      - localstack_data:/tmp/localstack

volumes:
  localstack_data:
```

Then start it:

```bash
docker-compose up -d localstack
```

## Setting up S3 Bucket

```bash
# Create the dogs-images bucket
aws s3 mb s3://dogs-images --endpoint-url=http://localhost:4566

# List buckets to verify
aws s3 ls --endpoint-url=http://localhost:4566
```

## Environment Configuration

Make sure your `env.json` file includes the S3 endpoint:

```json
{
  "DogsServiceLambda": {
    "DOGS_TABLE_NAME": "DogsTable",
    "DOGS_IMAGES_BUCKET": "dogs-images",
    "DYNAMODB_ENDPOINT": "http://host.docker.internal:8000",
    "S3_ENDPOINT_URL": "http://host.docker.internal:4566",
    "LOG_LEVEL": "DEBUG"
  }
}
```

## Running Your Application

1. Start LocalStack S3 (see above)
2. Create the S3 bucket (see above)
3. Start your SAM application:

```bash
# Start API Gateway locally
sam local start-api --env-vars env.json

# Or invoke a specific function
sam local invoke --event events/200_get_health_ev.json --env-vars env.json
```

## Testing S3 Operations

### 1. Start LocalStack
```bash
docker run -d --name localstack -p 4566:4566 -e SERVICES=s3 localstack/localstack
```

### 2. Create bucket
```bash
aws s3 mb s3://dogs-images --endpoint-url=http://localhost:4566
```

### 3. Test presigned URL generation (your API will do this)
```bash
aws s3 presign s3://dogs-images/test.jpg --endpoint-url=http://localhost:4566
```

### 4. Use the presigned URL to upload
```bash
curl -X PUT -T test-image.jpg "PRESIGNED_URL_HERE"
```

### 5. Verify upload worked
```bash
aws s3 ls s3://dogs-images --endpoint-url=http://localhost:4566
```

## Testing End-to-End Flow

1. **Create a dog image upload request:**
```bash
curl -X POST http://localhost:3000/users/550e8400-e29b-41d4-a716-446655440000/dogs/1/images \
  -H "Content-Type: application/json" \
  -d '{"image_extension": "jpg"}'
```

2. **Use the returned presigned URL to upload an image:**
```bash
# Copy the presigned_url from the response above
curl -X PUT -T files/test.jpg \
  -H "Content-Type: image/jpeg" \
  "PRESIGNED_URL_FROM_STEP_1"
```

3. **Verify the image was uploaded:**
```bash
aws s3 ls s3://dogs-images/users/ --recursive --endpoint-url=http://localhost:4566
```

## Troubleshooting

### LocalStack not accessible from Lambda
- Make sure you're using `host.docker.internal:4566` in your `env.json`
- For Linux, you might need to use your host machine's IP address instead

### Bucket doesn't exist error
- Make sure you've created the bucket before running your application
- Check that the bucket name matches exactly in your environment variables

### Presigned URL doesn't work
- Verify the S3 endpoint URL is correct
- Check that LocalStack is running and accessible on port 4566
- Make sure the Content-Type header matches exactly when uploading

## Cleanup

```bash
# Stop and remove LocalStack container
docker stop localstack
docker rm localstack

# If using docker-compose
docker-compose down -v
```

## Useful Commands

```bash
# Check LocalStack logs
docker logs localstack

# List all objects in bucket
aws s3 ls s3://dogs-images --recursive --endpoint-url=http://localhost:4566

# Download a file from S3
aws s3 cp s3://dogs-images/path/to/file.jpg ./downloaded-file.jpg --endpoint-url=http://localhost:4566

# Delete all objects in bucket
aws s3 rm s3://dogs-images --recursive --endpoint-url=http://localhost:4566
```