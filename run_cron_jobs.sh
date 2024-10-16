#!/bin/bash

# Variables for Kubernetes CronJob
NAMESPACE="your-namespace"
CRONJOB_FILE="cronjob.yaml"

# Set the Kubernetes context
echo "Deploying CronJobs to Kubernetes..."
kubectl apply -f ${CRONJOB_FILE} -n ${NAMESPACE}

echo "CronJob deployment successful!"
