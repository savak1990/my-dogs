# Image Uploader — Implementation Plan

This document is a step-by-step implementation plan for a two-project image uploader:

- Client: Flutter app (Android, iOS, Web) using Amplify v2 & Cognito for auth, with three pages:
  - Login page
  - Scrollable list of cards (name, age, image) with swipe-to-delete
  - Add modal to pick/upload image and metadata

- Backend: AWS SAM-based stack with API Gateway (Cognito auth), Lambda (proxy), DynamoDB, S3, and an asynchronous S3-event Lambda that uses Amazon Rekognition.

Goals
- Minimal viable product (MVP) end-to-end working with real AWS resources.
- Clear separation: Flutter client calls backend endpoints (authenticated), backend returns presigned URL and persists metadata.
- Simple, testable, and secure defaults for dev & `dev` stage deployment.

ASSUMPTIONS
- Single-user-per-Cognito identity (we store user_id from Cognito sub).
- Images are uploaded as binary files (jpg/png) via S3 pre-signed PUT URLs.
- Rekognition will be used with the DetectLabels API to confirm presence of a dog.
- We use Amplify v2 libraries on Flutter to handle Cognito auth and token management (or plain AWS Cognito SRP if you prefer manual integration).

CONTRACTS (API)

Base path: https://{api-id}.execute-api.{region}.amazonaws.com/dev

1) GET /users/{user_id}/dogs/upload-url
- Auth: Cognito (Authorization: Bearer id/access token)
- Query or body: none
- Response (200):
  {
    "uploadUrl": "https://s3-....",
    "objectKey": "uploads/{userId}/{uuid}.jpg",
    "expiresIn": 3600
  }

Notes: presigned URL will be a PUT URL that allows the client to upload the image. The objectKey returned must be saved by the client and later passed when POSTing metadata.

2) POST /users/{user_id}/dogs
- Auth: Cognito
- Body (application/json):
  {
    "name": "Fido",
    "age": 5,
    "image_key": "uploads/{userId}/{uuid}.jpg",
    "etag": "\"...\""  // optional: ETag returned by S3
  }
- Response (201): document created (DynamoDB item) or queued for processing.

3) GET /users/{user_id}/dogs
- Auth: Cognito
- Query params: optional pagination (limit, last_evaluated_key)
- Response (200): list of dogs for the calling user
  [ { "user_id": "...", "name": "Fido", "age": 5, "image_url": "https://...", "created_at": "..." }, ... ]

DATA SHAPE (DynamoDB)
- Table: Dogs
  - Partition key: user_id (string)
  - Sort key: name (string)
  - Attributes: dog_id (string, uuid), age (number), image_key (string), image_url (string), created_at (iso8601), rekognition_status (string: PENDING/VALIDATED/REJECTED), labels (list)

INFRASTRUCTURE (SAM)
- Resources required:
  - Cognito User Pool and App Client (or point the frontend to an existing pool)
  - API Gateway RestApi with a `dev` stage
  - Cognito Authorizer attached to API methods
  - Lambda: proxyHandler (python) for GET/POST /dogs and GET /dogs/upload-url
  - S3 Bucket: images-{{stack-name}}-dev with CORS and server-side encryption
  - DynamoDB Table: Dogs
  - Lambda: s3RekognitionHandler (python) — triggered by ObjectCreated:* on S3 bucket (async invocation)
  - IAM Roles / Policies: least-privilege to allow presign S3 put, put/get to S3, dynamo PutItem/GetItem/Query, rekognition:DetectLabels

High-level SAM template notes:
- Define RestApi with StageName: dev
- Attach AWS::Serverless::Function for proxy with API events for /dogs and /dogs/upload-url
- Add S3 bucket notification pointing to s3RekognitionHandler
- Use Outputs for API URL and Cognito IDs to wire to Flutter Amplify config

DEVELOPMENT STEPS (ordered)

Backend (SAM) — core first (local dev):
1. Initialize SAM project scaffold
   - Create python virtualenv for lambda code (keep dependencies minimal: boto3 (available in Lambda), requests if needed).
   - Init dogs_service with sam
   - Build dogs_service and try to invoke locally

2. Implement proxy lambda (python)
   - Handlers:
     - GET /dogs/upload-url: verify JWT, extract user sub (user_id), generate object key (userId/uuid), create presigned PUT URL using boto3 S3 client generate_presigned_url('put_object'), return uploadUrl + objectKey + expiresIn.
     - POST /dogs: validate body, write a DynamoDB item with rekognition_status=PENDING (image_url can be built from S3 bucket + key or left empty until Rekognition Lambda validates), return 201.
     - GET /dogs: query DynamoDB for items with partition key user_id, support pagination.
   - Input validation and error handling.

3. Implement S3 presigned URL behavior considerations
   - Presigned PUT doesn't set Content-Type; recommend client set proper Content-Type header.
   - Consider signing with fields if using POST instead of PUT; for simplicity use PUT.

4. Implement S3 -> Rekognition Lambda
   - Trigger: S3 ObjectCreated:* events
   - Behavior:
     - Download the object (or let Rekognition use S3 object reference) and call DetectLabels (min confidence configurable, e.g., 75%).
     - If a label 'Dog' (or similar) appears with confidence >= threshold, mark DynamoDB item rekognition_status=VALIDATED and set image_url to S3 public URL or a signed cloudfront url if you prefer.
     - If not detected, mark REJECTED and write labels and confidence for troubleshooting.
   - Permissions: rekognition:DetectLabels, dynamodb:UpdateItem, s3:GetObject (if required).

5. Local testing
   - Use `sam local start-api` for the REST endpoints.
   - For S3 and Rekognition local testing either:
     - Use real AWS dev account and deploy short-lived stack, or
     - Use LocalStack for S3 and DynamoDB emulation (Rekognition isn't available in LocalStack reliably — use real AWS for Rekognition testing).

Client (Flutter) — iterative MVP
6. Bootstrap Flutter app
   - Create Flutter project under `client/`.
   - Add Amplify v2 / Cognito dependencies and configure Amplify CLI or manual config. If using manual: use Cognito Hosted UI or native sign-in widgets.

7. Implement Authentication (Login Page)
   - Implement sign-in/sign-up flows using Amplify or Cognito SDK; on success store tokens (access/id) and call backend with Authorization header.

8. Implement Dog list page
   - After login, call GET /dogs to fetch user's dogs and render as scrollable list of cards.
   - Each card: image thumbnail (from S3 public URL or signed URL), name, age; enable swipe-to-delete to call backend delete (optional for MVP) or simply remove locally (if you add DELETE later implement in SAM/Lambda).

9. Implement Add modal (image picker + metadata)
   - UI: fields for name, numeric age, image picker (gallery/camera for mobile; file picker for web).
   - On Submit: run upload flow below.

Client upload flow (3 steps — exactly as requested)
1) Call GET /dogs/upload-url
   - Obtain uploadUrl, objectKey
2) Upload file to presigned URL (HTTP PUT)
   - Ensure correct Content-Type header and binary body
   - Capture response headers such as ETag
3) Call POST /dogs
   - Send { name, age, image_key: objectKey, etag }
   - On success close modal and optimistically add item to list (rekognition validation may happen async)

DEV / RUN COMMANDS (examples)
- Backend local API: sam build && sam local start-api --template template.yaml
- Deploy: sam deploy --guided (use stack name `image-uploader-dev`), or scripted in CI
- Flutter run (client):
  - Mobile: flutter run -d <device>
  - Web: flutter run -d chrome

TESTING
- Backend unit tests: pytest for Lambda handlers; mock boto3 with `moto` for S3/DynamoDB where appropriate. (Rekognition tests should be integration tests against AWS).
- Integration test: full E2E against a dev AWS account (deploy SAM stack to `dev`) and run the Flutter client against it.
- Flutter: widget tests for list and add modal; integration tests for auth flow using mocked Cognito or Amplify local mocks.

EDGE CASES & NOTES
- Auth failures: return 401 for unauthenticated requests. Validate tokens using Cognito authorizer in API Gateway or validate in Lambda.
- Upload errors: clients should retry failed PUT uploads; server must validate POST /dogs only accepts known objectKey prefixes (no arbitrary buckets).
- Incomplete uploads: DynamoDB entry created with rekognition_status=PENDING until Rekognition Lambda updates it.
- Large images: consider resizing on client or use a Lambda to create thumbnails. Be mindful of S3 object size limits and Rekognition image size limits.
- Concurrency: DynamoDB updates must use conditional writes if you later allow updates.

SECURITY & IAM
- Principle of least privilege for Lambdas. Sample permissions:
  - ProxyLambdaRole: s3:PutObject? No — only generate presigned URL (no S3 put permission required if presign uses backend credentials), s3:PutObject may be needed if you want server-side copy/validation. DynamoDB PutItem/Query limited to the Dogs table.
  - RekognitionLambdaRole: rekognition:DetectLabels, dynamodb:UpdateItem, s3:GetObject.
- S3 bucket: block public access; make objects private by default; provide either signed URLs for image delivery or make a small CloudFront distribution or enable S3 public read only if acceptable for the project.

QUALITY GATES
- Build: sam build (PASS)
- Lint: flake8 for python lambdas; dart analyze for Flutter
- Unit tests: minimal set to cover handlers (happy path + auth failure + invalid input)
- Integration smoke: deploy to `dev` and execute upload flow end-to-end

OBSERVABILITY
- Add CloudWatch Logs for Lambdas; structured logging (JSON) with correlation ids (request id and user id).
- Add CloudWatch metric/Alarm for Rekognition rejects exceeding X%.

TIMELINE / SIZING (rough)
- Day 1: SAM scaffold, proxy lambda core endpoints, local tests for GET/POST /dogs and presign URL
- Day 2: Implement S3 event lambda + Rekognition logic, DynamoDB schema and tests
- Day 3: Flutter client scaffold, Amplify auth wiring and simple login page
- Day 4: Implement list page, add modal and upload flow; integration testing
- Day 5: polish, deploy to dev, document and CI

NEXT STEPS (immediately actionable)
1. Create repo structure: `client/` and `backend/` with README placeholders.
2. Add `template.yaml` skeleton and a minimal `proxy_handler.py` (stub) to enable `sam local start-api`.
3. Start Flutter app scaffold in `client/` and wire dev auth to a test Cognito user pool.

AMPLIFY (Flutter) DEPLOYMENT — DEV ENVIRONMENT
If you'd like the Flutter application deployed to AWS using Amplify with a `dev` environment, follow these steps as part of the client work:

1. Install and configure Amplify CLI locally (if not already):
  - `npm install -g @aws-amplify/cli`
  - `amplify configure` to set up your AWS profile and default region

2. Initialize Amplify in the Flutter project:
  - From `client/` run `amplify init` and choose a name, environment `dev`, and your AWS profile. Select `javascript` framework when asked (Amplify Flutter uses JS tooling for hosting), then accept defaults for build settings or customize for Flutter web.

3. Add authentication and API to the Amplify project (optional if SAM creates Cognito manually):
  - `amplify add auth` — if you want Amplify-managed Cognito (easier for dev).
  - `amplify add hosting` — choose `Amplify Console` for continuous deployment or `S3 and CloudFront` for a manual publish.

4. Publish (host) the Flutter web build (for web target) or use Amplify for mobile distribution configuration:
  - Build web: `flutter build web`
  - Then `amplify publish` to upload hosting artifacts to Amplify Console (dev environment). Amplify Console will provide a URL for the hosted web app.

5. CI/CD: Connect your repo in Amplify Console to enable automatic builds on pushes to `main` or `dev` branches. Configure build settings for Flutter (install SDK, run `flutter build web`, then publish `amplify publish`).

6. Wiring to backend: If you use Amplify-managed auth and API, Amplify will update `amplify/backend` and the generated config; otherwise, after deploying the SAM backend, update the Flutter app's configuration with the Cognito User Pool IDs and API Gateway endpoints (typically put into `lib/config.dart` or Amplify `amplifyconfiguration.dart`).

Notes:
- For mobile (iOS/Android) you still use Amplify for auth (Cognito) but host the app via Play/AppStore or use Amplify's distribution workflows. For dev purposes, hosting web is the fastest way to expose the UI.
- If you prefer using SAM-created Cognito and API Gateway, skip `amplify add auth` and instead configure the Flutter app to use the Cognito pool/app client IDs created by SAM.


Appendix: Useful snippets and links
- S3 generate_presigned_url (boto3) — use Client('s3').generate_presigned_url('put_object', Params={'Bucket': bucket,'Key': key}, ExpiresIn=3600)
- Rekognition: client.detect_labels(Image={'S3Object':{'Bucket':bucket,'Name':key}}, MinConfidence=75)

---

If you want, I can now scaffold the repo (`client/` + `backend/`), create the SAM `template.yaml` skeleton and a minimal Python proxy lambda stub so you can run `sam local start-api` immediately. Say "scaffold backend" or "scaffold full repo" and I'll start the next task.
