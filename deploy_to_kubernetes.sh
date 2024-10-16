#!/bin/bash

# Variables for Kubernetes deployment
NAMESPACE="your-namespace"
DEPLOYMENT_FILE="k8s-deployment.yaml"
KUBE_CONTEXT="your-cluster-context"

# Set the Kubernetes context
echo "Setting Kubernetes context to ${KUBE_CONTEXT}..."
kubectl config use-context ${KUBE_CONTEXT}

# Create the namespace if it doesn't exist
echo "Creating Kubernetes namespace if not exists..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Deploy to Kubernetes
echo "Deploying to Kubernetes cluster..."
kubectl apply -f ${DEPLOYMENT_FILE} -n ${NAMESPACE}

echo "Deployment successful!"
