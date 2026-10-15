"""Narration script for the LGSI IoV project video — the single source of truth.

Conversational explainer style: we follow one vehicle ("Car 7") through the
whole system, ask the viewer questions, and pause for a beat before answers.

A sentence is one of:
  "text"                      caption and speech are the same
  ("caption", "spoken")       the voice needs a phonetic spelling (e.g. "C K K S")
  ("caption", "spoken", 1.6)  ...plus a silent pause (seconds) after it

Visual cues in ``scenes.py`` refer to sentences by their index inside a scene,
so if you add or remove a sentence, check the matching scene builder.

Facts are taken from:
  README.md, 5th Month Progress/Documentation/11_current_status.md,
  12_next_steps.md, 08_threat_model.md, 17_multikey_scheme_decision.md,
  Dataset/README.md, after_F_function/reports/final_report.md and the
  08.10.26 Weekly_Meet Final draft deck.
"""

# chapter labels shown in the header bar (scene "chapter" indexes into this)
CHAPTERS = ["Problem", "Idea", "Data", "Attacks", "Math", "Results", "Next", "Wrap-up"]

SCENES = [
    dict(
        id="title",
        chapter=None,
        title="",
        sentences=[
            "Your car has dozens of tiny computers inside it. And any one of them could be lying.",
            "Let's see how a whole fleet of cars can learn to catch hackers, without any car giving away its secrets.",
        ],
    ),
    dict(
        id="problem",
        chapter=0,
        title="Meet Car 7",
        sentences=[
            "Meet Car 7. Its engine, brakes and steering all chat over one shared wire: the CAN bus.",
            "Here's the catch. The CAN bus trusts everyone. No passwords. No locks.",
            "So when an attacker slips in a fake message, everyone just believes it.",
            ("Not science fiction: in 2015, hackers took over a Jeep on a highway, and 1.4 million cars were recalled.",
             "This is not science fiction. In twenty fifteen, hackers took over a Jeep on a highway, and 1.4 million cars were recalled."),
            "Car 7 needs a security guard that knows what normal traffic looks like. But one car alone never sees enough attacks to learn.",
        ],
    ),
    dict(
        id="idea",
        chapter=1,
        title="Learning together, secretly",
        sentences=[
            "So why not send every car's data to one big server?",
            "Because that data is private. It shows where you go, and how you drive.",
            "Federated learning flips it around: the data stays in the car, and only what the model learned travels.",
            ("Quick question: is that private enough? Think about it.",
             "Quick question. Is that private enough? Think about it.", 1.6),
            "Sadly, no. Clever attacks can rebuild your data from those updates. So we lock them.",
            ("Each car locks its update with CKKS encryption. The server adds up the locked boxes without opening them. It has no key.",
             "Each car locks its update with C K K S encryption. The server adds up the locked boxes, without opening them. It has no key."),
            "Only the combined result is unlocked, and a smarter model rides back to every car.",
        ],
    ),
    dict(
        id="data",
        chapter=2,
        title="Feeding the model",
        sentences=[
            "Where does the training data come from? Four public datasets, 8.6 gigabytes of real traffic.",
            ("Our main one, Car-Hacking, has millions of real CAN messages, each tagged normal or injected.",
             "Our main one, Car Hacking, has millions of real can messages, each tagged normal, or injected."),
            "We slide a window over the stream, 64 messages at a time, stepping 16, and squeeze each window into 46 numbers.",
            "Byte statistics, which IDs dominate, and how random the payload looks.",
            ("Whole blocks go to train, validation or test, so the test never peeks. Then the data is dealt to ten cars, each with a different mix.",
             "Whole blocks go to train, validation, or test, so the test never peeks. Then the data is dealt to ten cars, each with a different mix."),
        ],
    ),
    dict(
        id="attacks",
        chapter=3,
        title="Spot the attack",
        sentences=[
            "Let's play spot the attack. This is normal traffic.",
            ("Denial of service: one top-priority ID floods the bus, so nothing else gets through.",
             "Denial of service. One top priority I D floods the bus, so nothing else gets through."),
            ("Fuzzing: random IDs, random junk.", "Fuzzing. Random I Ds, random junk."),
            ("Spoofing: fake RPM or gear readings that lie to the dashboard.",
             "Spoofing. Fake R P M, or gear readings, that lie to the dashboard."),
            ("Our model calls out all four. And on V2X data, there are nineteen kinds of misbehaving cars, like ghosts reporting fake positions.",
             "Our model calls out all four. And on V to X data, there are nineteen kinds of misbehaving cars, like ghosts reporting fake positions."),
        ],
    ),
    dict(
        id="math_kan",
        chapter=4,
        title="Curves instead of weights",
        sentences=[
            "Now, the maths. Don't worry, it's friendlier than it looks.",
            "A normal neural network links two neurons with a single number: a weight.",
            ("ChebyKAN swaps that number for a whole curve the network can bend.",
             "Chebby Kan swaps that number for a whole curve, that the network can bend."),
            ("The curve is built from Chebyshev polynomials. Start with 1 and x. Each new one is 2x times the last, minus the one before.",
             "The curve is built from Chebyshev polynomials. Start with one, and x. Each new one is two x times the last, minus the one before."),
            "Mix five of them with five learnable coefficients, add a base weight, and you get six numbers per connection.",
            "Across 7,296 connections, that's 44,164 numbers. And every single one will be encrypted.",
        ],
    ),
    dict(
        id="math_ckks",
        chapter=4,
        title="Locked boxes that still add up",
        sentences=[
            ("CKKS packs numbers into slots. One ciphertext is like a train with 4,096 seats.",
             "C K K S packs numbers into slots. One ciphertext is like a train, with 4,096 seats."),
            "Each weight is scaled by 2 to the 40, and our 44,164 weights fill 11 trains, with a few empty seats at the end.",
            "The server runs function F: multiply each locked update by its data count, add them up, and divide by the total.",
            "It only multiplies by plain numbers, so it never needs an expensive ciphertext multiplication.",
            "And because decryption is linear, unlocking the sum gives exactly the same average as with no encryption at all.",
            "To catch poisoned cars, the server also measures how far each locked update sits from the group, and trusts the far ones less.",
        ],
    ),
    dict(
        id="results",
        chapter=5,
        title="Did encryption hurt?",
        sentences=[
            ("So, the big question. Does all this encryption hurt accuracy?",
             "So, the big question. Does all this encryption hurt accuracy?", 1.2),
            ("Nope. On Car-Hacking, encrypted training scores 99.77 percent, plain training 99.81. That gap is smaller than the noise between runs.",
             "Nope. On Car Hacking, encrypted training scores 99.77 percent, plain training 99.81. That gap is smaller than the noise between runs."),
            "The encryption error is below one in a million, and the server never decrypted a single car's update.",
            "The price? Each update grows to about 3.5 megabytes, and squeezing that into car radio links is a puzzle we're still solving.",
        ],
    ),
    dict(
        id="status",
        chapter=6,
        title="Where we are, and what's next",
        sentences=[
            "So where are we today? The encrypted pipeline works, function F is proven, and packing cut bandwidth by almost 30 percent.",
            "Next up: multi-key encryption. Right now the cars share one key.",
            "Soon each car holds just one piece, and only all the pieces together can unlock the result. No single party can peek.",
            ("To get there, we're moving from TenSEAL to OpenFHE.",
             "To get there, we're moving from Ten Seal, to Open F H E."),
            ("Then, hardware: an NXP automotive board and a Raspberry Pi, with fast NEON code, so the guard runs inside a real car.",
             "Then, hardware. An N X P automotive board, and a Raspberry Pie, with fast Neon code, so the guard runs inside a real car."),
        ],
    ),
    dict(
        id="summary",
        chapter=7,
        title="Wrap-up",
        sentences=[
            "So: Car 7 learns from the whole fleet, the server computes blind, and privacy costs no accuracy.",
            "Thanks for riding along!",
        ],
    ),
]


def caption(s):
    return s[0] if isinstance(s, tuple) else s


def spoken(s):
    return s[1] if isinstance(s, tuple) else s


def pause_after(s):
    return s[2] if isinstance(s, tuple) and len(s) > 2 else 0.0


if __name__ == "__main__":
    total = 0
    for sc in SCENES:
        n = sum(len(spoken(s).split()) for s in sc["sentences"])
        total += n
        print(f"{sc['id']:<10} {len(sc['sentences']):>2} sentences {n:>4} words")
    print(f"total words: {total}")
