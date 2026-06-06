// Minimal host-side Arduino shim — JUST enough of `String` + `isDigit` to
// compile and exercise src/hal/sp_json.h off-device (no ESP32 toolchain
// needed). Backed by std::string. Mirrors Arduino String's clamping behaviour
// for substring/indexOf so the parser logic under test behaves identically to
// the firmware. NOT a general Arduino emulation — only what sp_json.h uses.
#pragma once

#include <string>
#include <cstring>
#include <cstdlib>

inline bool isDigit(char c) { return c >= '0' && c <= '9'; }

class String {
  std::string s_;
 public:
  String() {}
  String(const char* c) : s_(c ? c : "") {}
  String(const std::string& s) : s_(s) {}

  int length() const { return (int)s_.size(); }
  const char* c_str() const { return s_.c_str(); }
  char operator[](int i) const {
    return (i >= 0 && i < (int)s_.size()) ? s_[i] : '\0';
  }

  int indexOf(const String& sub, int from = 0) const {
    if (from < 0) from = 0;
    if (from > (int)s_.size()) return -1;
    std::string::size_type p = s_.find(sub.s_, (std::string::size_type)from);
    return p == std::string::npos ? -1 : (int)p;
  }
  int indexOf(const char* sub, int from = 0) const {
    return indexOf(String(sub), from);
  }

  // Arduino clamps both forms rather than throwing.
  String substring(int from) const {
    if (from < 0) from = 0;
    if (from > (int)s_.size()) from = (int)s_.size();
    return String(s_.substr((std::string::size_type)from));
  }
  String substring(int from, int to) const {
    int n = (int)s_.size();
    if (from < 0) from = 0;
    if (to > n) to = n;
    if (from >= to) return String("");
    return String(s_.substr((std::string::size_type)from,
                            (std::string::size_type)(to - from)));
  }

  long toInt() const { return std::atol(s_.c_str()); }

  String operator+(const String& o) const { return String(s_ + o.s_); }
  String operator+(const char* o) const {
    return String(s_ + std::string(o ? o : ""));
  }
  bool operator==(const char* o) const { return s_ == std::string(o ? o : ""); }
  bool operator==(const String& o) const { return s_ == o.s_; }
  bool operator!=(const char* o) const { return !(*this == o); }
};

inline String operator+(const char* a, const String& b) { return String(a) + b; }
