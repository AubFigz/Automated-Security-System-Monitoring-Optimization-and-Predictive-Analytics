#!/bin/bash

# Variables for cleanup
NAMESPACE="your-namespace"
DEPLOYMENT_NAME="your-deployment-name"
DOCKER_REGISTRY="your-registry-url"
IMAGE_NAME="your-docker-image"
IMAGE_TAG="latest"

# Delete Kubernetes deployment
echo "Cleaning up Kubernetes deployment..."
kubectl delete deployment ${DEPLOYMENT_NAME} -n ${NAMESPACE}

# Remove old Docker images from the registry
echo "Cleaning up Docker images from registry..."
docker rmi ${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}

echo "Cleanup complete!"
