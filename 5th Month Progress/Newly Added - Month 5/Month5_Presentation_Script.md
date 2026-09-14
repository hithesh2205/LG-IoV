# Month 5 Status Update — Speaking Script

**Deck:** `Month5_Status_Update.pptx` (13 slides)
**Runtime:** ~16 minutes + questions
**Split:** three speakers — setup / substance / forward-look

> Say it in your own words. This is a guide to *what to land*, not a text to read out.
> The one rule: **do not read the slides aloud.** The audience can read. Your job is
> to say the thing the slide doesn't.

---

## Speaker A — slides 1–4 · setup and the audit (≈ 5 min)

### Slide 1 — Title · 20 sec

> "Good afternoon. This is our Month 5 update on the privacy-preserving intrusion
> detection system for connected vehicles.
>
> Short version before we start: this month didn't go the way we planned, and we
> think it went better because of it. I'll explain what we mean."

**Then move on.** Don't linger on the title.

---

### Slide 2 — Where we stand · 90 sec

> "Four numbers to anchor everything.
>
> We're five months into twelve.
>
> Of the eight deliverables that were due by end of Month 4, seven are now closed.
> That was five when the month started.
>
> We have a hundred and five automated tests that check the experiments are set up
> correctly — not that the model is good, but that the *measurement* is honest. I'll
> come back to why that matters.
>
> And there's one thing blocking us. It's not a technical problem. It's a purchase."

Pause. Then the green box:

> "The headline result: **encryption costs us nothing in accuracy.** On all four
> datasets, the encrypted system and the unencrypted one perform the same to within
> normal run-to-run variation. And the server never once decrypted an individual
> vehicle's data."

---

### Slide 3 — What Month 5 became · 90 sec

> "We started this month planning to implement a newer encryption scheme, from a
> 2023 paper.
>
> Before building on top of the existing system, we audited it. Standard practice —
> check the foundation before you add a floor.
>
> The audit found seven problems. Several of them meant our earlier results weren't
> measuring what we thought they were measuring."

Slow down here. This is the moment that sets the tone.

> "The one that mattered most: the encryption in our training loop wasn't actually
> encryption. It was a placeholder — a plain array with a tiny bit of noise added.
> It was always meant to be temporary. It just never got replaced.
>
> So Month 5 became: fix the foundation first, then build. That's what we did. And
> once that was done, we went back and closed three deliverables from Months 1 to 4
> that had never been started."

> "We'd rather find this ourselves in month five than have it found in month eleven."

---

### Slide 4 — The seven defects · 2 min

**Do not read the table.** Pick three.

> "I won't go through all seven. Three are worth your time.
>
> **D1 — our labels came from filenames.** Each attack recording was labelled
> entirely as that attack. But those recordings are mostly *normal* traffic with
> attacks injected into it. So we were training a model to recognise which file it
> was looking at, not whether an attack was happening. That's why one dataset was
> reporting a hundred percent accuracy. That number wasn't an achievement. It was a
> symptom.
>
> **D4 — the server was decrypting every vehicle's update.** This is the serious one.
> The entire point of the project is that the server can't read individual
> contributions. Our slides said that. Our code did the opposite — it decrypted
> every vehicle's full update, every round, to run the outlier check. Under real
> encryption that code simply cannot run.
>
> **D6 — someone had removed the transport security** in Month 4, on the reasoning
> that homomorphic encryption already covers it. It doesn't. Encryption hides the
> contents. It doesn't tell you who sent the message, or whether it was modified in
> transit. Those are different problems.
>
> All seven are fixed, and each now has an automated test so it can't come back
> quietly."

---

## Speaker B — slides 5–9 · results and what we built (≈ 6 min)

### Slide 5 — Results · 90 sec

> "So here's what the system actually does, now that we can trust the measurement.
>
> Three random seeds, ten simulated vehicles, five rounds of federated training.
> Every dataset, encrypted versus unencrypted.
>
> Look at the difference column. The largest gap is about one part in a thousand,
> and our seed-to-seed variation is larger than that. **Encryption is free in
> accuracy terms.**
>
> That sounds obvious, but it's the first time we could actually demonstrate it. The
> old setup couldn't answer this question at all — the fake encryption was adding
> noise, so the two versions drifted apart for reasons that had nothing to do with
> encryption."

Then the amber box — say this yourself, don't wait to be asked:

> "Two of these numbers need reading carefully. Car-Hacking is our real benchmark.
> CAN-VTC is close to trivial — the attack floods the bus, so it's easy to spot.
> And VeReMi is barely above guessing. I'll explain that on the next slide."

---

### Slide 6 — The chart · 60 sec

> "Visually — the blue and grey bars are the same height on every dataset. That's
> the result.
>
> On the right: zero. Across every run, the server decrypted zero individual vehicle
> updates. That's not a claim in a document, it's a counter in the code that gets
> checked after every round.
>
> On VeReMi — we measured this dataset *before* training it. The features simply
> don't separate the two classes. And there's a reason: VeReMi's attacks are things
> like a vehicle reporting a position that never changes. You can only see that by
> watching one vehicle over time. When the data was cleaned, the sender ID was
> dropped — so we can't tell which messages came from which vehicle. The task can't
> be expressed without it.
>
> We predicted it would fail, then trained it, and it failed exactly as predicted.
> We need to re-download that dataset."

---

### Slide 7 — What we built · 90 sec

> "Six things. I'll take the two that matter most.
>
> **The aggregation.** The server needs to spot a vehicle sending bad data. The
> usual method compares every vehicle against every other vehicle — which means
> seeing all their data. Impossible when it's encrypted. The method we adopted
> instead compares each vehicle to the *previous shared model*, which the server
> already has. That comparison can be done on encrypted data. Outliers get their
> influence reduced — not removed, reduced. That matters for vehicles, because a car
> that met a genuinely new attack looks like an outlier, and it's the most valuable
> one there.
>
> **Item D — a fix the paper doesn't have.** The scheme splits the decryption key
> across vehicles, and the pieces only cancel out if every vehicle reports back. The
> paper picks a random subset each round. So one vehicle in a tunnel, and decryption
> returns garbage — silently. For a laptop simulation that never shows up. For real
> cars it's Tuesday. We changed it so the key pieces are regenerated for whoever
> actually turns up each round."

---

### Slide 8 — Three older deliverables closed · 60 sec

> "Then we went back to Months 1 through 4.
>
> Three deliverables had never been started. All three are now done or substantially
> done — a bandwidth optimisation module, the core cryptographic transform, and a
> hardware benchmark.
>
> Deliverables due by end of Month 4 went from five of eight to seven of eight."

---

### Slide 9 — Two engineering results · 90 sec

> "Two concrete results, both measured.
>
> **Left — we cut upload size by thirty percent, with no accuracy cost.** The
> interesting part is where it came from. It wasn't a cryptography trick. We looked
> at what the server actually does with each encrypted update, and noticed the two
> operations work on separate copies — they don't feed into each other. So the data
> needs less cryptographic 'headroom' than we were sending. Encrypted data shrinks
> as you use up that headroom, so vehicles now use one level before uploading.
> Three-and-a-half megabytes down to two-and-a-half.
>
> **Right — the core transform is eleven times faster than the naive approach.**
>
> Worth admitting: our first version was *slower* than naive. The algorithm was
> right; we'd written it in a way that made about eight thousand tiny function calls
> per operation, and the overhead swamped the maths. Restructuring it made it
> fifty-three times faster.
>
> That's a genuinely useful lesson for the embedded work: performance here is about
> memory access patterns, not arithmetic."

---

## Speaker C — slides 10–13 · limitations, the ask, close (≈ 4 min)

### Slide 10 — What we are not claiming · 90 sec

Deliver this steadily. It builds credibility rather than costing it.

> "Four things we're deliberately not claiming.
>
> **One.** We don't yet have full multi-key encryption. The maths is real, but the
> key-splitting part is modelled, not implemented — because the library we're using
> has no interface for it. We've picked the replacement library and that's the Month
> 6 priority. Until then we won't describe it as complete in any write-up.
>
> **Two.** Nothing has run on real hardware. Everything we've shown was measured on
> a laptop.
>
> **Three.** Our outlier detection works against obvious attacks. It's untested
> against a patient attacker sending small biased updates over many rounds — and our
> method actually rewards staying close to the average, so that's a real weakness.
> The experiment is scheduled.
>
> **Four.** VeReMi contributes nothing until we re-download it.
>
> Every one of these has a date attached."

---

### Slide 11 — The blocker and the ask · 90 sec

**Slow right down. This is why the meeting exists.**

> "Which brings us to the one thing we need from this meeting.
>
> Every remaining item from Months 1 to 4 is blocked on the same thing. Not a
> technical problem. **No hardware has been ordered.**
>
> The embedded work is now software-complete. The transform is written and tested.
> The benchmark runs. We just have nothing to run it on.
>
> We're asking for two boards.
>
> An **NXP S32G evaluation board** — that's the realistic production target, an
> automotive processor built for exactly this.
>
> And a **Raspberry Pi 5.** That one's the important half. It's inexpensive, we can
> have it this week, and it's ARM — same processor family. It lets us start
> cross-compiling and profiling immediately, while the automotive board is sourced.
>
> Without a board, Months 7 through 12 can't start either — the hardware-in-the-loop
> testing and the power measurements both need one."

Then stop talking. Let them respond.

---

### Slide 12 — Month 6 plan · 60 sec

> "Priorities for next month.
>
> Order the hardware — an hour of work, unblocks everything.
>
> Two small security fixes we've already identified — a few hours.
>
> Then the big one: migrating to the new cryptography library. Twelve days. That's
> what makes the multi-key encryption real rather than modelled.
>
> Then the attacker experiment, scaling up to fifty vehicles, and re-acquiring
> VeReMi.
>
> One good sign — the embedded work shrank from about forty days to twenty-two this
> month, because we did the software half."

---

### Slide 13 — Summary · 45 sec

> "To close.
>
> We audited the project and fixed seven problems — all verified by automated tests.
>
> We replaced the placeholder encryption with the real thing, and showed it costs no
> accuracy.
>
> We closed three older deliverables — five of eight became seven of eight.
>
> And one thing is blocking us, and it's a board.
>
> Everything is documented and on GitHub — a twenty-seven page technical document
> plus sixteen supporting ones.
>
> Happy to take questions."

---

## If you're cut to 5 minutes

Slides **2 → 5 → 11**. Nothing else.

> Where we stand (four numbers) → the results table (encryption is free) → the ask
> (order a board).

---

## Questions you should expect

**"Why did it take five months to find these problems?"**
> Honest answer: we were adding features rather than checking foundations. The
> placeholder encryption was always meant to be temporary and nobody revisited it.
> That's why we now have a hundred and five automated tests — so the checking isn't
> dependent on someone remembering.

**"Are the old results in your earlier presentations wrong?"**
> Yes. We've marked them invalid in the repository and kept them only for record.
> Every number in today's deck is from re-runs on the corrected system.

**"Why is CAN-VTC at a hundred percent? Isn't that the same problem again?"**
> No — different cause, and we checked. The labels are correct now. That attack
> floods the bus with one message ID, so it's genuinely easy to detect. We measured
> it: a single feature separates it perfectly. We report it, but Car-Hacking is the
> benchmark we'd stand behind.

**"Why not just use a smaller model to fix the bandwidth?"**
> That's the most direct lever and we've already used it — the model went from about
> six hundred thousand parameters to forty-four thousand. Bandwidth scales directly
> with parameter count. Beyond this, the bigger win is having roadside units combine
> updates before they reach the server, and that's an architecture decision we
> should take early.

**"How much does the encryption slow things down?"**
> About a hundred and twenty milliseconds per vehicle per round on our laptop, and
> two-and-a-half megabytes uploaded. The time is fine. The bandwidth is the real
> concern for vehicle networks and it's why the packing work mattered.

**"Is this publishable?"**
> Possibly, on two points: the dropout fix, which the paper we're building on
> doesn't address, and the patient-attacker weakness if it turns out to be real.
> Both need the Month 6 experiments first.

**"What if you don't get the hardware?"**
> We can keep going on the cryptography and the migration for Month 6. But the
> embedded deliverables stay blocked, and Months 7 to 12 assume they're done — so
> the gap compounds rather than staying still.

---

## Practical notes

- **Add your three names to the title slide.** It's currently blank.
- Every slide has speaker notes in PowerPoint — press **Alt + F5** for presenter view.
- Open a scroll-through in PowerPoint before the meeting. The deck was validated
  programmatically but never visually rendered.
- Slides 4, 5, 8 and 12 have tables — check those specifically for row spacing.
- If asked for detail beyond what's here, point at the repository rather than
  improvising. The master PDF answers most of it.
