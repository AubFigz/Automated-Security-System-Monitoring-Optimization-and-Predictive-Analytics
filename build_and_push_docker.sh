#!/bin/bash

# Variables for image name and tag
IMAGE_NAME="your-docker-image"
IMAGE_TAG="latest"
DOCKER_REGISTRY="your-registry-url"

# Build the Docker image
echo "Building Docker image..."
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

# Authenticate with Docker registry
echo "Authenticating with Docker registry..."
docker login ${DOCKER_REGISTRY} -u "$DOCKER_USERNAME" -p "$DOCKER_PASSWORD"

# Tag and push the image to the registry
echo "Pushing Docker image to the registry..."
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
docker push ${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}

echo "Docker image ${IMAGE_NAME}:${IMAGE_TAG} pushed successfully!"
