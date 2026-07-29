# Iterate policy — cheap without false reject

**Goal:** spend little wall-clock on junk tracks, **without** killing ideas that only fail amplitude on L1 but would pass or improve on L2.

Full ladder context: [SUITE_CRITICAL.md](./SUITE_CRITICAL.md).

---

## Roles (not interchangeable)

| Rung | Role | May decide |
|------|------|------------|
| **Preview** | Track END / uncross timing | Kill bad END targets only |
| **L½** (optional 33×4–6) | Screening | Direction only — never final kill |
| **L1** (33×8) | Default experiment | **Direction** Kill / Hold / Promote |
| **L2** (49×16, seed7) | Amplitude + Gate SoT | Confirm Hold→Promote; ship path |
| **L0 FastWan** | UI alive | **Never** pose |

Cheap answers: *Is motion going the right way?*  
Quality answers: *How complete is open_end geometry?*

**Ship signal = open_end PASS on L2+ only.** L1 FAIL is not “idea dead”.

---

## Verdicts after each gated Move run

| Verdict | Meaning | Next |
|---------|---------|------|
| **KILL** | Direction wrong; quality will not fix choreography | Drop track/prompt variant; do not L2 |
| **HOLD** | Incomplete / noisy / ambiguous — risk of false reject | **One** L2 seed7 required before drop |
| **PROMOTE** | Direction right; needs amplitude or near gate | L2 (or L2×24 if already close) |
| **PASS** | `ok` / `pose_pass` | L3 multi-seed / ship path — not more L1 spam |

---

## KILL (no L2)

Any of:

- Track **Preview END** off-body or nonsense (dx/dy target wrong)
- Video: **kick**, freeze, **apart-only**, reverse order (apart before uncross)
- Clear **no uncross** over full clip (not “almost”)
- Total face/body morph / collapse

Do **not** KILL solely because L1 `ok=false`.

---

## HOLD (L2 mandatory before discard)

Default bucket when unsure. Includes:

- Visually “almost open” / “fehlt der Rest”
- Gate phase `uncrossing_height` or `need_lateral_apart` with mid progress
- progress roughly **≥ 0.45** and not an obvious kick
- L1 ugly but trajectory order correct
- Single bad seed — still Hold the **track**, not the universe of seeds

Hygiene: keep Hold artifacts until one L2 is logged (mp4 + gate JSON + tracks sha).

---

## PROMOTE (run L2 now)

- Uncross **visible** before apart (even if incomplete)
- progress **≥ ~0.55** or improving vs last same-track L1
- Phase height/apart (not pure still_crossed **with** video confirming kick/cross)
- Researcher judgment: “direction yes, amplitude no” (classic e01)

L2 seed **7** once per track variant. Compare Δ progress L1→L2:

- L2 **better or equal** → keep track; tune uncross_frac / apart lightly  
- L2 **much worse** and direction broken → then KILL  
- L2 near thresholds → steps 24–30, not seed spam  

---

## PASS

`pose_gate` open_end `ok` on **L2+** → leaderboard + L3 / motor ship.  
Never ship on L0/L1 alone.

---

## Anti-patterns

| Don’t | Do |
|-------|-----|
| L1 FAIL ⇒ drop track | HOLD → one L2 |
| L½ FAIL ⇒ drop track | L1 at least; then Hold/Promote |
| 10× L1 seeds | 1× L2 on good direction |
| L2 as default every tweak | L1 direction → L2 confirm |
| Gate number without watching video | Video + gate together |
| FastWan as pose | L0 = UI only |

---

## Suggested loop

```
Preview tracks (gratis)
  → L1 33×8
  → Gate + glance video
  → KILL | HOLD | PROMOTE | PASS
  → if HOLD or PROMOTE: L2 49×16 seed7 once
  → Gate again; only then A/B tracks or steps↑
```

---

## Numbers (e01 open_end, guidance only)

| | |
|--|--|
| Gate open | max_dy ≤ 45, min_dx ≥ 55 (motor) |
| Lab best plateau (L2) | ~0.86 seed7 `uncrossing_height` |
| Hold floor (soft) | progress ≳ 0.45 + non-kick video |
| Promote floor (soft) | progress ≳ 0.55 **or** clear uncross direction |

Thresholds are **heuristics** for the HUD, not a second gate. Pose truth remains motor `pose_gate`.
