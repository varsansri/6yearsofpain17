"""
STAGE FUNNEL (Idea 2) — narrow the story space across each clock hour.

Each 1-hour cycle is split into four 15-minute stages. The system gathers and narrows
the possible stories stage by stage, and only pulls the trigger in the final stage:

  Stage 1 (:00-:14)  GATHER & NARRATE — read what's happening, seed stories from the
                     Door-0 cycle map. Do NOT enter.
  Stage 2 (:15-:29)  NARROW + ADD-MISSED — prune weak stories, but ADD 2-3 new ones we
                     might have missed. Do NOT enter.
  Stage 3 (:30-:44)  NARROW HARD — cut to the few stories still alive. Do NOT enter.
  Stage 4 (:45-:59)  COMMIT — only stage where a NEW trade may be entered, on the
                     dominant surviving story.

Trade MANAGEMENT (Door 5) is unaffected — open trades are managed every candle.
Deterministic, pure Python — no AI, nothing to fake.
"""
import config

_NAMES = {
    1: "GATHER & NARRATE",
    2: "NARROW + ADD-MISSED",
    3: "NARROW HARD",
    4: "COMMIT (entry allowed)",
}


def stage_of(timestamp) -> tuple:
    """Return (stage_num 1-4, stage_name) for an M5 timestamp."""
    minute = timestamp.minute if hasattr(timestamp, "minute") else int(str(timestamp)[14:16])
    num = (minute // 15) + 1
    return num, _NAMES[num]


def entry_allowed(stage_num: int) -> bool:
    if not config.STAGE_FUNNEL_ENABLED:
        return True          # funnel off → original behavior (enter any candle)
    return stage_num >= config.ENTRY_STAGE


def guidance(stage_num: int) -> str:
    """Instruction handed to Door 3 so it narrows according to the stage."""
    if not config.STAGE_FUNNEL_ENABLED:
        return ""
    name = _NAMES[stage_num]
    base = (f"STAGE {stage_num}/4 — {name}.\n"
            "This hour is a narrowing funnel. Carry forward the story set from earlier stages.\n")
    if stage_num == 1:
        return base + ("Action: GATHER. Lay out the full set of possible stories for this hour, "
                       "seeded by the cycle map. Keep options OPEN. Do NOT force a trade.")
    if stage_num == 2:
        return base + ("Action: NARROW, but also ADD 2-3 stories you may have MISSED in stage 1. "
                       "Prune stories already invalidated by price. Do NOT force a trade.")
    if stage_num == 3:
        return base + ("Action: NARROW HARD. Cut to the few stories still alive. State which are "
                       "eliminated and why, in buyer/seller terms. Do NOT force a trade yet.")
    return base + ("Action: COMMIT. Only the dominant surviving story matters now. If it gives a "
                   "clean buyer/seller entry at a POI, this is the stage to take it.")
