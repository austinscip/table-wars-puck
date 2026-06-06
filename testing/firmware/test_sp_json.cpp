// Host-side regression tests for src/hal/sp_json.h — the puck's JSON field
// extractors. These back the consolidated match-state parse and the
// pending-pick / pending-minigame parsing in g_speed_pyramid.h. Run on the
// build host (no ESP32 needed) via testing/firmware/run.sh; wired into CI.
//
// Covers the hardening from audit firmware-2026-06-06:
//   - M2: bounded extract_string, needle-derived value_offset (no magic +24).
//   - The rejected "CRITICAL": the "id" needle carries a leading quote, so it
//     must NOT match the tail of "picker_puck_id"/"category_id"/"question_id".
//
// Pure assertion harness — no framework. Prints FAIL lines and returns
// non-zero on any failure so CI fails loudly.

#include "arduino_shim.h"
#include "../../src/hal/sp_json.h"

#include <cstdio>

static int g_failures = 0;

#define CHECK(cond)                                                       \
  do {                                                                    \
    if (!(cond)) {                                                        \
      std::printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond);         \
      ++g_failures;                                                       \
    }                                                                     \
  } while (0)

static void test_extract_string() {
  String j = "{\"role\":\"host\",\"lobby_code\":\"ABC123\"}";
  String out;
  CHECK(sp_json::extract_string(j, "role", &out));
  CHECK(out == "host");
  CHECK(sp_json::extract_string(j, "lobby_code", &out));
  CHECK(out == "ABC123");
  CHECK(!sp_json::extract_string(j, "missing", &out));

  // Bounded: an oversized value is refused rather than copied (heap guard).
  std::string big = "{\"x\":\"";
  for (int i = 0; i < 500; ++i) big += 'A';
  big += "\"}";
  String huge(big);
  String sink;
  CHECK(!sp_json::extract_string(huge, "x", &sink, 256));
  CHECK(sp_json::extract_string(huge, "x", &sink, 1000));  // higher cap OK
}

static void test_extract_int() {
  String j = "{\"question_id\":42,\"time_limit\":10,\"neg\":-7}";
  int v = 0;
  CHECK(sp_json::extract_int(j, "question_id", &v) && v == 42);
  CHECK(sp_json::extract_int(j, "time_limit", &v) && v == 10);
  CHECK(sp_json::extract_int(j, "neg", &v) && v == -7);
  CHECK(!sp_json::extract_int(j, "absent", &v));

  // Non-numeric value -> no digits -> false.
  String s = "{\"k\":\"abc\"}";
  CHECK(!sp_json::extract_int(s, "k", &v));
}

static void test_extract_bool() {
  String j = "{\"active\":true,\"complete\":false}";
  bool b = false;
  CHECK(sp_json::extract_bool(j, "active", &b) && b == true);
  CHECK(sp_json::extract_bool(j, "complete", &b) && b == false);
  CHECK(!sp_json::extract_bool(j, "missing", &b));
  // A bool near the end of the buffer must not read past it (substring clamps).
  String tail = "{\"complete\":true}";
  CHECK(sp_json::extract_bool(tail, "complete", &b) && b == true);
}

static void test_value_is_null() {
  String j =
      "{\"pending_category_pick\":null,\"pending_minigame\":{\"flavor\":\"B\"}}";
  CHECK(sp_json::value_is_null(j, "\"pending_category_pick\":"));
  CHECK(!sp_json::value_is_null(j, "\"pending_minigame\":"));
  // Absent key -> not null (the caller then indexOf()s and bails).
  CHECK(!sp_json::value_is_null(j, "\"nope\":"));
}

// The exact logic path used by _parse_pending_pick: extract picker, then loop
// the "\"id\":" needle for up to 3 offer ids. This is the regression for the
// agent's (rejected) "category_id false-positive" claim — the leading quote in
// the needle means picker_puck_id / category_id never match.
static void test_pending_pick_parse() {
  String body =
      "{\"exists\":true,\"round\":2,\"complete\":false,"
      "\"pending_category_pick\":{\"picker_puck_id\":2,\"offer\":["
      "{\"id\":10,\"name\":\"X\"},{\"id\":20,\"name\":\"Y\"},"
      "{\"id\":30,\"name\":\"Z\"}],\"deadline_at\":123},"
      "\"pending_minigame\":null,\"category_id\":99}";

  CHECK(!sp_json::value_is_null(body, "\"pending_category_pick\":"));
  CHECK(sp_json::value_is_null(body, "\"pending_minigame\":"));

  int pp_at = body.indexOf("\"pending_category_pick\":");
  CHECK(pp_at >= 0);
  int picker = 0;
  CHECK(sp_json::extract_int(body.substring(pp_at), "picker_puck_id", &picker));
  CHECK(picker == 2);

  String slice = body.substring(pp_at);
  int ids[3] = {0, 0, 0};
  int cursor = 0;
  int k = 0;
  for (; k < 3; ++k) {
    int hit = slice.indexOf("\"id\":", cursor);
    if (hit < 0) break;
    int v = 0;
    if (!sp_json::extract_int(slice.substring(hit), "id", &v)) break;
    ids[k] = v;
    cursor = hit + 5;
  }
  // Must be the three offer ids, in order — NOT picker_puck_id (2) or the
  // trailing category_id (99).
  CHECK(ids[0] == 10);
  CHECK(ids[1] == 20);
  CHECK(ids[2] == 30);
  CHECK(k == 3);
}

static void test_pending_minigame_parse() {
  String bull =
      "{\"pending_category_pick\":null,\"pending_minigame\":{\"flavor\":\"B\","
      "\"target_quadrant\":\"C\",\"duration_s\":5}}";
  String flavor, target;
  CHECK(sp_json::extract_string(bull, "flavor", &flavor) && flavor == "B");
  CHECK(sp_json::extract_string(bull, "target_quadrant", &target) &&
        target == "C");

  // SHOT_CLOCK: target_quadrant is JSON null -> extract_string finds no
  // opening quote for the value -> returns false -> firmware sets _mg_target=0.
  String shot =
      "{\"pending_minigame\":{\"flavor\":\"S\",\"target_quadrant\":null}}";
  CHECK(sp_json::extract_string(shot, "flavor", &flavor) && flavor == "S");
  CHECK(!sp_json::extract_string(shot, "target_quadrant", &target));
}

int main() {
  test_extract_string();
  test_extract_int();
  test_extract_bool();
  test_value_is_null();
  test_pending_pick_parse();
  test_pending_minigame_parse();

  if (g_failures == 0) {
    std::printf("ok — all sp_json host tests passed\n");
    return 0;
  }
  std::printf("FAILED — %d check(s)\n", g_failures);
  return 1;
}
