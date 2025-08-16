#!/usr/bin/env bash
set -euo pipefail

# One-command installer for Our-project-1
# Creates/updates repo worldpath/Our-project-1 with Azure OIDC CI/CD pipeline.

ORG="worldpath"
REPO="Our-project-1"
BRANCH="main"

echo "Cloning $ORG/$REPO ..."
if ! gh repo view "$ORG/$REPO" >/dev/null 2>&1; then
  gh repo create "$ORG/$REPO" --private --confirm
fi

gh repo clone "$ORG/$REPO"
cd "$REPO"
git checkout -B "$BRANCH"

# Ensure workflow exists
mkdir -p .github/workflows
cat > .github/workflows/deploy.yml <<'YAML'
name: build-and-deploy
on:
  push:
    branches: [ "main" ]
  workflow_dispatch:
permissions:
  id-token: write
  contents: read
jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Azure login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - name: Build and push image
        run: |
          az acr login --name ${{ vars.ACR_NAME }}
          docker build -t ${{ vars.REGISTRY }}/${{ vars.IMAGE_NAME }}:${{ github.sha }} .
          docker push ${{ vars.REGISTRY }}/${{ vars.IMAGE_NAME }}:${{ github.sha }}
      - name: Deploy infra (Bicep)
        uses: azure/cli@v2
        with:
          inlineScript: |
            az deployment group create -g ${{ vars.RESOURCE_GROUP }}               --template-file infra/main.bicep               --parameters location=${{ vars.AZURE_LOCATION }} acrName=${{ vars.ACR_NAME }}               --parameters containerImage=${{ vars.REGISTRY }}/${{ vars.IMAGE_NAME }}:${{ github.sha }}
YAML

git add .github/workflows/deploy.yml
git commit -m "Add Azure OIDC workflow" || true
git push -u origin "$BRANCH"

echo "Installer complete. Check GitHub Actions for deployment run."
