# Cost Tracking

Track all project costs here to maintain budget visibility.

## Component Costs

| Part | Manufacturer Part # | Unit Price | Qty | Total | Supplier | Notes |
|------|-------------------|------------|-----|-------|----------|-------|
| MCU | | $X.XX | X | $X.XX | [Digi-Key/LCSC] | |
| Sensor | | $X.XX | X | $X.XX | | |
| LED | | $X.XX | X | $X.XX | | |
| Battery | | $X.XX | X | $X.XX | | Not assembled by JLCPCB |
| Passive components | | $X.XX | XX | $X.XX | | Bulk pricing |

**Total Components per Unit:** $XX.XX

## PCB Manufacturing

### Prototype Run (5 units)

| Item | Spec | Price | Notes |
|------|------|-------|-------|
| PCB fabrication | X layers, XXmm x XXmm | $XX.XX | JLCPCB/PCBWay |
| Component sourcing | X parts | $XX.XX | LCSC or manufacturer |
| SMT assembly | X SMT parts | $XX.XX | Top side only |
| Stencil | 100x100mm | $XX.XX | First order only |
| Shipping | | $XX.XX | DHL/FedEx |

**Total Prototype (5 units):** $XXX.XX
**Per Unit:** $XX.XX

### Production Run (100 units)

| Item | Spec | Price | Notes |
|------|------|-------|-------|
| PCB fabrication | X layers, XXmm x XXmm | $XXX.XX | Volume pricing |
| Component sourcing | X parts × 100 | $XXX.XX | Bulk discount |
| SMT assembly | X SMT parts × 100 | $XXX.XX | Setup fee + per unit |
| Stencil | Reuse from prototype | $0.00 | |
| Shipping | | $XX.XX | Sea freight option |

**Total Production (100 units):** $X,XXX.XX
**Per Unit:** $XX.XX

## 3D Printing / Enclosure

| Item | Material | Print Time | Price | Notes |
|------|----------|------------|-------|-------|
| Top case | PLA/PETG | Xh | $X.XX | Can print locally |
| Bottom case | PLA/PETG | Xh | $X.XX | |
| Button caps (X pcs) | TPU | Xh | $X.XX | Flexible material |

**Total per Unit:** $XX.XX

## Additional Costs

### Development
- [ ] Development boards: $XX.XX
- [ ] Test equipment: $XX.XX
- [ ] CAD software licenses: $XX.XX/year
- [ ] Component samples: $XX.XX

### One-Time Costs
- [ ] Stencil (first order): $XX.XX
- [ ] Tooling/fixtures: $XX.XX
- [ ] Certifications (FCC/CE): $XXX.XX

## Cost Summary

| Quantity | PCB + Assembly | Components | Enclosure | Total per Unit |
|----------|---------------|------------|-----------|----------------|
| 1 (dev) | $XX.XX | $XX.XX | $X.XX | **$XXX.XX** |
| 5 (proto) | $XX.XX | $XX.XX | $X.XX | **$XX.XX** |
| 10 | $XX.XX | $XX.XX | $X.XX | **$XX.XX** |
| 50 | $XX.XX | $XX.XX | $X.XX | **$XX.XX** |
| 100 | $XX.XX | $XX.XX | $X.XX | **$XX.XX** |
| 500 | $XX.XX | $XX.XX | $X.XX | **$XX.XX** |

## Manufacturing Quotes

### Quote 1: [Manufacturer Name] - [Date]

**Configuration:**
- Quantity: X units
- PCB: X layers, X×Xmm
- Assembly: Top side, X SMT parts
- Lead time: X days

**Pricing:**
- PCB fabrication: $XX.XX
- Component sourcing: $XX.XX
- Assembly: $XX.XX
- Shipping: $XX.XX
- **Total: $XXX.XX ($XX.XX per unit)**

**Notes:**
- [Any special notes, discounts, or issues]
- [Component availability]

**Quote file:** `orders/quotes/[manufacturer]_[date].pdf`

---

### Quote 2: [Manufacturer Name] - [Date]

[Same structure as above]

---

## Price Comparison

| Manufacturer | Qty | Per Unit | Lead Time | Component Availability | Notes |
|--------------|-----|----------|-----------|----------------------|-------|
| JLCPCB | 5 | $XX.XX | 5-7 days | 95% in stock | Fast, good for proto |
| PCBWay | 5 | $XX.XX | 7-10 days | Must source separately | Higher quality |
| [Other] | 5 | $XX.XX | XX days | | |

## Budget Tracking

**Initial Budget:** $X,XXX.XX

| Date | Item | Amount | Running Total | Notes |
|------|------|--------|---------------|-------|
| YYYY-MM-DD | Development boards | -$XX.XX | $X,XXX.XX | ESP32 + sensors |
| YYYY-MM-DD | PCB prototype quote | -$XXX.XX | $X,XXX.XX | 5 units from JLCPCB |
| | | | | |

**Remaining Budget:** $X,XXX.XX

## Cost Optimization Notes

### Opportunities to Reduce Cost
- [ ] Switch to alternative part X (saves $X.XX per unit)
- [ ] Reduce PCB size by Xmm (saves $X.XX)
- [ ] Use 2-layer instead of 4-layer (saves $XX.XX)
- [ ] Order components directly instead of through assembler (saves $X.XX)

### Trade-offs Considered
- **4-layer vs 2-layer PCB:** Chose 4-layer for better signal integrity (+$XX.XX per unit)
- **Part X vs Part Y:** Chose X for reliability despite +$X.XX cost
- **SMT vs Through-hole:** All SMT for automated assembly

---

## Update Log

| Date | Updated By | Changes |
|------|------------|---------|
| YYYY-MM-DD | [Name] | Initial cost estimate |
| YYYY-MM-DD | [Name] | Added JLCPCB quote |
| YYYY-MM-DD | [Name] | Updated component pricing |
