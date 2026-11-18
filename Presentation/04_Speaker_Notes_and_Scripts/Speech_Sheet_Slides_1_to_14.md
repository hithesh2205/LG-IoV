# Speech sheet — slides 1 to 14

**Segment:** opening and status → CKKS mathematical foundations → the FHE-vs-plaintext baseline
**Runtime:** ~17 minutes (opening ~3½, maths and results ~13½)
**Arc:** *where we are* → *here is the maths you asked for* → *here is what the maths forces us to do* → *here is the experiment it made possible*

> **The one rule: do not read the slides.** Slides 5–10 are handwritten derivations —
> the audience can follow the numbers themselves. Your job is to say why each step
> is there. Point at the number, say what it *means*, move on.

---

## ⚠️ Read this before you go in

**Slide 7 has an arithmetic typo.** It shows `b_sum = 1474`. The three ciphertext
values on slide 6 are 721 + 801 + 452, which sum to **1974**.

Everything downstream uses 1974 and is correct — `b_agg = 1974 ÷ 3 = 658`, which is
the number slide 7 then carries into slide 8. So only the one printed digit is wrong.

**Do not read "1474" aloud.** Say *"the b values add to about nineteen seventy-four,
and dividing by three gives six fifty-eight."* If someone catches it, own it in one
sentence — *"typo on the slide, the working number is 1974, and 658 is right"* — and
carry on. Fixing the image before the meeting is better if you have five minutes.

**Second, smaller thing:** slide 9 writes `b(x) = a(x)·s(x) + e(x)`, and slide 10
decrypts with `m' = c₀ + c₁·s`. Those two need opposite signs to be consistent — the
standard form is `b = −a·s + e`. Only a cryptographer will notice. If asked, say the
sign convention follows the simplified integer example on slide 5 and the
implementation uses the standard form. Don't volunteer it.

---

## Slide 1 — Title · 30 sec

**Do not linger. Name it, frame it, move.**

> "Good afternoon. This is our Month 5–6 update on the privacy-preserving intrusion
> detection system for connected vehicles."

Then one framing sentence, so they know what they are listening for:

> "Two things to take away today. The encryption in our system is now **real** rather
> than a stand-in — and we can show it costs us **nothing** in accuracy."

**Then move on.** Don't read the names on the slide.

---

## Slide 2 — Recap from last meeting · 60 sec

**Three quick beats, then the action item — that last one is the point of the slide.**

> "Briefly, where we left things.
>
> We narrowed the detection model to ChebyKAN — about 44,000 parameters, fourteen times
> smaller than what we had before. Under encryption, parameter count is the cost driver,
> so that reduction is what makes everything else affordable.
>
> We demonstrated encrypted federated aggregation across all four datasets. And we
> committed to CKKS as the scheme, so the server never sees an individual vehicle's
> update."

**Land the fourth bullet deliberately — it sets up the next ten slides:**

> "And you gave us an action item: show the mathematics, don't just assert it. **Slides
> 5 through 10 are that.** We work the whole scheme through on numbers small enough to
> check by hand."

---

## Slide 3 — Contents · 20 sec

**Signpost, don't recite. Group them.**

> "The shape of today: the CKKS mathematics first, then the encrypted-versus-plaintext
> experiment, then what we found when we audited our own pipeline, then the V2X
> communication layer, and we close on multi-key CKKS — which is where the work goes
> next."

**Then straight on.** Five bullets read aloud one by one is dead air.

---

## Slide 4 — Where we stand · 90 sec

**The substantive opening slide. Give it real time.**

> "Before the detail — where the project actually is.
>
> Five deliverables that were overdue from Months 1 through 4 are now closed: the threat
> model, the security specification, the library evaluation, the packing and encoding
> module, and the NTT reference implementation. Several of those had never been started."

Then the tests — say what they are *for*, not how many:

> "We now have an automated test suite guarding three things: that the data pipeline is
> labelled and split honestly, that the cryptography is correct, and that the privacy
> property actually holds. That last one matters most — it is a counter in the code that
> checks, after every single round, that the server decrypted **zero** individual vehicle
> updates. It is checked, not claimed."

Then the placeholder, stated plainly:

> "Real CKKS now replaces the placeholder throughout the federated loop. I'll come back
> to what that placeholder was and why it mattered, on slide 14."

**Close on the strongest line — and say the part the slide leaves out:**

> "And the homomorphic aggregator is implemented and running. Worth noting: in your own
> project plan that is a **Month 7 to 12 item.** We are ahead of schedule on that track."

---

## Slide 5 — The CKKS scheme, simplified · 90 sec

**Frame it as answering their homework first.**

> "Last meeting you asked us to show the mathematics rather than assert it. Slides 5
> through 10 do that, on numbers small enough to check by hand."

Then walk the left column — slowly, these are the only definitions in the whole deck:

> "Three things define the scheme. A **secret key** — here just two numbers, four and
> nine. A **modulus** q, a hundred thousand and three, which everything wraps around.
> And a **scaling factor** Δ of a thousand, which is how we turn decimals into whole
> numbers, because the mathematics only works on integers.
>
> Three vehicles are each holding one weight — 0.10, 0.12, 0.09. In the real system
> that's 44,164 numbers per vehicle. Here it's one each, so you can follow it."

Then the equation, once:

> "Encryption is that single line. Take a random vector **a**, multiply by the secret
> key, add a small random noise **e**, and add the scaled weight. What comes out is
> **b**. The pair (a, b) is the ciphertext.
>
> The noise is the whole point — it is what makes this unbreakable. Without **e** it
> is one line of algebra to recover the key."

**Now land the red note. This is the hook for the second half of the deck:**

> "But notice the drawback in red. In this simplified scheme **every client shares the
> same secret key.** That means one compromised vehicle leaks the entire fleet. That
> is a real flaw, we are not hiding it — and it is exactly the problem xMK-CKKS solves
> later in this deck."

---

## Slide 6 — Encryption, three clients · 90 sec

**Do one client properly. Wave at the other two.**

> "Same equation, three times. Take client one.
>
> Its random vector **a** is 37 and 52. Multiply by the secret key: 37 times 4, plus 52
> times 9 — that's 616. Add the noise, 5. Then add the scaled weight: 0.10 times a
> thousand is 100. Total, **721**.
>
> So client one transmits the pair — the vector [37, 52], and 721."

Then the point of the slide:

> "And this is what matters: **721 tells you nothing about 0.10.** The weight has been
> buried under the key and the noise. Clients two and three do exactly the same with
> their own random vectors, and get 801 and 452."

**Pre-empt the obvious question:**

> "You might ask — the vector **a** is public, so why can't the server just subtract?
> Because it would need the secret key to do it, and the server never has it."

---

## Slide 7 — Aggregation on the server · 60 sec

**This is the moment the whole project rests on. Slow down.**

> "Now the server does something that looks far too simple to work.
>
> It adds the ciphertexts together. The **a** parts: 37 plus 21 plus 58 is 116; 52 plus
> 66 plus 14 is 132. And the **b** parts add to about nineteen seventy-four. Divide
> both by three, because there are three clients, and we get an aggregated ciphertext."

Pause. Then:

> "The server has just computed an average — **of numbers it cannot read.** It did not
> decrypt anything. It has no key. It performed ordinary addition on the encrypted
> values, and the encryption survived it.
>
> That property is what makes federated learning with encryption possible at all. Take
> that away and there is no project."

*(Say "nineteen seventy-four" — do not read the printed 1474.)*

---

## Slide 8 — Decryption, and the error · 90 sec

> "The aggregated ciphertext goes back to the clients, who do have the key.
>
> Multiply the aggregated **a** by the secret key — 38.66 times 4, plus 44 times 9 —
> gives 550.64. Subtract that from 658 and you get 107.36. Divide by the scaling
> factor to undo the Δ we multiplied in at the start, and you get **0.10736**."

Then the comparison — this is the payoff:

> "Now check it. The true average of 0.10, 0.12 and 0.09 is **0.10333**. We got
> 0.10736. The whole computation happened under encryption and the answer is right to
> about **four thousandths.**"

**Handle the error honestly and immediately — don't let them raise it first:**

> "That error is not a flaw in the scheme, it is an artefact of the toy numbers. Our
> modulus here is a hundred thousand, chosen so it fits on a page. The real system uses
> a 200-bit modulus, and there the error is around **ten to the minus eight** — six
> orders of magnitude below the noise that stochastic gradient descent already has. We
> measured it. It is not a source of accuracy loss, and slide 13 demonstrates that."

---

## Slide 9 — The real case: numbers become polynomials · 75 sec

**Signal the gear change.**

> "Everything so far used two-element vectors. The real scheme replaces them with
> **polynomials**, and this slide is that translation."

> "A layer's weights — a, b, c — become the coefficients of a polynomial: a plus b x
> plus c x squared, all scaled by Δ. So an entire weight tensor is now **one algebraic
> object** rather than thousands of separate numbers.
>
> The secret key becomes a polynomial too, living in this ring R_q — polynomials with
> integer coefficients mod q, where x to the N wraps around to minus one. That wrap-around
> is what keeps the degree bounded no matter how much you multiply."

**Give them the "so what", because the notation alone won't:**

> "The practical consequence is packing. At our parameters one ciphertext holds **4,096
> numbers**. So a 44,164-parameter update needs **eleven ciphertexts, not 44,164**. That
> single property is what takes this from theoretically interesting to actually
> affordable, and it is why we chose CKKS over the alternatives."

---

## Slide 10 — Public key, encryption, decryption · 75 sec

> "Same three steps as the toy example, now in polynomial form.
>
> The public key is a pair of polynomials, (a, b). The plaintext is a polynomial — here
> 288 plus 325x plus 471x squared, which is just some layer's scaled weights.
>
> To encrypt, we draw a fresh random polynomial **u** and two fresh noise terms, and
> produce two components: c₀ is b·u plus noise plus the message; c₁ is a·u plus noise.
> The ciphertext is that pair."

**The one sentence that makes this slide worth its time:**

> "Note that **u** and the noise are fresh every single time. Encrypt the same weights
> twice and you get two completely different ciphertexts. So the server cannot tell
> whether two vehicles submitted the same update, or whether a vehicle changed at all
> between rounds."

Then decryption, briefly:

> "Decryption is one line: c₀ plus c₁ times the secret key, then divide out Δ. The
> noise terms are small enough that they vanish in the rounding."

---

## Slide 11 — Noise, depth, and why it shapes the design · 90 sec

**This is the bridge from mathematics to engineering. Make that explicit.**

> "So far the maths has been permissive. This slide is where it starts saying no.
>
> Every operation on a ciphertext grows the noise. Additions grow it slowly.
> **Multiplying two ciphertexts** grows it fast, so fast that we have to consume one
> prime from the modulus chain each time to control it. Run out and the ciphertext
> stops decrypting — not degrades, stops."

> "A chain of L primes buys L minus 2 multiplications. And we cannot simply use a longer
> chain, because security depends on the ratio of the ring dimension to the total
> modulus bits. At our ring size of 8192, 128-bit security caps us at 218 bits — which
> gives us **exactly two multiplications.** No headroom."

**Then the number that makes it concrete:**

> "And the costs are wildly asymmetric. Adding two ciphertexts takes about **0.03
> milliseconds**. Multiplying two takes about **15**. That is a factor of roughly 490,
> and we measured it on our own machine."

**Close with the design consequence — this is the sentence to land:**

> "So the protocol was not designed for elegance. It was designed around a hard budget
> of two multiplications. Every architectural choice we make later in this deck —
> including how we score vehicles for trustworthiness — exists because of that
> constraint."

---

## Slide 12 — Baseline setup · 60 sec

**Short slide. Say why the experiment exists, not what's on it.**

> "Now to the experiment the maths made possible.
>
> The question is simple: **does encryption cost us accuracy?** We need that answered
> before we start quantization, because quantization introduces a second approximation.
> If we don't know what the first one costs, we can never attribute a later drop to the
> right cause."

> "So: real CKKS on one arm, exact plaintext on the other, **everything else held
> identical.** Same seeds, same data split, same initialisation, same order of
> operations. Three seeds, ten vehicles, five rounds."

**The last bullet is the one that makes it a real experiment:**

> "And we don't just claim the two paths are equivalent — there is a test that asserts
> the aggregation is **bitwise identical** between them. That is what makes this a
> controlled comparison rather than two runs that happen to look similar."

---

## Slide 13 — Results · 2 min

**The biggest slide in this segment. Give it the time.**

Start with the table, one sentence:

> "Four datasets, encrypted against plaintext. Look at the delta column — the largest
> gap anywhere is about one part in a thousand, and our seed-to-seed variation is larger
> than that."

Then the headline, said plainly:

> "**Encryption costs no accuracy.** Not 'a negligible amount' — nothing we can
> distinguish from random variation between runs."

**Now the honesty section. Say all of this before anyone asks — it is what buys you
credibility for the rest of the deck.**

> "Two of these numbers need reading carefully, and I'd rather flag them myself.
>
> **CAN-VTC shows 100%.** That is not a result to be proud of and it is not the
> labelling defect we found earlier — we checked that specifically. The DoS attack floods
> the bus with one CAN ID that never appears in clean traffic, at 51% of all messages.
> A single feature separates it at thirteen sigma. The split is verified clean. The task
> is simply easy. What that number measures is **flood detection, not generalisation.**
>
> **Car-Hacking is the benchmark we actually stand behind** — five real attack classes,
> injection density between 12 and 24%, and the best single feature only gets to 0.94.
> There is no shortcut there. If you want one number from this table, take that one.
>
> **VeReMi is near chance, and we know exactly why.** Its attacks are defined by how one
> sender's claims change over time — a vehicle reporting a position that never moves,
> for instance. When that dataset was cleaned, the sender ID column was dropped. Without
> it you cannot tell which messages came from which vehicle, so the task cannot be
> expressed at all. We predicted it would fail before training it, and it failed as
> predicted. It needs re-acquiring, and it is on the Month 6 list."

---

## Slide 14 — What this baseline establishes · 75 sec

**Three points. The first is a confession — deliver it evenly, not apologetically.**

> "Three things follow.
>
> **First** — and this is the important one. Until this month, what our training loop
> called encryption was a placeholder: a plain array with a tiny amount of noise added.
> It was meant to be temporary and it never got replaced. That means the FHE-versus-plaintext
> comparison in earlier decks **was not a controlled experiment** — the two arms drifted
> apart for reasons unrelated to encryption. With real CKKS in place, this is the first
> time we can actually answer the question."

> "**Second**, because accuracy is now demonstrably encryption-invariant, when we
> introduce INT8 quantization next, any accuracy change is attributable to quantization
> alone. We have isolated the variable. That is the entire purpose of doing this
> baseline before the quantization work rather than after."

> "**Third**, the costs, measured rather than estimated: about 42 milliseconds to encrypt
> an update, 118 to 230 for the encrypted distance computation, and 2.47 megabytes on the
> wire per vehicle per round."

**Set up the next section:**

> "The time is comfortable. **The 2.47 megabytes is not** — and that becomes the honest
> problem we deal with on the bandwidth slide."

---

## Timing

| Slide | Target | Running |
|---|---|---|
| 1 | 0:30 | 0:30 |
| 2 | 1:00 | 1:30 |
| 3 | 0:20 | 1:50 |
| 4 | 1:30 | 3:20 |
| 5 | 1:30 | 4:50 |
| 6 | 1:30 | 6:20 |
| 7 | 1:00 | 7:20 |
| 8 | 1:30 | 8:50 |
| 9 | 1:15 | 10:05 |
| 10 | 1:15 | 11:20 |
| 11 | 1:30 | 12:50 |
| 12 | 1:00 | 13:50 |
| 13 | 2:00 | 15:50 |
| 14 | 1:15 | 17:05 |

**If you get cut short:** slides **4 → 5 → 7 → 8 → 13**. Where we stand, the setup, the
aggregation that works under encryption, the answer coming out right, and the results.
Skip 6, 9 and 10 — they are detail, not argument. Slide 3 can always go.

---

## Questions to expect in this segment

**"Why is the error 0.004? That seems large."**
> Toy modulus, chosen so the arithmetic fits on a page. At our real parameters it is
> around 1e-8, which we measured. Slide 13 is the evidence that it costs no accuracy.

**"If the server can add the ciphertexts, why can't it decrypt them?"**
> Addition doesn't need the key; decryption does. The server can compute on the values
> without ever being able to read them — that is precisely what homomorphic means.

**"All clients sharing one secret key is a serious weakness."**
> Agreed, and that is why we flagged it in red on slide 5 rather than glossing over it.
> It is the exact problem the xMK-CKKS section addresses — every device gets its own key,
> and no single compromise leaks the fleet.

**"How do we know the encrypted and plaintext runs are really comparable?"**
> There is a test asserting the aggregation is bitwise identical between the two
> backends. If they ever diverge, the test suite fails.

**"Was the earlier comparison wrong, then?"**
> Yes. The old 'encryption' was a placeholder that added noise, so the two arms diverged
> for reasons unrelated to encryption. We found it, replaced it with real CKKS, and
> re-ran everything. Every number in today's deck comes from the corrected pipeline.

**"Can you do multiplication as well as addition?"**
> Yes, but it's expensive — about 490 times the cost of addition — and our parameters
> allow exactly two per round. That budget shapes the whole protocol design.
