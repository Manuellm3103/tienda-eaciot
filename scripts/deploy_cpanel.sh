#!/bin/bash
# Complete deployment script for cPanel (Hostgator)

set -e

echo "=========================================="
echo "  TIENDA EACIOT - CPANEL DEPLOYMENT"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}ERROR: .env file not found${NC}"
    echo "Run: python scripts/setup_free_services.py"
    exit 1
fi

echo -e "${YELLOW}Step 1: Installing dependencies...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

echo -e "${YELLOW}Step 2: Running migrations...${NC}"
alembic upgrade head
echo -e "${GREEN}✓ Migrations completed${NC}"

echo -e "${YELLOW}Step 3: Creating directories...${NC}"
mkdir -p uploads
mkdir -p backups
mkdir -p logs
echo -e "${GREEN}✓ Directories created${NC}"

echo -e "${YELLOW}Step 4: Setting permissions...${NC}"
chmod 755 uploads
chmod 755 backups
chmod 755 logs
echo -e "${GREEN}✓ Permissions set${NC}"

echo -e "${YELLOW}Step 5: Verifying installation...${NC}"
python -c "from app.main import app; print('✓ App imports OK')"
python -c "from app.database import engine; print('✓ Database OK')"

echo ""
echo "=========================================="
echo -e "${GREEN}  DEPLOYMENT COMPLETED!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Create admin user:"
echo "   python scripts/create_admin.py admin@eaciot.com YOUR_PASSWORD"
echo ""
echo "2. Setup free services (if not done):"
echo "   python scripts/setup_free_services.py"
echo ""
echo "3. Configure cPanel:"
echo "   - Setup Python App"
echo "   - Configure .htaccess"
echo "   - Add cron jobs"
echo ""
echo "4. Test your store:"
echo "   curl https://tienda.eaciot.com/health"
echo ""
