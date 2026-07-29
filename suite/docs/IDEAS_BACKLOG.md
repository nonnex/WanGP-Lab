# Backlog (suite)

## Done (mission cockpit)

- Lab Bridge track preview + apart-dx
- L0 / L1 / L2 ladder buttons (set image_start + custom_guide)
- Gate last UI output (`_outputs/`)
- Leaderboard panel in Bridge
- `_outputs` symlink + keep-last-2 hygiene
- Windows Desktop launcher

## P0 next

- Auto-fill still into Gradio image component (if API exposes setter)
- Watch-folder auto-gate on `_outputs/` (optional background)
- Multi-seed queue zip from Bridge

## P1

- Mission Mode badge (profile/sage/int8 locked)
- Track A/B side-by-side in Bridge
- Gate video scrub + knee overlay

## P2

- FLF2V A/B after open_end
- e12 preset locked until open_end PASS
- Bernini polish pass

## P3

- Multi-fixture derive → tracks
- Night batch queue

## Done (generic missions 0.5)

- `suite/missions/` recipe packs + template
- mission_lib: load/stage/ladder/run_card/gate hints
- Lab Bridge 0.5 mission dropdown (not e01-hardcoded)
- image_start as list (Motion Designer style)
- run_mission.sh headless by mission id

## Done (researcher UX 0.6)

- Gate HUD top (PASS/FAIL + next-action + dy/dx)
- L1 one-click → fill form + jump Media Generator
- uncross-frac control in tracks build (default 0.70)
- Frames default 33 (L1); L2 secondary button
- Last gated video preview; leaderboard collapsed
- Policy copy: L1 iterate / L2 candidate only

## Done (iterate policy)

- `suite/docs/ITERATE_POLICY.md` — KILL/HOLD/PROMOTE/PASS, false-reject rules
- `mission_lib.iterate_verdict` + Gate HUD verdict line
- SUITE_CRITICAL / AGENTS linked
