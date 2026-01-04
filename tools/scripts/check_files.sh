#!/bin/bash

# check_files.sh
# Verifies all required manufacturing files are present

echo "🔍 Checking Manufacturing Files..."
echo ""

# Navigate to project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

ERRORS=0
WARNINGS=0

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Check function
check_file() {
    local path=$1
    local description=$2
    local required=$3

    if [ -d "$path" ]; then
        if [ "$(ls -A $path 2>/dev/null)" ]; then
            echo -e "${GREEN}✓${NC} $description"
            return 0
        fi
    elif [ -f "$path" ]; then
        echo -e "${GREEN}✓${NC} $description"
        return 0
    fi

    if [ "$required" = "required" ]; then
        echo -e "${RED}✗${NC} $description (REQUIRED)"
        ((ERRORS++))
    else
        echo -e "${YELLOW}⚠${NC} $description (recommended)"
        ((WARNINGS++))
    fi
    return 1
}

echo "=== Hardware Files ==="
check_file "hardware/altium/*.PrjPcb" "Altium project file" "optional"
check_file "hardware/kicad/*.kicad_pro" "KiCad project file" "optional"
check_file "hardware/manufacturing/gerbers" "Gerber files" "required"
check_file "hardware/manufacturing/drill" "Drill files" "required"
check_file "hardware/manufacturing/bom" "BOM (Bill of Materials)" "required"
check_file "hardware/manufacturing/cpl" "CPL (Pick-and-Place)" "required"

echo ""
echo "=== Mechanical Files ==="
check_file "mechanical/stl" "STL files for 3D printing" "optional"
check_file "mechanical/step" "STEP files" "optional"

echo ""
echo "=== Documentation ==="
check_file "README.md" "README" "required"
check_file ".claude.md" "Claude context file" "required"
check_file "CHANGELOG.md" "Changelog" "recommended"
check_file "docs" "Documentation folder" "recommended"

echo ""
echo "=== Git ==="
if [ -d ".git" ]; then
    echo -e "${GREEN}✓${NC} Git repository initialized"

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        echo -e "${YELLOW}⚠${NC} Uncommitted changes present"
        ((WARNINGS++))
    else
        echo -e "${GREEN}✓${NC} No uncommitted changes"
    fi

    # Check for version tags
    if git tag | grep -q "v[0-9]"; then
        LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null)
        echo -e "${GREEN}✓${NC} Version tags found (latest: $LATEST_TAG)"
    else
        echo -e "${YELLOW}⚠${NC} No version tags (recommended)"
        ((WARNINGS++))
    fi
else
    echo -e "${RED}✗${NC} Git repository not initialized (REQUIRED)"
    ((ERRORS++))
fi

echo ""
echo "=== Manufacturing Readiness Check ==="

# Count files
GERBER_COUNT=$(find hardware/manufacturing/gerbers -type f 2>/dev/null | wc -l | tr -d ' ')
DRILL_COUNT=$(find hardware/manufacturing/drill -type f -name "*.drl" 2>/dev/null | wc -l | tr -d ' ')
BOM_COUNT=$(find hardware/manufacturing/bom -type f -name "*.csv" 2>/dev/null | wc -l | tr -d ' ')
CPL_COUNT=$(find hardware/manufacturing/cpl -type f -name "*.csv" 2>/dev/null | wc -l | tr -d ' ')

echo "📊 File counts:"
echo "   Gerber files: $GERBER_COUNT (expect ~12-25)"
echo "   Drill files: $DRILL_COUNT (expect 1-2)"
echo "   BOM files: $BOM_COUNT (expect 1)"
echo "   CPL files: $CPL_COUNT (expect 1)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "🚀 Ready to run: ./tools/scripts/prepare_manufacturing.sh"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  $WARNINGS warnings found${NC}"
    echo ""
    echo "You can proceed, but consider addressing warnings."
else
    echo -e "${RED}❌ $ERRORS errors found${NC}"
    [ $WARNINGS -gt 0 ] && echo -e "${YELLOW}⚠️  $WARNINGS warnings found${NC}"
    echo ""
    echo "Fix errors before manufacturing."
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
