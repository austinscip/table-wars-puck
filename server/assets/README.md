# Polish assets

Audio, music, and SFX files driven by the runtime cue language
(`server/runtime/cues.py`). Every cue name has at most one asset per
channel; swap the file, all games inherit the new sound.

## Channels

| Directory | Channel | Used for |
|---|---|---|
| `vo/` | `Cue.VO` | Host voice-over lines. Ducks music. Full sentences, 1-3s. |
| `music/` | `Cue.MUSIC` | Music bed under the host VO. Loops + transitions. |
| `sfx/` | `Cue.SFX` | Short ambient effects (ding, buzz, whoosh). <500ms. |

(LED, motor, buzzer, haptic cues are firmware-side and have no audio
asset.)

## Naming convention

`<cue_name>.<ext>`, where `<cue_name>` matches the `Cue` enum value:

```
sfx/player_correct.mp3
sfx/player_wrong.mp3
vo/match_start.mp3
music/round_start.mp3
```

Polish authors targeting a specific channel-cue swap a single file. No
code changes.

## Manifest

Each channel directory has an `assets.yaml` listing every cue → file
mapping with license attribution. Add a row when you drop a new asset:

```yaml
- cue: player_correct
  file: player_correct.mp3
  source: freesound.org/people/<user>/sounds/<id>/
  license: CC0
  duration_ms: 320
```

The build step reads this manifest to package only the referenced files
into the TV app, dropping anything unlisted. Drop-and-forget assets
don't ship.

## Generation

- **VO**: Kokoro TTS via `scripts/build_vo.py` (TODO). Reads a YAML of
  cue → text mapping, renders to mp3.
- **Music**: Pixabay CC0 (manual curation).
- **SFX**: freesound.org / Sonniss GDC (manual curation).

## Why an asset cue layer at all

Games never call `play("ding.mp3")`. They emit
`CueEvent(cue=Cue.PLAYER_CORRECT, target=puck_index)`. The polish
system decides everything else — file, channel, volume, ducking. That
keeps the game logic out of the polish loop and lets a designer iterate
sounds without touching Python.
