#!/bin/bash

# Variables for testing
NAMESPACE="your-namespace"
POD_NAME="your-pod-name"

# Check if pods are running
echo "Checking pod status..."
kubectl get pods -n ${NAMESPACE}

# Verify if pod is healthy
POD_STATUS=$(kubectl get pod ${POD_NAME} -n ${NAMESPACE} -o jsonpath="{.status.phase}")
if [ "${POD_STATUS}" == "Running" ]; then
    echo "Pod ${POD_NAME} is running successfully!"
else
    echo "Pod ${POD_NAME} is not running. Please check the logs."
    exit 1
fi
