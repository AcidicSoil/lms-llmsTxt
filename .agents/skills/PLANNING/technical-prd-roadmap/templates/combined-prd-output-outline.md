# PRD: [Title]

## 1. Overview
- Problem statement
- Target users
- Why current solutions fail
- Success metrics
- Constraints and assumptions

## 2. Capability Tree (Functional Decomposition)

### Capability: [Name]

#### Feature: [Name]
- Description:
- Inputs:
- Outputs:
- Behavior:
- MVP: Yes/No

## 3. Repository Structure + Module Definitions (Structural Decomposition)
- Repository tree
- Module definitions
- Single responsibility per module
- Public exports per module

## 4. Dependency Chain (layers, explicit “Depends on: […]”)
- Foundation layer with no dependencies
- Higher layers in topological order
- Explicit dependency list for every non-foundation module
- Cycle and heavy-dependency notes

## 5. Development Phases
- Phase 0…N
- Entry criteria
- Exit criteria
- Tasks with dependencies
- Acceptance criteria
- Test strategy
- Delivered usable capability

## 6. User Experience
- Personas
- Key flows
- UI/UX notes tied to capabilities
- Commands or API examples when relevant

## 7. Technical Architecture
- System components
- Data models
- APIs and integrations
- Infrastructure
- Decisions with rationale, trade-offs, and alternatives

## 8. Test Strategy
- Test pyramid targets
- Coverage minimums
- Critical scenarios per module
- Integration points

## 9. Risks and Mitigations
- Technical risks
- Dependency risks
- Scope risks
- Impact, likelihood, mitigation, fallback

## 10. Appendix
- Research and references
- Glossary
- Open questions
- Non-goals

## 11. Recommended Default Task Structure
- Recommended epic count
- Recommended implementation task count
- Recommended subtask count and density ranges
- Brief rationale
