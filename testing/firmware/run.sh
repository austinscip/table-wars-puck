#!/usr/bin/env bash
# Compile + run the firmware host tests (pure logic from src/hal/sp_json.h,
# exercised through a minimal Arduino String shim — no ESP32 toolchain). Run
# locally or in CI. Exits non-zero on any test failure or compile error.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
out="$(mktemp -d)/sp_json_tests"

CXX="${CXX:-c++}"
"$CXX" -std=c++17 -Wall -Wextra -Werror \
  "$here/test_sp_json.cpp" -o "$out"

"$out"
