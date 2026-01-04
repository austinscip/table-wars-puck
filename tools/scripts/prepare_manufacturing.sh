#!/bin/bash

# prepare_manufacturing.sh
# Prepares all manufacturing files for upload to PCB manufacturer

set -e  # Exit on error

echo "🔧 Preparing Manufacturing Files..."
echo ""

# Navigate to project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="hardware/manufacturing/outputs"
mkdir -p "$OUTPUT_DIR"

# === 1. ZIP GERBERS ===
echo "📦 Zipping Gerber files..."
if [ -d "hardware/manufacturing/gerbers" ] && [ "$(ls -A hardware/manufacturing/gerbers)" ]; then
    cd hardware/manufacturing
    zip -q "outputs/gerbers_${TIMESTAMP}.zip" gerbers/*
    echo "   ✓ Created: outputs/gerbers_${TIMESTAMP}.zip"
    cd "$PROJECT_ROOT"
else
    echo "   ⚠️  No Gerber files found in hardware/manufacturing/gerbers/"
fi

# === 2. ZIP DRILL FILES ===
echo ""
echo "📦 Zipping Drill files..."
if [ -d "hardware/manufacturing/drill" ] && [ "$(ls -A hardware/manufacturing/drill)" ]; then
    cd hardware/manufacturing
    zip -q "outputs/drill_${TIMESTAMP}.zip" drill/*
    echo "   ✓ Created: outputs/drill_${TIMESTAMP}.zip"
    cd "$PROJECT_ROOT"
else
    echo "   ⚠️  No Drill files found in hardware/manufacturing/drill/"
fi

# === 3. COPY BOM ===
echo ""
echo "📋 Preparing BOM..."
if [ -f "hardware/manufacturing/bom/"*.csv ]; then
    cp hardware/manufacturing/bom/*.csv "$OUTPUT_DIR/BOM_${TIMESTAMP}.csv"
    echo "   ✓ Copied BOM to outputs/"
else
    echo "   ⚠️  No BOM CSV found in hardware/manufacturing/bom/"
fi

# === 4. COPY CPL (Pick-and-Place) ===
echo ""
echo "📍 Preparing Pick-and-Place..."
if [ -f "hardware/manufacturing/cpl/"*.csv ]; then
    cp hardware/manufacturing/cpl/*.csv "$OUTPUT_DIR/CPL_${TIMESTAMP}.csv"
    echo "   ✓ Copied CPL to outputs/"
else
    echo "   ⚠️  No CPL file found in hardware/manufacturing/cpl/"
fi

# === 5. ZIP STL FILES ===
echo ""
echo "🎨 Zipping STL files for 3D printing..."
if [ -d "mechanical/stl" ] && [ "$(ls -A mechanical/stl/*.stl 2>/dev/null)" ]; then
    cd mechanical
    zip -q "../$OUTPUT_DIR/STL_files_${TIMESTAMP}.zip" stl/*.stl
    echo "   ✓ Created: outputs/STL_files_${TIMESTAMP}.zip"
    cd "$PROJECT_ROOT"
else
    echo "   ⚠️  No STL files found in mechanical/stl/"
fi

# === 6. CREATE MANUFACTURING PACKAGE ===
echo ""
echo "📦 Creating complete manufacturing package..."
cd "$OUTPUT_DIR"
zip -q "MANUFACTURING_PACKAGE_${TIMESTAMP}.zip" *_${TIMESTAMP}.* 2>/dev/null || true
cd "$PROJECT_ROOT"

# === 7. CREATE README ===
echo ""
echo "📝 Creating manufacturing README..."
cat > "$OUTPUT_DIR/README_${TIMESTAMP}.txt" << EOF
Manufacturing Files Package
Generated: $(date)

Contents:
- gerbers_${TIMESTAMP}.zip     : Gerber files (PCB layers)
- drill_${TIMESTAMP}.zip       : Drill files
- BOM_${TIMESTAMP}.csv         : Bill of Materials
- CPL_${TIMESTAMP}.csv         : Component Placement (Pick-and-Place)
- STL_files_${TIMESTAMP}.zip   : 3D printing files for enclosure

Upload Instructions:
1. Go to JLCPCB.com or PCBWay.com
2. Select "PCB Assembly" or "Instant Quote"
3. Upload gerbers.zip and drill.zip
4. Upload BOM.csv and CPL.csv when prompted
5. Upload STL files for 3D printing quote

Notes:
- Verify all specifications before ordering
- Check component availability
- Review assembly quote carefully
- Request photos during assembly if possible

For questions: [your-email]
EOF

echo "   ✓ Created README with instructions"

# === 8. SUMMARY ===
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Manufacturing files prepared!"
echo ""
echo "📁 Location: hardware/manufacturing/outputs/"
echo ""
echo "📦 Files created:"
ls -lh "$OUTPUT_DIR" | grep "$TIMESTAMP" | awk '{print "   " $9 " (" $5 ")"}'
echo ""
echo "🚀 Next steps:"
echo "   1. Review files in: hardware/manufacturing/outputs/"
echo "   2. Upload to manufacturer (JLCPCB/PCBWay)"
echo "   3. Get quote and verify pricing"
echo "   4. Place order"
echo ""
echo "💡 Tip: Keep original files and this package for records"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Open outputs folder
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "$OUTPUT_DIR"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open "$OUTPUT_DIR" 2>/dev/null || true
fi
