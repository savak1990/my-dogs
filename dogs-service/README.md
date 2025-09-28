# Dogs Image Upload Service Backend

A serverless backend service for managing user dog profiles and image uploads. This service provides REST APIs for creating dog profiles, uploading images, and retrieving dog information with their associated images.

## Architecture

This service is built using AWS serverless architecture with the following components:

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client    │────│  API Gateway    │────│  Lambda         │
│             │    │                 │    │  (Python 3.13) │
└─────────────┘    └─────────────────┘    └─────────────────┘
                                                     │
                                                     │
                   ┌─────────────────┐              │
                   │    DynamoDB     │◄─────────────┤
                   │   Dogs Table    │              │
                   └─────────────────┘              │
                                                     │
                   ┌─────────────────┐              │
                   │       S3        │◄─────────────┘
                   │ Images Bucket   │
                   └─────────────────┘
```

### Component Details

- **API Gateway**: Handles HTTP requests and routes them to Lambda functions
- **Lambda Function**: Contains the business logic, written in Python 3.13
  - Uses AWS Lambda Powertools for structured logging, tracing, and validation
  - Handles CRUD operations for dogs and image upload coordination
- **DynamoDB**: NoSQL database storing dog information and image metadata
  - Uses composite keys: `PK=USER#<user_id>`, `SK=DOG#<dog_id>` or `IMAGE#<dog_id>#<image_id>`
- **S3 Bucket**: Stores actual dog images
  - Generates presigned URLs for secure direct uploads
  - CORS-enabled for browser uploads

### Data Flow

1. **Dog Management**: Dogs are stored in DynamoDB with user association
2. **Image Upload Process**:
   - Client requests image upload placeholder via API
   - Service generates presigned S3 URL and creates pending image record
   - Client uploads directly to S3 using presigned URL
   - S3 notifications (future enhancement) can trigger image processing
   - Image status updates reflect upload and processing state

### API Endpoints

- `GET /health` - Service health check
- `POST /users/{user_id}/dogs` - Create a new dog profile
- `GET /users/{user_id}/dogs` - List all dogs for a user
- `POST /users/{user_id}/dogs/{dog_id}/images` - Create image upload placeholder and get presigned URL

## API Usage Examples

Below are curl examples demonstrating the main workflow for using this service:

### Prerequisites

Replace `$API_BASE_URL` with your actual API Gateway endpoint URL:

```bash
export API_BASE_URL="https://your-api-id.execute-api.region.amazonaws.com/Prod"
export USER_ID="550e8400-e29b-41d4-a716-446655440000"
```

### 1. Health Check

First, verify the service is running:

```bash
curl -X GET "$API_BASE_URL/health" \
  -H "Accept: application/json" | json_pp
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "dogs-service",
  "timestamp": "2025-09-27T10:30:00Z"
}
```

### 2. Create a Dog Profile

Create a new dog profile for a user:

```bash
curl -X POST "$API_BASE_URL/users/$USER_ID/dogs" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "name": "Buddy",
    "age": 3
  }' | json_pp
```

**Expected Response:**
```json
{
  "dog_id": 1,
  "name": "Buddy",
  "age": 3
}
```

### 3. List User's Dogs

Retrieve all dogs for the user (should show the newly created dog):

```bash
curl -X GET "$API_BASE_URL/users/$USER_ID/dogs" \
  -H "Accept: application/json" | json_pp
```

**Expected Response:**
```json
[
  {
    "dog_id": 1,
    "name": "Buddy",
    "age": 3,
    "images": []
  }
]
```

### 4. Upload Dog Image

Create an image upload placeholder and get presigned URL:

```bash
curl -X POST "$API_BASE_URL/users/$USER_ID/dogs/1/images" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "image_extension": "jpg"
  }' | json_pp
```

**Expected Response:**
```json
{
  "image_id": 1,
  "method": "PUT",
  "presigned_url": "https://your-bucket.s3.amazonaws.com/path/to/image?signed-params...",
  "expires_in": 3600,
  "headers": null,
  "max_size": null
}
```

### 5. Upload Image to S3

Use the presigned URL to upload your image directly to S3:

```bash
curl -X PUT "PRESIGNED_URL_FROM_STEP_4" \
  -H "Content-Type: image/jpeg" \
  --data-binary @/path/to/your/dog-image.jpg
```

### 6. Verify Image Upload

List the user's dogs again to see the uploaded image:

```bash
curl -X GET "$API_BASE_URL/users/$USER_ID/dogs" \
  -H "Accept: application/json" | json_pp
```

**Expected Response:**
```json
[
  {
    "dog_id": 1,
    "name": "Buddy",
    "age": 3,
    "images": [
      {
        "image_id": "1",
        "status": "pending"
      }
    ]
  }
]
```

## Environment Variables

The service uses the following environment variables:

- `DOGS_TABLE_NAME`: DynamoDB table name for storing dog data
- `DOGS_IMAGES_BUCKET`: S3 bucket name for storing images
- `POWERTOOLS_SERVICE_NAME`: Service name for logging/tracing
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `DYNAMODB_ENDPOINT`: DynamoDB endpoint (for local development)
- `S3_ENDPOINT`: S3 endpoint (for local development)
- `S3_PRESIGN_ENDPOINT`: S3 endpoint for presigned URLs

## Development

### Local Development

The service includes scripts and configuration for local development using LocalStack:

1. Start LocalStack services
2. Run `./scripts/setup_local.sh` to set up local AWS resources
3. Use the provided event files in `events/` directory for testing

### Testing

Run unit tests:
```bash
cd tests
python -m pytest unit/
```

Run integration tests:
```bash
python -m pytest integration/
```

### Deployment

Deploy using AWS SAM:

```bash
sam build
sam deploy --guided
```

## Image Status Lifecycle

Images go through the following statuses:

- `pending`: Image placeholder created, awaiting upload
- `uploaded`: Image successfully uploaded to S3
- `ready`: Image processed and ready for use
- `rejected`: Image rejected due to content policy
- `failed`: Processing failed
- `deleted`: Image deleted

## Error Handling

The API returns standard HTTP status codes:

- `200`: Success
- `201`: Created
- `400`: Bad Request (validation errors)
- `404`: Not Found
- `500`: Internal Server Error
- `503`: Service Unavailable (health check failed)

Error responses include detailed error messages and request correlation IDs for debugging.