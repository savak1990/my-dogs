# Dogs Image Upload Service Backend

A serverless backend service for managing user dog profiles and image uploads with automated image processing. This service provides REST APIs for creating dog profiles, uploading images, and retrieving dog information with their associated images. Images are automatically processed upon upload using event-driven Lambda functions.

## Architecture

This service is built using AWS serverless architecture with the following components:

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client    │────│  API Gateway    │────│  Dogs Service   │
│             │    │                 │    │  Lambda         │
└─────────────┘    └─────────────────┘    │  (Python 3.13) │
                                           └─────────┬───────┘
                                                     │
                   ┌─────────────────────────────────┼─────────────────┐
                   │          Common Layer           │                 │
                   │  (AWS Powertools, Pydantic,     │                 │
                   │   Config, Logger, Tracer)       │                 │
                   └─────────────────────────────────┼─────────────────┘
                                                     │                 │
                   ┌─────────────────┐              │                 │
                   │    DynamoDB     │◄─────────────┤                 │
                   │   Dogs Table    │              │                 │
                   └─────────────────┘              │                 │
                                                     │                 │
                   ┌─────────────────┐              │    ┌────────────▼──────────┐
                   │       S3        │◄─────────────┘    │  Dogs Image Processor │
                   │ Images Bucket   │                   │  Lambda (Python 3.13) │
                   └─────────┬───────┘                   └───────────────────────┘
                             │                                       ▲
                             │ S3 Events                             │
                             │ (PUT/DELETE)                          │
                             └───────────────────────────────────────┘
```

### Component Details

- **API Gateway**: Handles HTTP requests and routes them to Lambda functions
- **Dogs Service Lambda**: Contains the main business logic, written in Python 3.13
  - Handles CRUD operations for dogs and image upload coordination
  - Uses the shared Common Layer for utilities and configuration
- **Dogs Image Processor Lambda**: Handles S3 event-driven image processing, written in Python 3.13
  - Triggered automatically on S3 object creation (PUT) and deletion events
  - Processes uploaded images and updates their status in DynamoDB
  - Uses the shared Common Layer for utilities and configuration
- **Common Layer**: Shared AWS Lambda Layer containing:
  - AWS Lambda Powertools for structured logging, tracing, and validation
  - Pydantic for data validation and settings management
  - Shared configuration, logger, and tracer instances
  - Common utilities used by both Lambda functions
- **DynamoDB**: NoSQL database storing dog information and image metadata
  - Uses composite keys: `PK=USER#<user_id>`, `SK=DOG#<dog_id>` or `IMAGE#<dog_id>#<image_id>`
- **S3 Bucket**: Stores actual dog images
  - Generates presigned URLs for secure direct uploads
  - CORS-enabled for browser uploads
  - Configured with event notifications to trigger image processing

### Data Flow

1. **Dog Management**: Dogs are stored in DynamoDB with user association
2. **Image Upload Process**:
   - Client requests image upload placeholder via API
   - Dogs Service generates presigned S3 URL and creates pending image record in DynamoDB
   - Client uploads directly to S3 using presigned URL
   - S3 automatically triggers Dogs Image Processor Lambda on object creation/deletion
   - Image Processor Lambda processes the uploaded image and updates status in DynamoDB
   - Image status progresses through lifecycle states (pending → uploaded → processed → ready)

### API Endpoints

- `GET /health` - Service health check
- `POST /users/{user_id}/dogs` - Create a new dog profile
- `GET /users/{user_id}/dogs` - List all dogs for a user
- `POST /users/{user_id}/dogs/{dog_id}/images` - Create image upload placeholder and get presigned URL

### Shared Dependencies and Architecture

The service uses a layered architecture with a Common Layer that provides:

- **AWS Lambda Powertools**: Structured logging, distributed tracing, and metrics
- **Pydantic**: Data validation, settings management, and type safety
- **Shared Configuration**: Centralized environment variable management
- **Observability**: Common logger and tracer instances across both Lambda functions

This approach ensures:
- Consistent logging and tracing across all Lambda functions
- Reduced deployment package size by sharing common dependencies
- Centralized configuration management
- Easier maintenance and updates of shared utilities

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

### 6. Verify Image Upload and Processing

List the user's dogs again to see the uploaded image and its processing status:

```bash
curl -X GET "$API_BASE_URL/users/$USER_ID/dogs" \
  -H "Accept: application/json" | json_pp
```

**Expected Response (after automatic processing):**
```json
[
  {
    "dog_id": 1,
    "name": "Buddy",
    "age": 3,
    "images": [
      {
        "image_id": "1",
        "status": "uploaded"
      }
    ]
  }
]
```

**Note**: The image status will automatically progress from `pending` → `uploaded` → `ready` as the Dogs Image Processor Lambda handles the S3 events and processes the uploaded image.

## Environment Variables

The service uses the following environment variables, with core configuration managed through the Common Layer:

### Core Configuration (Common Layer)
- `POWERTOOLS_SERVICE_NAME`: Service name for logging/tracing (dogs-service or dogs-image-processor)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `DOGS_TABLE_NAME`: DynamoDB table name for storing dog data
- `DOGS_IMAGES_BUCKET`: S3 bucket name for storing images

### Upload Configuration
- `IMAGE_UPLOAD_EXPIRATION_SECS`: Presigned URL expiration time (default: 3600 seconds)
- `IMAGE_UPLOAD_MAX_SIZE`: Maximum image upload size (default: 5MB)
- `SUPPORTED_IMAGE_EXTENSIONS`: Allowed image file extensions (jpg, jpeg, png, webp)

### Development/Local Testing
- `DYNAMODB_ENDPOINT`: DynamoDB endpoint (for local development with LocalStack)
- `S3_ENDPOINT`: S3 endpoint (for local development with LocalStack)
- `S3_PRESIGN_ENDPOINT`: S3 endpoint for presigned URLs (defaults to S3_ENDPOINT if not set)

**Note**: Configuration, logging, and tracing are centralized in the Common Layer using Pydantic for settings management and AWS Powertools for observability. Both Lambda functions share the same configuration through the layer.

## Development

### Local Development

The service includes scripts and configuration for local development using LocalStack:

1. Start LocalStack services
2. Run `./scripts/setup_local.sh` to set up local AWS resources
3. Use the provided event files in `events/` directory for testing both Lambda functions:
   - API Gateway events for the Dogs Service Lambda
   - S3 events (`s3_put_image_ev.json`, `s3_delete_image_ev.json`) for the Image Processor Lambda

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

The deployment will create both Lambda functions with the shared Common Layer, configure S3 event triggers, and set up all necessary IAM permissions.

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