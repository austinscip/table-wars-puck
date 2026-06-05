# Table Wars TV

The Google TV / Android TV app for Table Wars. Lives next to the Flask
sandbox (`server/`) and the bar portal (`portal/`).

Stack: React Native 0.85 via the `react-native-tvos` community fork, React
Navigation (native-stack), Supabase JS client, AsyncStorage for session
persistence.

## What's here

Skeleton ported from the existing Speed Pyramid TV display
(`server/static/games/speed-pyramid/`):

| Screen | What it shows |
|---|---|
| Title | TABLE WARS wordmark, "Hold the puck button to pair", breathing dots |
| Pair | 6-digit code with per-digit lock-in state |
| Lobby | Pair code, joined-player avatars, host start hint |
| Scoreboard | Sorted final results with winner crown |

State flow is stubbed — real wiring comes when the multi-game runtime
(Track G) is online.

## Setup to run on a device or emulator

The code type-checks and runs through Metro without any Android tooling
installed. To actually launch on an emulator or a Chromecast with Google
TV, you need:

### 1. JDK 17

Installed via Homebrew. To make it visible to Gradle:

```sh
echo 'export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"' >> ~/.zshrc
echo 'export JAVA_HOME="/opt/homebrew/opt/openjdk@17"' >> ~/.zshrc
```

### 2. Android Studio + SDK

Download Android Studio: https://developer.android.com/studio

Inside Android Studio → SDK Manager:
- **SDK Platforms:** Android 14 (API 34) — matches RN 0.85's target.
- **SDK Tools:** Android SDK Build-Tools, Android Emulator, Android SDK
  Platform-Tools, Google TV ATV Intel x86_64 System Image (under
  "Android TV" sub-section).

Then export the SDK paths:

```sh
echo 'export ANDROID_HOME="$HOME/Library/Android/sdk"' >> ~/.zshrc
echo 'export PATH="$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$PATH"' >> ~/.zshrc
```

### 3. Create a Google TV emulator AVD

In Android Studio → Device Manager → Create Virtual Device:
- **Category:** TV
- **Device:** Television (1080p)
- **System image:** Google TV ATV API 34
- **AVD name:** TableWarsTV-emulator

### 4. Banner image (required for Play Store TV channel, not for dev)

Android TV apps need a 320×180 PNG at
`android/app/src/main/res/drawable-xhdpi/tv_banner.png`, referenced via
`android:banner="@drawable/tv_banner"` on the `<application>` element. The
manifest leaves this out for now since `uses-feature leanback` is set to
`required="false"`. Add it before submitting to the TV channel.

### 5. Run

```sh
# Start Metro
npm run start

# In another shell, launch the emulator from Device Manager, then:
npm run android
```

The first build is slow (Gradle downloads ~1 GB of caches). Subsequent
builds are 30-60s.

## Run on a real Chromecast with Google TV

1. Enable developer options: Settings → About → click "Build" 7 times.
2. Settings → Developer options → ADB debugging ON.
3. Find the device IP: Settings → Network → connection details.
4. From your Mac: `adb connect <chromecast-ip>:5555`
5. `npm run android` will deploy to the connected device.

## Local config

`src/config.ts` holds the Supabase URL + anon (publishable) key. It's
generated from `~/tablewars/.env` and gitignored. To regenerate:

```sh
set -a; source ~/tablewars/.env; set +a
cat > src/config.ts <<EOF
export const SUPABASE_URL = '\$SUPABASE_URL';
export const SUPABASE_ANON_KEY = '\$SUPABASE_ANON_KEY';
EOF
```

A committed `src/config.example.ts` documents the shape.
