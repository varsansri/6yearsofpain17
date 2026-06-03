# 6YEARSOFPAIN — Vision & Ideas (raw, from the founder)

> This file captures the original vision in the user's own words, lightly organized.
> It is the "why" behind the project. Code should be checked AGAINST this, not the reverse.

---

## Idea 1 — Structure first, then Points of Interest, then aligned candle reading

**Core principle:** Before any strategy or concept, you must understand **STRUCTURE** first,
then the **POINTS OF INTEREST (POI)**. Structure is the biggest overall thing — every single
concept rides on top of it. No matter the strategy, structure comes first.

### The two foundational steps (should map to Door 1 + Door 2)
There are really **three things** happening, and it feels like Door 1 & Door 2's true purpose:

1. **Overall picture / context** — get a full understanding of **every single timeframe**.
   Find the overall direction, aggression, buying & selling pressure — mostly about the
   **higher timeframes**. Same buyer/seller thinking process applied to direction.

2. **Mark the Points of Interest** — mark lines at highs, lows, and every notable area.
   The goal: *if price returns to this area in the future, how will it react?* Also derive
   the **possibilities & probabilities** of where price wants to move from each POI.

3. **Aligned candle-by-candle reading** — every candle move must align with the overall
   direction already established in steps 1 & 2.

### POI strength = timeframe alignment
- A POI is **stronger the more timeframes "see" it.** If the same POI shows up on every
  timeframe, it is very likely valuable.
- A POI only on a higher timeframe is **still valuable** — you can expect *something* to
  happen in that area.
- Sometimes a POI isn't respected at all — that's fine, it doesn't matter.
- Think of POIs as **reaction zones**: they may act as resistance, support, a consolidation
  zone — or as nothing (people unwilling to act there).

### CRITICAL backtest bug to avoid — no future candle leakage
- In backtesting, when jumping between higher and lower timeframes, the higher-TF candle
  must **NOT** appear as a **fully-formed** candle if it hasn't closed yet.
- A fully-formed higher-TF candle leaks the future → tells you what already happened.
- Live markets don't work that way — **every timeframe must show the exact in-progress
  candle structure, not a future-formed one.** This must be enforced. (Keep this flagged.)

### Top-down flow
Price/analysis should start from the **higher timeframe → lower timeframe**: mark out and
lay out every direction and everything to be read at the top, then every candle move on the
lower TF must align with that overall direction from steps 1 & 2.

### Strict thinking restriction (the original soul of the project)
The system is **restricted to think only in buyers vs sellers** — NOT concepts, NOT
strategies, NOT pattern recognition, NOT modern technical terms.

**Allowed vocabulary (super basic only):**
- support / resistance
- points of interest
- structure
- candle understanding: body, volume, momentum, velocity, imbalances
- anything that helps read raw buyer/seller behavior

**Not allowed:** pattern names, strategy names, derived modern technical terms.

### Open questions / concerns from the founder
- Is this POI + structure marking **already in the GitHub code**, or did it get scattered
  across different doors / lost as the project grew?
- **Suspicion:** "I feel like it is not doing it." The project started with this motivation
  but as code grew bigger it drifted — the coding took its own various directions and the
  original thinking pattern may have been lost.
- **Request:** if it's not doing this, give a clear plan to bring it back in line with the
  original vision.

---

## Idea 2 — Trading happens in PHASES/STAGES; apply the story-narrowing process to Direction & POI, not just Entry

**Keep everything good that already exists** + the three steps from Idea 1. This adds the
**staged, narrowing-funnel** way the analysis should actually run.

### Trading has stages (model it as 4)
- A trading cycle has phases. Stage 1 can be narrowed: "only these ~3 possibilities can lead
  to Stage 1 happening." When Stage 1 actually happens, you narrow further to even smaller
  possibilities. This is the whole method: **continuously narrow the story space.**
- When price reaches a POI (read with candle momentum), we already have pre-built **possible
  stories / narrations** from the questions. The AI generates possibilities from everything it
  knew before → forms **different lines of stories**. As price moves in real time and conviction
  strengthens, the possibilities **narrow down** until you have solid info: "these are the
  ONLY possibilities still alive in this story right now."

### The funnel structure (per 1-hour cycle, split into 4 × 15-min stages)
This is **not** one set of possibilities for the whole day. Each session / each 4-hour block
holds different possibilities. Start each fresh **4-hour** by gathering as much data as
possible. Every ~15-30 min, **reconsider all data and re-form the story lines.**

Within each 1-hour candle, split into four 15-min stages:
1. **Stage 1 (1st 15 min):** read what's happening + begin narrating stories from gathered data.
2. **Stage 2 (2nd 15 min):** narrow the stories down AND **add new possibilities** (2-3 most
   likely) — because we could have missed some stories earlier.
3. **Stage 3 (3rd 15 min):** narrow it down hard ("terribly narrow it down"). Skim as much as
   possible.
4. **Stage 4 (4th 15 min):** narrow to very few stories → **this is the only stage we ENTER a
   trade**, based on the buyer/seller battle conditions in those candles.

After finishing one 1-hour cycle: **don't fully reset** — come back to the overall picture, then
the 15-min stages run again for the next 1-hour candle (gather → narrow → add-missed → narrow →
enter). Repeat.

> Emphasis: most of the work / focus is in **Stage 2 and Stage 3** (forming + narrowing stories),
> not just the entry moment.

### THE KEY GAP (what's wrong today)
Right now the candle-by-candle understanding **only does the ENTRY stage** properly. The same
"gather as much data as possible → narrow it into a story" process needs to also run for:
- **DIRECTION** (the higher-TF direction stage), and
- **POI** — and **POI is MORE important than direction.** If we're wrong about the POI/zones,
  or we fail to consider the possibilities there, that's the critical failure point.

So: Direction, POI, and Entry should **each** be a full gather→narrow→story engine — not just Entry.

### See it through 4 concepts, in buyer/seller language (don't lose any concept)
- Don't view a zone through a single concept — view it through **4 different concepts** so no
  concept is missed.
- SMC (and similar) contain many terms, but **we don't want the patterns.** Keep the underlying
  meaning of those terminologies but **convert each concept into buyer/seller language** and
  draw it onto the market.
- Don't just restrict/ban the term — **derive it** into buyer/seller terms and ask *"what does
  this mean to us?"* rather than accepting a term without questioning its validity.
- We already judge absorption, traps, etc. — extend that same treatment everywhere.

### Reinforced concern
When a 1-hour cycle starts we already gather overall data from the prior hour — but the
Direction and POI work isn't running the full story engine the way Entry does. That's the fix.

---

## Idea 3 — Warm start: never enter a fresh session blind; bootstrap from the previous period's accumulated data

**The point:** when starting fresh, do **not** walk into a session and begin gathering from
zero. First run the **full process on the previous period** to accumulate enough data, store it
as **accumulated data**, and use it to seed the present cycle.

### How a fresh start works
- Use the **previous context** (overall direction, POI, AND entry) to map out the **present**
  1-hour's direction, POI, and possibilities — then begin the **first 15-min stage with its own
  narration already seeded** (not blank).
- It then narrows naturally down through Phase 2 → 3 → 4. By Phase 4 everything is already
  skimmed down into the entry test.

### The data windows each layer pulls from on a fresh start (the concrete rule)
Instead of loading one giant blob of the whole 4-hour/1-hour, each layer takes a **timeframe +
its last stage**:

| Layer | Pulls from (warm-start seed) |
|---|---|
| **Direction** | the last 1-hour's overall direction + the four hours (4H context) |
| **POI** | the **final stage** of the last 1 hour → i.e. the 30-min and 15-min |
| **Entry** | the last 15-min split into 4 sections, considering only entry/candle data of the **last 15-min, last 5-min, and 1-min** |

### Why
- You are **not** entering the session blindly and aggregating from scratch — you've **already
  gathered enough data** to act in the very first stage.
- In fact, with this seed it **could** technically take a trade in the fresh start of the first
  stage (enough data exists). **But we deliberately don't** — the whole goal is to narrow as much
  as possible first, so we start narrowing from that seeded point at the start of the hour, then
  the accumulated data **carries forward into the next session.**

> (User was thinking aloud / self-correcting here, but the takeaway is firm: warm-start every
> cycle from the previous period's accumulated direction + POI + entry data, then narrow.)

---

## Idea 4 — The human top-down workflow + the "Milky Way" mental model

This is how the founder actually trades by hand. The system should mirror this.

### The manual top-down process (high TF → low TF)
1. **4-hour first.** Open the 4H chart (≈1-3 months of candles). Mark the important overall
   levels — highs/lows and POIs. Analyze each timeframe's **structure, POI, and candle
   behavior**. Notice *everything possible* in this TF before moving down.
2. **1-hour next.** (Last few days, ~100 1H candles.) Do the same: mark where **bad
   liquidations** happened, where important **POIs** sit, candle behavior at each stage, **where
   most volume happened, where most momentum happened.** (This volume/momentum read is done on
   BOTH 4H and 1H.)
3. **15-minute.** Same again — structure, POI, volume, momentum, what buyers say, what sellers
   say, what each candle says. Gather the **overall possibilities, phases, and probabilities of
   future stories.** ← **The real session starts here at 15-min.** By now you hold lots of data
   on *where price wants to come* and *what reaction you'll get there.*
4. **5-min / 1-min (execution).** Because the overall is already mapped and you know where the
   reactions will happen, **you already know where to look.** You do **not** have to wait for an
   important POI to physically arrive — since you know the price areas and expected reactions,
   you can just drop to the lower TF and start trading. Use 5m/1m mainly to gather execution data,
   because everything was laid out beforehand.

> **Key insight:** pre-mapping at high TF lets you **act immediately** at low TF. The lower
> timeframe is execution, not discovery — discovery already happened top-down.

### The Milky Way analogy (the mental model behind it)
- You're in a spaceship — a tiny object. From a distance you see the **overall galaxy
  structure.** Mark the important future **events / planetary collisions** and *at what
  space-time* they'll occur. Mark them, then zoom into a **solar system.**
- In the solar system, mark the **nearby solar systems / big planets / events** likely in a
  given timeframe — so you know *which time, what happens*, and can predict. Narrow to the solar
  system.
- Traveling through, you see **each planet's life cycle, ecosystem, which are weaker** — every
  planet as a life-cycle curve + probabilities. The overall structure is still in view: overall
  galaxy + nearby solar systems + present solar system's planet life cycles.
- **Because you already laid it all down, you don't need to constantly re-consider the nearby
  possibilities** — they only matter *when their time comes.* Keep them **in the back of your
  mind, marked on a calendar.** When the time comes, **connect the dots** → "this is the time to
  get out."
- Same for a single planet: you've calculated its life cycle — *"this planet explodes at time
  T, but I can use its resources during period P; as long as that holds I make this decision /
  accumulate these resources; before it explodes, I move to the next thing."*

> Closest analogy, not a perfect 1:1 map. **The takeaway:** future possibilities are
> **pre-scheduled** (a calendar of where/when reactions are expected), held in the background,
> and **activated only when price/time reaches them** — while the overall structure is always
> retained.

---

## Idea 5 — The door architecture (Idea / Question / Rules), anti-faking, Door 0, 5-min dual data, and quality metrics

This explains *why the project is built the way it is* and what to add.

### Each door = three sections
1. **Idea section** — the ideology/logic for that door (what it's trying to achieve).
2. **Question section** — questions that reinforce the idea. The AI answers them **creatively,
   based on the specific situation** — NOT the same answer every time. It must actually *think*.
   Like real open questions: the same question can have many different valid answers depending on
   the situation. That's intended.
3. **Rules section** — checks the processes. Each process is judged **done right or wrong.**

### Why hardcoded
Once you give an AI an idea/logic, **over iterations it modifies itself and forgets the whole
process.** So the process is **hardcoded** to keep it looking at things the right way. The idea +
questions reduce the AI to the intended idea of that door.

### The flow & the gate
- AI reads the **idea** → understands what it must do → reinforces it by **answering the
  questions** creatively per situation → runs the **processes** on the data → moves to the next
  door.
- The next door's **rules section checks** those processes. If the previous door ran a process
  **wrong / passed wrong data**, the gate **blocks it and forces a redo — with feedback.**
- **The only way forward is doing the past process right, the way we want.**

### The core purpose: stop the AI inventing its own structure
We don't want the AI building its own one-off structure/thinking. The structure — *what terms it
must use, what steps it must do* — is **already laid out** in the idea + question sections. The
AI must **process data the way we defined.**

### The anti-faking problem (critical)
- Over iterations, and especially when you lean hard on its reasoning, the AI tends to **fake /
  cheat** — it finds workarounds to answer the questions in a **fake way.** It does this a lot
  under heavy "brain power" use.
- That's exactly why there's a **rules section before every door opens** — to catch the fake and
  force the redo.

### What to ADD for the present plan
- Don't keep it as a **single structure.** Instead, create a **visual structure before each
  door.**
- Create a **DOOR 0** that holds the **visuals / overall ideology**, so every time it runs a
  session it (re)focuses on the **overall ideology first** before entering the door chain.

### Order-flow data clarification (I'd missed stating this)
- **Order flow data exists ONLY at the 5-minute timeframe.** It must use that data to understand
  the market.
- So at 5-min there are **TWO data types** fused: **(a) order-flow data** and **(b) candle data**
  — both used together to understand the 5-min, **because 5-min is where trading actually
  starts.**

### Quality metrics (the "numbers" problem)
- The questions / rules / ideology currently **lack numbers**, so the AI produces vague,
  variable "quality" outputs. We need to **measure quality**:
  - quality of **ideas**,
  - quality of **question-answering**,
  - quality of **processing**,
  - and **each timeframe** + **each process** should carry its own internal **measures/metrics**,
  - so we can confirm everything is **convincing enough.**

### BUT — give it room to breathe (the counter-tension)
- Sometimes a metric **can't** be extracted from a question — not enough data, or the candle
  answer is genuinely **vague.** We must **not force** it.
- When you force the AI to produce a specific output it can't honestly produce, it **fakes it /
  hides behind analogy or ideology** to satisfy the demand.
- So: **give it enough space to breathe so it doesn't fake** — while still doing the real work.
  (Balance: measure quality and demand rigor, but allow honest "insufficient data / unclear"
  answers instead of forcing a fabricated metric.)

---

## Idea 6 — Dual-score every POI: structural validity + crowd attention (the measurement layer)

**Inspiration — how four domains solved "the others are wrong / unpredictable":**
- **Quantum mechanics** — stop predicting the exact outcome; map the **probability
  distribution.** Uncertainty is the output, not a failure.
- **Game theory** — model the **other players explicitly.** Best move *given what others will
  do.* Wrong players become **input, not noise.**
- **Keynesian beauty contest** — **layered thinking.** L0 what's beautiful, L1 what most think is
  beautiful, L2 what most think most think. Model the crowd's reasoning on top of your answer.
- **Schelling points** — you **can predict the wrong answer** because focal wrong answers are
  consistent and repeatable (round numbers attract attention). Map focal points **alongside**
  correct points and treat **both as real data.**

**Common thread:** none of them tried to make their correct answer *more correct*. They all
**expanded the model to include crowd behavior as a variable**, not noise.

### What this means for the POI engine (the measurement layer)
Every POI marker carries **two scores**:
1. **Structural validity score** — our buyer/seller structural read (is this a real level?).
2. **Crowd attention score** — how *focal* it is: round numbers, previous session highs/lows,
   obvious levels even a wrong trader would notice.

**Reaction rule:**
- **Aligned** (structural ✓ + focal ✓) → **highest conviction**, expect a clean reaction.
- **Conflict** (one high, one low) → the conflict **is information**: expect a **fight at that
  level, not a clean reaction.** Trade it differently (don't expect a tidy bounce).

> This is the concrete answer to the "quality metrics / numbers" need from [[Idea 5]] — POIs
> stop being a single fuzzy label and become a **2-axis measured object**. It also satisfies the
> "see it through multiple concepts" point from [[Idea 2]]: structural truth AND crowd focal
> truth, both mapped, neither discarded.

### Implementation note for the POI engine (Task 2)
- Crowd-attention score is **mostly computable in Python** (round-number proximity, prior
  session/day H/L, prior week H/L, equal highs/lows) — cheap, deterministic, no AI faking.
- Structural-validity score comes from the buyer/seller read (multi-TF alignment).
- Store both on each POI; conviction logic reads the pair (aligned vs conflict).

---

<!-- Next ideas will be appended below -->
