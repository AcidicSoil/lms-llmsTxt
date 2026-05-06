# Project Overlays

Apply one overlay after the core lifecycle.

## Greenfield Overlay

Priorities:
- problem clarity before implementation
- fast architecture convergence
- design system and observability early
- one complete vertical slice before expanding scope
- avoid speculative complexity

Extra gates:
- platform choice justified
- first-run UX reviewed before scale-out
- telemetry exists before launch
- scope is constrained to a shippable release

Recommended order:
1. framing
2. reference UX and architecture
3. foundation
4. first vertical slice
5. iterative slices
6. hardening
7. polish
8. launch readiness
9. staged launch

## Brownfield Overlay

Priorities:
- protect existing behavior
- map system before edits
- establish characterization tests
- use feature flags and compatibility layers
- migrate through small vertical slices
- prefer strangler patterns over broad rewrites

Extra gates:
- current behavior baselined
- rollback defined per migration slice
- observability added before risky changes
- public APIs, URLs, data contracts, and user workflows preserved unless breaking change is approved

Recommended order:
1. audit and baseline
2. characterization tests
3. migration plan
4. observability upgrades
5. compatibility layer or flags
6. smallest high-value slice
7. iterative replacement/refactor
8. hardening
9. polish
10. staged rollout
