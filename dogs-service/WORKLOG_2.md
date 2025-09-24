# Step 2 

Now need to rename my hello-world example created from the template to the actual DogsService naming.

Renamed HelloWorld to DogsService and added /users/{user_id}/dogs path for GET and POST methods.

Deleted .aws-sam folder

Re-run sam build

sam local start-api

curl http://localhost/users/{user_id}/dogs