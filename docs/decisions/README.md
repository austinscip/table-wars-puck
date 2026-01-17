# Design Decisions

Document important design decisions here to maintain context about why certain choices were made.

## How to Use This Folder

Create a new markdown file for each major decision:

```
YYYY-MM-DD_decision_title.md
```

### Example filename:
```
2025-12-15_mcu_selection.md
2025-12-20_power_supply_design.md
2026-01-05_sensor_placement.md
```

## Decision Template

Copy this template for each decision:

```markdown
# [Decision Title]

**Date:** YYYY-MM-DD
**Status:** [Proposed / Accepted / Deprecated / Superseded]
**Deciders:** [Names or roles]

## Context

What is the situation that requires this decision?
- Background information
- Constraints (cost, size, timeline, etc.)
- Requirements that must be met

## Decision

What was decided and why?

## Alternatives Considered

### Option 1: [Name]
**Pros:**
- Pro 1
- Pro 2

**Cons:**
- Con 1
- Con 2

**Cost:** $XX.XX per unit

### Option 2: [Name]
[Same structure]

### Option 3: [Name]
[Same structure]

## Comparison Table

| Criteria | Option 1 | Option 2 | Option 3 | Winner |
|----------|----------|----------|----------|--------|
| Cost | $XX | $XX | $XX | ✓ Option 1 |
| Power consumption | XX mA | XX mA | XX mA | ✓ Option 2 |
| Size | XX mm² | XX mm² | XX mm² | ✓ Option 1 |
| Availability | In stock | 12 week lead | In stock | ✓ Option 1 |
| Support | Good | Excellent | Poor | ✓ Option 2 |

## Final Decision

**Chosen:** Option X

**Reasoning:**
- Reason 1
- Reason 2
- Reason 3

## Consequences

**Positive:**
- Benefit 1
- Benefit 2

**Negative:**
- Trade-off 1 (and how we're mitigating it)
- Trade-off 2

**Risks:**
- Risk 1: [Mitigation strategy]
- Risk 2: [Mitigation strategy]

## Implementation Notes

- [ ] Task 1 to implement this decision
- [ ] Task 2
- [ ] Update BOM with new part
- [ ] Update schematic
- [ ] Test new configuration

## Related Decisions

- Links to other decision documents that relate to this one
- [2025-12-10_power_supply.md](2025-12-10_power_supply.md)

## References

- [Datasheet link]
- [Forum discussion]
- [Application note]
- [Vendor comparison]

## Updates

### YYYY-MM-DD
Updated because [reason]. Changed [what changed].

---

*Template by Claude Code*
```

## Example Decisions to Document

- MCU selection (ESP32 vs STM32 vs RP2040)
- Power supply architecture (LDO vs buck converter)
- Battery chemistry and capacity
- Communication protocol (WiFi vs BT vs LoRa)
- Sensor selection and placement
- PCB layer count (2 vs 4 vs 6 layers)
- Connector types
- Enclosure material and manufacturing method
- Assembly strategy (SMT vs through-hole)
- Cost vs performance trade-offs

## Tips

1. **Document as you decide** - Don't wait until later
2. **Include numbers** - Actual measurements, costs, specs
3. **Explain the "why"** - Future you will forget
4. **Link to resources** - Datasheets, app notes, calculations
5. **Update if changed** - Mark old decisions as superseded
6. **Be honest about trade-offs** - Nothing is perfect

## Decision Status Meanings

- **Proposed:** Under consideration, not final
- **Accepted:** Implemented and working
- **Deprecated:** No longer recommended but still in use
- **Superseded:** Replaced by a better decision (link to new one)
