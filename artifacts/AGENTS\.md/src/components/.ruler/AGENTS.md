# keep React components small, focused, and composable

Scope: React components under `src/components` and any feature `*/components` folders.

## core rules

1. **One main component per file**
   - One primary React component per `.tsx` file.
   - File name matches the main component name (`SessionList.tsx` → `SessionList`).
   - Co-located helpers must be:
     - Pure functions, or
     - Tiny presentational components (< ~40 LOC) that are strictly view-only.

2. **File-size limits**
   - Soft target: **150–250 LOC** per component file (excluding imports and types).
   - Warning zone: **> 400 LOC** → required refactor before adding new behavior.
   - Hard cap: **600 LOC**. No exceptions; split file or extract modules before merging.

3. **Split responsibilities**
   - **State + side effects → custom hooks** in `*.hooks.ts` or `*.hooks.tsx`.
   - **View-only JSX → presentational components** in `*.view.tsx` or `*Section.tsx`.
   - **Pure helpers / formatting / data shaping → utilities** in `*.utils.ts` or `*.format.ts`.

4. **JSX nesting**
   - Max **3 levels** of JSX nesting inside any component render.
   - If a block nests deeper, extract it into a subcomponent:
     - Example: complex cards, list items, accordions, toolbars, sheets.
   - Conditionals (`&&`, `?:`) should wrap subcomponents, not large inline JSX trees.

5. **Feature layers**
   - Every non-trivial feature has **three layers**:
     1. **Container**: orchestrates data + state + callbacks (no layout complexity).
     2. **View model / hooks**: filtering, grouping, sorting, formatting, logging.
     3. **Presentational components**: lists, items, cards, toolbars, sheets.
   - Do not mix all three layers in one file.

6. **No “gravity wells”**
   - If a component:
     - Handles **remote data**, **filters/search**, **virtualization**, and **logging**
     - Or renders **more than one major UI surface** (e.g., header + filters + main list + side sheet)
   - Then it must be split into separate container + view + presentational files before adding features.

---

## if your component does X → use Y

- Needs **shared stateful logic** across multiple components
  → Create `useXxx` in `ComponentName.hooks.ts` and consume from thin `.tsx` components.

- Needs **complex filters/sorting/grouping**
  → `useXxxFilters` / `useXxxGrouping` hook in `*.hooks.ts`; main component only wires outputs into views.

- Needs **virtualized lists + item cards**
  → `FeatureList.tsx` (container with `TimelineView` or virtualization)
  → `FeatureListItem.tsx` (single item card; all detailed JSX lives here).

- Needs **advanced side sheets / dialogs / popovers**
  → `FeatureFiltersSheet.tsx`, `FeatureDialog.tsx` etc.
  → Main component only passes props and open/close state.

- Needs **reusable formatting** (dates, bytes, counts, labels)
  → `featureFormat.ts` or `feature.utils.ts` with pure functions. No React imports.

- Needs **cross-feature helper (e.g., search matchers, highlight)**
  → Shared utility under `src/utils/` or `src/lib/`, never re-implemented inside large components.

---

## structure conventions

For any non-trivial component (lists, explorers, complex panels), prefer:

- `FeatureName/FeatureName.tsx`
  - Thin container; receives props.
  - Uses hooks from same folder; composes view components.
- `FeatureName/FeatureName.hooks.ts`
  - `useFeatureNameState`, `useFeatureNameFilters`, etc.
  - Owns all `useState`, `useEffect`, `useMemo`, logging, and derived-state logic.
- `FeatureName/FeatureName.view.tsx`
  - Optional: top-level layout if container is already dense.
- `FeatureName/FeatureNameList.tsx`, `FeatureName/FeatureNameItem.tsx`
  - Virtualized lists and cards.
- `FeatureName/FeatureName.format.ts`
  - `formatBytes`, `formatDate`, `formatRelativeTime`, label builders, etc.
- `FeatureName/FeatureName.types.ts`
  - Local shared types/interfaces for this feature only.

New behavior must go into hooks or utilities before being added to the main `.tsx`.

---

## when to split a file (hard triggers)

Trigger a refactor **before** adding more code if any of these are true:

1. File > **400 LOC** or diff adds > **80 LOC** to a file already > **300 LOC**.
2. Component uses **3+ `useState` / `useReducer` / `useEffect`** and also renders complex JSX.
3. Component includes **two or more** of:
   - Search/filter logic
   - Grouping/sorting/aggregation
   - Virtualized list / timeline
   - Side sheet / advanced modal
   - Telemetry/logging
4. JSX render body:
   - Scrolls beyond one screen
   - Contains deeply nested conditional branches or maps with inline complex JSX.

On these triggers you must:

- Move state + business logic into `*.hooks.ts`.
- Move large JSX blocks into subcomponents in their own files.
- Move helpers into `*.utils.ts` / `*.format.ts`.

---

## review checklist before merging a component change

- [ ] Does each `.tsx` file expose exactly **one main component**?
- [ ] Is the file within the **150–250 LOC target** (and always < 600 LOC)?
- [ ] Is complex logic (**filters, grouping, logging, streaming, server calls**) located in hooks/utilities, not directly in the render body?
- [ ] Are list items / cards / rows implemented as dedicated components, not giant inline JSX blocks?
- [ ] Are advanced sheets / dialogs / popovers implemented as their own components?
- [ ] Is JSX nesting <= 3 levels in all render paths?
- [ ] Are reusable formatting functions and helpers shared via `*.utils.ts` / `*.format.ts` instead of redefined?
- [ ] For new features: did we create or extend a `useXxx` hook rather than injecting more state into an already-large component?

---

## examples of “bad” vs “good” placement (conceptual)

- **Bad**: `SessionList.tsx` contains:
  - Filter state, quick filters, size/timestamp parsing, logging, grouping, virtualization, and card JSX.
- **Good**:
  - `SessionList.tsx` → ties together hooks + view components only.
  - `useSessionExplorerFilters` / `useSessionGrouping` in `SessionList.hooks.ts`.
  - `SessionRepoAccordion.tsx`, `SessionRepoVirtualList.tsx`, `SessionCard.tsx` as separate view files.
  - `sessionFormat.ts`, `sessionSearch.ts`, `sessionGrouping.ts` for pure helpers.

- **Bad**: `ChatDockPanel.tsx` owns bootstrapping, streaming, model selection, misalignment state, message list, input, and all subcomponents.
- **Good**:
  - `ChatDockPanel.tsx` → bootstrap + delegates to `ChatDockPanelInner`.
  - `useChatDockState`, `useChatModelPreference` hooks for logic.
  - `ChatHeader.tsx`, `ChatMessages.tsx`, `MessageBubble.tsx`, `MisalignmentList.tsx` as small view components.

---

## project constraints for components

- Use TypeScript React (`.tsx`) for all components.
- Prefer **function components + hooks**; no new class components.
- Keep **imports stable**: heavy libraries used only in containers/hooks, not repeated across many leaf components.
- New complex UI surfaces must start with a **container + hooks + view** layout; do not begin as a single monolithic component.
