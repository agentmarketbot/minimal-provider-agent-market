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

# Start market scan process
echo "Starting market scan process..."
nohup poetry run python src/market_scan_process.py > nohup.market_scan.out 2>&1 &

# Start solve instances process
echo "Starting solve instances process..."
nohup poetry run python src/solve_instances_process.py > nohup.solve_instances.out 2>&1 &

echo "All services started. Check the following log files:"
echo "- nohup.litellm.out for LiteLLM logs"
echo "- nohup.market_scan.out for market scanning logs"
echo "- nohup.solve_instances.out for instance solving logs" 