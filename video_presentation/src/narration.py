"""Narration script for the LGSI IoV project video — the single source of truth.

Each scene is a list of sentences. A sentence is either a plain string (shown as
the caption AND spoken) or a ``(caption, say)`` pair when the text-to-speech
voice needs a phonetic spelling (e.g. "CKKS" -> "C K K S").

Visual cues in ``scenes.py`` refer to sentences by their index inside a scene,
so if you add or remove a sentence, check the matching scene builder.

Facts are taken from:
  README.md, 5th Month Progress/Documentation/11_current_status.md,
  12_next_steps.md, 08_threat_model.md, 17_multikey_scheme_decision.md,
  Dataset/README.md, after_F_function/reports/final_report.md and the
  08.10.26 Weekly_Meet Final draft deck.
"""

# chapter labels shown in the header bar (scene "chapter" indexes into this)
CHAPTERS = ["Problem", "Approach", "Data", "Attacks", "Math", "Results", "Status", "Summary"]

SCENES = [
    dict(
        id="title",
        chapter=None,
        title="",
        sentences=[
            ("Privacy-preserving collaborative intrusion detection for the Internet of Vehicles.",
             "Privacy preserving, collaborative intrusion detection, for the Internet of Vehicles."),
            ("Our LG Soft India project, in under six minutes.",
             "Our L G Soft India project, in under six minutes."),
        ],
    ),
    dict(
        id="problem",
        chapter=0,
        title="1 · The real-world problem",
        sentences=[
            "A modern car is a network on wheels: dozens of control units talk over the CAN bus.",
            "The CAN bus has no authentication, so any node can send any message.",
            ("In 2015, researchers hacked a Jeep Cherokee remotely, and 1.4 million vehicles were recalled.",
             "In twenty fifteen, researchers hacked a Jeep Cherokee remotely, and 1.4 million vehicles were recalled."),
            "Intrusion detection can catch such attacks, but it needs data from many vehicles.",
            "Federated learning keeps private driving data in the car and shares only model updates.",
            "But even updates can be inverted to reveal the data. That is the gap we close.",
        ],
    ),
    dict(
        id="approach",
        chapter=1,
        title="2 · How we do it",
        sentences=[
            ("Each vehicle trains a small ChebyKAN detector on its own CAN traffic.",
             "Each vehicle trains a small Chebby Kan detector on its own can traffic."),
            ("It encrypts its update with CKKS homomorphic encryption before anything leaves the car.",
             "It encrypts its update with C K K S homomorphic encryption, before anything leaves the car."),
            "The roadside unit and server add the encrypted updates without decrypting them. They hold no secret key.",
            "They also score each update's distance from consensus, and down-weight outliers to resist poisoning.",
            "Only the total is decrypted, and the new global model returns to the fleet.",
        ],
    ),
    dict(
        id="data",
        chapter=2,
        title="3 · Datasets and preprocessing",
        sentences=[
            "We use four public datasets, 8.6 gigabytes in total.",
            ("Car-Hacking and CAN-VTC hold in-vehicle traffic, VeReMi holds V2X beacons, and CICIDS-2017 is a sanity check.",
             "Car Hacking and can V T C hold in-vehicle traffic, Vereh-mee holds V to X beacons, and C I C I D S 2017 is a sanity check."),
            "Each CAN message keeps its own ground-truth label.",
            ("A 64-message window slides 16 at a time, and each window becomes 46 features: byte statistics, ID frequencies and entropy.",
             "A 64 message window slides 16 at a time, and each window becomes 46 features: byte statistics, I D frequencies, and entropy."),
            "Whole blocks go to train, validation or test, 70, 15, 15, so windows never leak across the split.",
            ("Features are clipped, standardised, and split across ten vehicles with a Dirichlet split, alpha 0.3.",
             "Features are clipped, standardised, and split across ten vehicles with a Deerish-lay split, alpha 0.3."),
        ],
    ),
    dict(
        id="attacks",
        chapter=3,
        title="4 · Attacks we detect and defend against",
        sentences=[
            "The detector learns four in-vehicle attacks.",
            ("Denial of service floods the bus with top-priority ID zero; fuzzing injects random IDs and payloads.",
             "Denial of service floods the bus with top priority I D zero. Fuzzing injects random I Ds and payloads."),
            ("RPM and gear spoofing inject fake engine-speed and gear readings.",
             "R P M and gear spoofing inject fake engine speed and gear readings."),
            ("VeReMi adds nineteen V2X misbehaviours, like false positions and replayed beacons.",
             "Vereh-mee adds nineteen V to X misbehaviours, like false positions and replayed beacons."),
            "We also protect the learning itself: encryption blocks gradient inversion, and robust weighting limits poisoning.",
        ],
    ),
    dict(
        id="math_kan",
        chapter=4,
        title="5 · The mathematics — ChebyKAN weights as polynomials",
        sentences=[
            "Now the maths. A normal network multiplies each input by one weight.",
            ("ChebyKAN replaces that weight with a learnable curve built from Chebyshev polynomials.",
             "Chebby Kan replaces that weight with a learnable curve, built from Chebyshev polynomials."),
            ("T0 is 1, T1 is x, and each next one is 2x times the previous, minus the one before.",
             "T zero is one. T one is x. And each next one is two x times the previous, minus the one before."),
            ("Each edge computes φ(x): a base weight times x, plus five coefficients times T0 to T4 of tanh x. Six parameters per edge.",
             "Each edge computes fie of x: a base weight times x, plus five coefficients times T zero to T four of tan h x. Six parameters per edge."),
            "With 46 inputs, two hidden layers of 64, and 4 classes, that is 7,296 edges,",
            "giving 44,164 parameters in total, broken down here.",
            ("Because it is all polynomials, it suits CKKS arithmetic.",
             "Because it is all polynomials, it suits C K K S arithmetic."),
        ],
    ),
    dict(
        id="math_ckks",
        chapter=4,
        title="5 · The mathematics — CKKS packing and the function F",
        sentences=[
            ("CKKS encrypts real numbers. With N = 8,192, one ciphertext holds 4,096 values in parallel slots.",
             "C K K S encrypts real numbers. With N equals 8,192, one ciphertext holds 4,096 values in parallel slots."),
            "Each weight is scaled by 2 to the 40, and 44,164 weights fill 11 ciphertexts, the last one zero-padded.",
            "The server's function F multiplies each encrypted update by its sample count, adds them, and scales by one over the total.",
            "Only plaintext scalars touch the ciphertexts, so the multiplicative depth is zero.",
            "Decryption is linear, so decrypting the result gives exactly the weighted average of the plain updates.",
            "For robustness, each update's squared distance to the global model costs one ciphertext multiplication, and becomes a trust weight.",
            "Vehicles decrypt and re-encrypt fresh every round, so noise never builds up and no bootstrapping is needed.",
        ],
    ),
    dict(
        id="results",
        chapter=5,
        title="6 · Results",
        sentences=[
            "Does encryption cost accuracy? No.",
            ("On Car-Hacking, our main benchmark, encrypted training scores 99.77 percent versus 99.81 in plaintext, over three seeds.",
             "On Car Hacking, our main benchmark, encrypted training scores 99.77 percent, versus 99.81 in plaintext, over three seeds."),
            ("On CICIDS, 95.55 versus 95.42. Every gap is within seed noise.",
             "On C I C I D S, 95.55 versus 95.42. Every gap is within seed noise."),
            "Aggregation error stays below one in a million, and no individual update was ever decrypted.",
            "The price is bandwidth: about 3.5 megabytes per update, twenty-one times plaintext.",
            ("Honest limits: CAN-VTC is too easy, and VeReMi stays near chance until re-acquired with sender IDs.",
             "Honest limits. Can V T C is too easy, and Vereh-mee stays near chance until re-acquired with sender I Ds."),
        ],
    ),
    dict(
        id="status",
        chapter=6,
        title="7 · Where we stand and what comes next",
        sentences=[
            ("Done so far: the real CKKS pipeline, function F with its proof, encrypted robust weighting, packing, and a validated NTT.",
             "Done so far: the real C K K S pipeline, function F with its proof, encrypted robust weighting, packing, and a validated N T T."),
            ("Next, multi-key encryption. Today the fleet shares one key, because TenSEAL allows nothing more.",
             "Next, multi-key encryption. Today the fleet shares one key, because Ten Seal allows nothing more."),
            ("After comparing centralised and decentralised multi-key CKKS, we are moving to OpenFHE, so no single party can decrypt an update.",
             "After comparing centralised and decentralised multi-key C K K S, we are moving to Open F H E, so no single party can decrypt an update."),
            ("Then hardware: an NXP S32G board and a Raspberry Pi 5, a NEON-accelerated NTT, and an on-vehicle IDS.",
             "Then hardware: an N X P, S 32 G board, and a Raspberry Pie 5, a Neon accelerated N T T, and an on-vehicle I D S."),
            ("Plus V2X bandwidth, patient low-magnitude attackers, and differential privacy.",
             "Plus V to X bandwidth, patient low-magnitude attackers, and differential privacy."),
        ],
    ),
    dict(
        id="summary",
        chapter=7,
        title="8 · In short",
        sentences=[
            "In short: vehicles learn together, the server computes blind, and privacy costs no accuracy.",
            "Thank you for watching.",
        ],
    ),
]


def caption(s):
    return s[0] if isinstance(s, tuple) else s


def spoken(s):
    return s[1] if isinstance(s, tuple) else s


if __name__ == "__main__":
    total = 0
    for sc in SCENES:
        n = sum(len(spoken(s).split()) for s in sc["sentences"])
        total += n
        print(f"{sc['id']:<10} {len(sc['sentences']):>2} sentences {n:>4} words")
    print(f"total words: {total}  (~{total / 160:.1f} min of speech at 160 wpm)")
