def lambda_handler(event, context):
    print("Processing dog image...")
    
    print(f"Event: {event}")
    
    return {
        'statusCode': 200,
        'body': 'Image processed successfully'
    }