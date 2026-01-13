#!/bin/bash
# Deploy script for updating Airflow on EC2
#
# Usage: ./scripts/deploy.sh [--rebuild]
#
# Options:
#   --rebuild   Rebuild Docker images (needed if src/ changed)
#
# Prerequisites:
#   - SSH key at ~/.ssh/reddit-airflow-key.pem
#   - terraform output to get the IP

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get EC2 IP from Terraform output
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/../terraform"

if [ ! -f "$TERRAFORM_DIR/terraform.tfstate" ]; then
    echo -e "${RED}Error: No terraform state found. Run 'terraform apply' first.${NC}"
    exit 1
fi

EC2_IP=$(cd "$TERRAFORM_DIR" && terraform output -raw elastic_ip 2>/dev/null)
KEY_NAME=$(cd "$TERRAFORM_DIR" && terraform output -raw ssh_command | grep -oP '(?<=-i ~/.ssh/)[^.]+')

if [ -z "$EC2_IP" ]; then
    echo -e "${RED}Error: Could not get EC2 IP from terraform output.${NC}"
    exit 1
fi

SSH_KEY="$HOME/.ssh/${KEY_NAME}.pem"
SSH_CMD="ssh -i $SSH_KEY ec2-user@$EC2_IP"

echo -e "${GREEN}Deploying to EC2 at $EC2_IP${NC}"

# Check if rebuild flag is set
REBUILD=false
if [ "$1" == "--rebuild" ]; then
    REBUILD=true
    echo -e "${YELLOW}Rebuild mode: Will rebuild Docker images${NC}"
fi

# Execute deployment commands on EC2
echo -e "${GREEN}1. Pulling latest code...${NC}"
$SSH_CMD "cd /opt/reddit-recommendation && git pull"

if [ "$REBUILD" = true ]; then
    echo -e "${GREEN}2. Rebuilding Docker images...${NC}"
    $SSH_CMD "cd /opt/reddit-recommendation/airflow && \
        docker compose -f docker-compose.yaml -f docker-compose.prod.yaml build --no-cache"
fi

echo -e "${GREEN}3. Restarting services...${NC}"
$SSH_CMD "cd /opt/reddit-recommendation/airflow && \
    docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d"

echo -e "${GREEN}4. Checking service status...${NC}"
$SSH_CMD "docker ps"

echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo -e "Airflow UI: http://$EC2_IP:8080"
