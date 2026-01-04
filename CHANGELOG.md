# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### To Do
- [ ] Item 1
- [ ] Item 2

### In Progress
- Item being worked on

## [1.0.0] - YYYY-MM-DD

### Added - Hardware
- Initial PCB design
- Component selection
- Power management circuit
- [List all major hardware additions]

### Added - Firmware
- Initial firmware framework
- Communication protocol
- [List firmware features]

### Added - Mechanical
- Enclosure design
- 3D printable files
- [List mechanical additions]

### Changed
- [Describe changes to existing features]

### Fixed
- [Bug fixes]

### Known Issues
- [List current known issues]
- [With workarounds if available]

## [0.9.0] - YYYY-MM-DD - Prototype

### Added
- Proof of concept schematic
- Breadboard prototype
- Initial component testing

### Issues Found
- [Issues discovered during prototyping]
- [Led to changes in v1.0]

## [0.5.0] - YYYY-MM-DD - Design Phase

### Added
- Requirements document
- Block diagram
- Initial component research

### Decisions Made
- **MCU Selection:** [Chosen MCU] - [Reason]
- **Power Source:** [Battery type] - [Reason]
- **Connectivity:** [WiFi/BT/etc.] - [Reason]

## [0.1.0] - YYYY-MM-DD - Concept

### Added
- Initial concept
- Requirements gathering
- Market research

---

## Version Numbering

This project uses [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Incompatible hardware changes (requires new PCB)
- **MINOR** version: Backwards-compatible functionality additions (firmware only)
- **PATCH** version: Bug fixes and minor improvements

### Examples:
- `1.0.0` → `2.0.0` : New PCB revision with different pinout
- `1.0.0` → `1.1.0` : New firmware feature, same hardware
- `1.0.0` → `1.0.1` : Bug fix in firmware, same hardware

---

## How to Update This Changelog

When making changes:

1. **During development:** Add to "Unreleased" section
2. **Before release:** Move from "Unreleased" to new version section
3. **Format:** Use past tense ("Added", not "Add")
4. **Categories:** Added / Changed / Deprecated / Removed / Fixed / Security
5. **Hardware vs Firmware:** Specify which changed

### Example Entry:

```markdown
## [1.1.0] - 2025-03-15

### Added - Hardware
- USB-C charging port (previously micro-USB)
- Battery voltage monitoring circuit

### Added - Firmware
- Low battery warning
- USB connection detection

### Fixed
- ESP32 brown-out issues during WiFi transmission
- LED flickering at low battery

### Known Issues
- Occasional Bluetooth disconnect (investigating)
```

---

## Links

- [Unreleased]: https://github.com/user/repo/compare/v1.0.0...HEAD
- [1.0.0]: https://github.com/user/repo/compare/v0.9.0...v1.0.0
- [0.9.0]: https://github.com/user/repo/compare/v0.5.0...v0.9.0
