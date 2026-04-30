#!/bin/bash
set -euo pipefail

# ANSI colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔍 Starting local verification...${NC}"

# Check requirements
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ 'uv' is not installed. Please install it.${NC}"
    exit 1
fi

echo -e "${GREEN}🧹 Cleaning dist/...${NC}"
rm -rf dist/

echo -e "${GREEN}🔨 Building artifacts...${NC}"
uv build

echo -e "${GREEN}📝 Validating metadata...${NC}"
# Run with twine installed in ephemeral env
if ! uv run --with twine scripts/release/validate_metadata.py; then
    echo -e "${RED}❌ Metadata validation failed.${NC}"
    exit 1
fi

echo -e "${GREEN}🔥 Running smoke tests...${NC}"
# Run with pytest installed in ephemeral env
if ! uv run --with pytest pytest tests/smoke_test.py; then
    echo -e "${RED}❌ Smoke tests failed.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All verification steps passed!${NC}"
