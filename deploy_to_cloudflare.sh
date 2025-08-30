#!/bin/bash
# CloudFlare Pages Deployment Script for Enhanced Crypto Trading Bot Control UI
# As recommended by ChatGPT-5 Pro for production deployment

set -e

echo "🚀 Deploying Enhanced Crypto Trading Bot Control UI to CloudFlare Pages..."
echo "=================================================================="

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "📦 Installing Wrangler CLI..."
    npm install -g wrangler
fi

# Login to CloudFlare (if not already logged in)
echo "🔐 Checking CloudFlare authentication..."
if ! wrangler whoami &> /dev/null; then
    echo "Please login to CloudFlare:"
    wrangler login
fi

# Prepare frontend files
echo "📁 Preparing frontend files for deployment..."
mkdir -p dist
cp -r control_ui/frontend/* dist/
cp _headers dist/
cp _redirects dist/

# Deploy to CloudFlare Pages
echo "☁️ Deploying to CloudFlare Pages..."
wrangler pages deploy dist --project-name crypto-trading-bot-control-ui --compatibility-date 2023-08-30

echo "✅ Deployment complete!"
echo "🌐 Your enhanced crypto trading bot control UI is now available on CloudFlare Pages"
echo "📊 Access your dashboard at: https://crypto-trading-bot-control-ui.pages.dev"
echo ""
echo "🛡️ Features deployed:"
echo "  - Real-time portfolio monitoring"
echo "  - Risk parameter controls"  
echo "  - Emergency stop functionality"
echo "  - Modern glass morphism UI"
echo "  - Enhanced security headers"
echo ""
echo "💡 Next steps:"
echo "  1. Configure custom domain (optional)"
echo "  2. Set up API backend URL in CloudFlare environment variables"
echo "  3. Update CORS settings if needed"