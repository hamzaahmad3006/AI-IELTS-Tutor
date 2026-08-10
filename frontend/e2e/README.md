# End-to-end tests

```bash
# 1. A backend the device can reach. Not localhost — see frontend/.env.example.
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000

# 2. Build and run, against a real phone over ADB:
cd frontend
npx detox build --configuration android.attached.debug
npx detox test  --configuration android.attached.debug
```

`android.attached.debug` targets a phone connected over ADB. There is also an
`android.emu.debug` configuration; set `DETOX_AVD_NAME` to your own AVD, which
`emulator -list-avds` will show.

## Not yet run

**These specs have never been executed.** The emulator on the development
machine does not reach `boot_completed`, and no physical device has been
attached, so the configuration is written from the documented API rather than
confirmed against a running app.

Two things will almost certainly need fixing on the first real run:

- **`testID` props.** The specs address elements by `testID` and most of those
  do not exist in the components yet. The first run will fail on the first
  missing one, and each is a one-line addition.
- **Onboarding step order.** The spec assumes exam type, then consent. If the
  screens are ordered differently the taps land in the wrong place.

This is recorded rather than hidden because a green-looking E2E setup that has
never run is worse than an obviously unrun one: it invites people to trust a
signal that does not exist.

## Why one journey rather than a suite

Register, onboard, submit an essay, see a band. If that path is broken the app
has no purpose.

E2E tests are slow, flaky and expensive to maintain, and a large suite of them
decays into something people skip — at which point it is worse than nothing,
because everyone believes it is running. The unit and smoke suites cover
breadth; this covers the thing that must never break, plus session persistence
across a restart, which is the one assertion the unit tests genuinely cannot
make about the Keystore.
