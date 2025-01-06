#!/bin/bash

# Export AWS credentials from .env
export CUSTOM_AWS_ACCESS_KEY_ID=$(grep CUSTOM_AWS_ACCESS_KEY_ID .env | cut -d '=' -f2)
export CUSTOM_AWS_SECRET_ACCESS_KEY=$(grep CUSTOM_AWS_SECRET_ACCESS_KEY .env | cut -d '=' -f2)
export CUSTOM_AWS_REGION_NAME=$(grep CUSTOM_AWS_REGION_NAME .env | cut -d '=' -f2)

# Start litellm server
echo "Starting litellm server..."
nohup poetry run litellm --config litellm.config.yaml > nohup.litellm.out 2>&1 &

# Wait for litellm to start (adjust sleep time if needed)
sleep 15

# Start main application
echo "Starting main application..."
nohup poetry run python main.py > nohup.main.out 2>&1 &

echo "Both services started. Check nohup.litellm.out and nohup.main.out for logs." 