# Mobile App Runbook

## End State

Polished mobile app with strong onboarding, responsive interactions, offline/error handling, app-store readiness, and operational telemetry.

## Critical Tracks

- mobile UX
- navigation
- auth/session
- sync and offline behavior
- performance/battery
- push notifications
- analytics/crash reporting
- release pipeline

## Workflow

1. Define journeys, onboarding/login, notification strategy, offline behavior, and device/OS support matrix.
2. Design native interaction patterns, typography/scaling, dark mode, accessibility, gestures, loading/error states.
3. Establish navigation shell, state model, API integration, secure storage, analytics, crash reporting, feature flags, signing/build pipeline.
4. Build slices: onboarding/auth, home/dashboard, primary object flows, notifications, settings/profile, offline/sync states.
5. Harden: device matrix, network degradation, battery/performance, push delivery, resume/background handling, app-store policy compliance.
6. Polish: fast startup, native-feeling gestures, deliberate offline/retry states, strong first-run experience, store assets and copy.

## Production Checklist

- crash reporting live
- store submission assets ready
- release channels defined
- rollout/rollback strategy defined
- privacy disclosures complete
- signing and credential handling documented
- analytics funnels verified

## Brownfield Notes

Preserve local data across upgrades. Test migrations across app versions. Feature-flag risky flows and staged rollouts.
