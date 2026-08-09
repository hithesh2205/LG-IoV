"""Build the standalone note: why an authenticated encrypted channel is needed
alongside FHE, and whether an integrity-only scheme would suffice.

    python scripts/build_channel_rationale_pdf.py "<output_dir>"
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, NextPageTemplate, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

INK = colors.HexColor("#1a1a2e")
BLUE = colors.HexColor("#2d6cdf")
GREEN = colors.HexColor("#1e9e6a")
RED = colors.HexColor("#d64545")
AMBER = colors.HexColor("#d98324")
GREY = colors.HexColor("#5a6472")
LIGHT = colors.HexColor("#eef2f8")
RULE = colors.HexColor("#c8d2e0")

ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("t", parent=ss["Title"], fontSize=22, leading=27,
                            textColor=INK, spaceAfter=8),
    "sub": ParagraphStyle("s", parent=ss["Normal"], fontSize=12, leading=17,
                          alignment=TA_CENTER, textColor=GREY),
    "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontSize=16, leading=21,
                         textColor=INK, spaceBefore=15, spaceAfter=8),
    "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12.5, leading=16,
                         textColor=BLUE, spaceBefore=12, spaceAfter=5),
    "body": ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.8, leading=14.4,
                           alignment=TA_JUSTIFY, textColor=INK, spaceAfter=6),
    "bullet": ParagraphStyle("bu", parent=ss["BodyText"], fontSize=9.8, leading=14,
                             leftIndent=14, bulletIndent=4, spaceAfter=3, textColor=INK),
    "q": ParagraphStyle("q", parent=ss["BodyText"], fontSize=10.5, leading=15,
                        textColor=INK, backColor=LIGHT, borderPadding=9,
                        borderWidth=0.8, borderColor=BLUE, spaceBefore=6,
                        spaceAfter=10, fontName="Helvetica-Oblique"),
    "ok": ParagraphStyle("ok", parent=ss["BodyText"], fontSize=9.4, leading=13.4,
                         textColor=INK, backColor=colors.HexColor("#eefaf4"),
                         borderPadding=8, borderWidth=0.7, borderColor=GREEN,
                         spaceBefore=5, spaceAfter=9),
    "warn": ParagraphStyle("w", parent=ss["BodyText"], fontSize=9.4, leading=13.4,
                           textColor=INK, backColor=colors.HexColor("#fdeeee"),
                           borderPadding=8, borderWidth=0.7, borderColor=RED,
                           spaceBefore=5, spaceAfter=9),
    "note": ParagraphStyle("n", parent=ss["BodyText"], fontSize=9.4, leading=13.4,
                           textColor=INK, backColor=colors.HexColor("#fff8ec"),
                           borderPadding=8, borderWidth=0.7, borderColor=AMBER,
                           spaceBefore=5, spaceAfter=9),
    "code": ParagraphStyle("c", parent=ss["Code"], fontSize=8.4, leading=11.6,
                           textColor=INK, backColor=LIGHT, borderPadding=7,
                           leftIndent=6, spaceBefore=4, spaceAfter=8),
}


def P(t):
    return Paragraph(t, S["body"])


def B(t):
    return Paragraph(t, S["bullet"], bulletText="•")


def H(t, lvl=1):
    return Paragraph(t, S[f"h{lvl}"])


def box(t, style):
    return Paragraph(t, S[style])


def tbl(data, widths, fs=8.4, header=True):
    # Plain strings in a reportlab cell do NOT wrap - they clip at the column
    # edge, silently truncating text mid-word. Wrap every cell in a Paragraph.
    cell = ParagraphStyle("cell", parent=ss["BodyText"], fontSize=fs,
                          leading=fs + 2.6, textColor=INK,
                          spaceAfter=0, spaceBefore=0)
    cell_h = ParagraphStyle("cellh", parent=cell, fontName="Helvetica-Bold")
    data = [[Paragraph(c.replace("\n", "<br/>"),
                       cell_h if (header and r == 0) else cell)
             if isinstance(c, str) else c
             for c in row]
            for r, row in enumerate(data)]

    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    st = [("FONTSIZE", (0, 0), (-1, -1), fs),
          ("LEADING", (0, 0), (-1, -1), fs + 3.2),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TEXTCOLOR", (0, 0), (-1, -1), INK),
          ("GRID", (0, 0), (-1, -1), 0.4, RULE),
          ("TOPPADDING", (0, 0), (-1, -1), 4),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
          ("LEFTPADDING", (0, 0), (-1, -1), 5),
          ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), LIGHT)]
    t.setStyle(TableStyle(st))
    return t


TITLE = "Why FHE Still Needs an Authenticated Encrypted Channel"


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(2 * cm, A4[1] - 1.25 * cm, TITLE)
    canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.25 * cm, "LGSI IoV - design note")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(2 * cm, A4[1] - 1.45 * cm, A4[0] - 2 * cm, A4[1] - 1.45 * cm)
    canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.drawCentredString(A4[0] / 2, 1.05 * cm, f"page {doc.page}")
    canvas.restoreState()


def content(F):
    # ── title ────────────────────────────────────────────────────────────
    F += [
        Spacer(1, 2.4 * cm),
        box("Why FHE Still Needs an<br/>Authenticated Encrypted Channel", "title"),
        Spacer(1, 0.5 * cm),
        box("And whether an integrity-only scheme would be enough", "sub"),
        Spacer(1, 1.5 * cm),
    ]
    F.append(tbl([
        ["Project", "Privacy-Preserving Collaborative IDS for IoV (LGSI)"],
        ["Question from", "Design review, Month 5"],
        ["Date", date.today().isoformat()],
        ["Verdict", "Both layers are required. The integrity-only proposal is "
                    "half right, and it exposes a real gap in the current design."],
    ], [3.6 * cm, 11.4 * cm], header=False, fs=9.4))
    F += [Spacer(1, 1.2 * cm)]

    F.append(box(
        "“Anyhow the encrypted data is only going to the server side, so why do we need "
        "an AES channel? And if integrity is the problem, can we not just use one "
        "integrity / authenticity verification scheme?”", "q"))
    F.append(NextPageTemplate("body"))
    F.append(PageBreak())

    # ── 1 ────────────────────────────────────────────────────────────────
    F.append(H("1. Short answer", 1))
    F.append(P(
        "Both layers are needed, but <b>not for the reason usually given</b>. The second half of "
        "the question is the sharper one, and it is largely correct: the missing property really is "
        "authentication and integrity, and a signature scheme supplies most of it. Plain "
        "confidentiality-on-the-wire is <i>not</i> what justifies the channel — FHE already "
        "hides the payload from anyone listening."))
    F.append(P("Two things still force an encrypted channel rather than a signature alone:"))
    F.append(B("<b>The masked key shares must not be public.</b> FheFL has each vehicle upload "
               "<i>ss</i><sub>u</sub> alongside its ciphertext. Anyone who collects all of them can "
               "reconstruct the aggregate decryption key. Broadcasting those in the clear hands "
               "every passive listener the server's capability."))
    F.append(B("<b>A bare signature is a tracking beacon.</b> A signature identifies its signer to "
               "anyone with a radio. In a vehicular network that converts the protocol into a "
               "location-tracking oracle — which attacks the very privacy the project exists "
               "to protect."))
    F.append(box(
        "<b>And the question surfaces a genuine defect.</b> AES-GCM authenticates with a "
        "<i>symmetric</i> tag, so the server — which holds the same key — could forge a "
        "vehicle's update. The system therefore cannot prove which vehicle submitted a poisoned "
        "model. That is a real gap, and the fix is exactly the mechanism proposed in the question: "
        "add a per-message signature. See section 7.", "note"))

    # ── 2 ────────────────────────────────────────────────────────────────
    F.append(H("2. “Security” is not one property", 1))
    F.append(P(
        "Most confusion here comes from treating security as a single thing that either is or is "
        "not present. It decomposes into at least five independent properties, and a given "
        "primitive supplies some and not others."))
    F.append(tbl([
        ["Property", "Plain meaning", "Who is the attacker?"],
        ["Confidentiality", "Nobody can read the content", "Eavesdropper, or the recipient itself"],
        ["Authentication", "The message really came from who it claims", "Impersonator"],
        ["Integrity", "The message was not modified in flight", "On-path attacker"],
        ["Freshness", "This is not an old message resent", "Replay attacker"],
        ["Non-repudiation", "The sender cannot later deny sending it, and a third\n"
                            "party can verify who did", "A lying sender, or a lying server"],
    ], [3.0 * cm, 6.6 * cm, 5.4 * cm]))
    F.append(box(
        "<b>The decisive asymmetry.</b> Transport encryption protects data <i>in transit</i>. It "
        "can never protect data <i>from the recipient</i>, because the recipient holds the key. "
        "The server is the one party AES structurally cannot defend you against — and the "
        "server is precisely the adversary this project cares about. That is the entire reason FHE "
        "is in the design at all.", "ok"))

    # ── 3 ────────────────────────────────────────────────────────────────
    F.append(H("3. What each layer actually provides", 1))
    F.append(tbl([
        ["Threat", "Adversary", "AES-GCM channel", "FHE"],
        ["Eavesdropping on the radio", "network", "yes", "yes"],
        ["Server reads your individual update", "server", "NO - it holds the key", "YES"],
        ["Impersonating a vehicle", "network", "yes", "no"],
        ["Modifying a ciphertext in flight", "network", "yes", "NO - malleable by design"],
        ["Replaying an old update", "network", "yes, with round binding", "no"],
        ["Registering 500 fake vehicles (Sybil)", "attacker", "yes, via identity keys", "no"],
        ["Proving who sent a poisoned update", "server or vehicle", "NO - symmetric tag", "no"],
    ], [5.3 * cm, 2.4 * cm, 4.4 * cm, 3.0 * cm]))
    F.append(P(
        "The two <b>NO</b>s in the FHE column are the ones that matter, and the reason is section 4."))

    # ── 4 ────────────────────────────────────────────────────────────────
    F.append(H("4. Why FHE cannot supply integrity - malleability", 1))
    F.append(P(
        "<b>Malleability</b> means an attacker who cannot read a ciphertext can still change it into "
        "a ciphertext of a <i>related, predictable</i> plaintext. For ordinary encryption this is a "
        "serious flaw, and modern schemes are built to prevent it."))
    F.append(P(
        "Homomorphic encryption <b>gives malleability up deliberately.</b> That is the whole point: "
        "the server must be able to take Enc(a) and Enc(b) and produce Enc(a+b) without the key. "
        "But the same property is available to anyone on the path:"))
    F.append(Paragraph(
        "attacker intercepts   Enc(f)<br/>"
        "attacker computes     Enc(f) + Enc(bias)  =  Enc(f + bias)<br/>"
        "server receives and aggregates a poisoned update it cannot detect",
        S["code"]))
    F.append(P(
        "The server cannot notice, because the modified ciphertext is a perfectly valid ciphertext. "
        "No property of CKKS prevents this — CKKS is at best IND-CPA, and is explicitly not "
        "IND-CCA. <b>Integrity has to come from somewhere else.</b> The GCM authentication tag "
        "supplies it: change one bit of the frame and verification fails."))
    F.append(box(
        "This is the cleanest refutation of “FHE is enough”. It is not that FHE happens "
        "to lack integrity; it is that FHE <b>must</b> lack it in order to be useful. The property "
        "that makes homomorphic aggregation possible is the same property an attacker uses to "
        "tamper with updates.", "warn"))

    # ── 5 ────────────────────────────────────────────────────────────────
    F.append(PageBreak())
    F.append(H("5. The proposal: integrity/authenticity only", 1))
    F.append(P(
        "The proposal is to drop the encrypted channel and instead attach an authenticity tag to "
        "each FHE ciphertext — for example an Ed25519 signature over "
        "<font face='Courier'>(round_id || ciphertext)</font>. Since FHE already hides the payload, "
        "why encrypt it a second time?"))

    F.append(H("5.1 What the proposal gets right", 2))
    F.append(B("The FHE ciphertext genuinely is confidential against a passive listener. Wrapping "
               "it in AES adds <b>no</b> extra confidentiality for that payload."))
    F.append(B("A signature over the ciphertext plus the round number delivers authentication, "
               "integrity and freshness — the three properties FHE lacks."))
    F.append(B("A signature is in one way <b>stronger</b> than AES-GCM's tag: it is asymmetric, so "
               "it also gives non-repudiation, which a shared-key tag cannot."))
    F.append(P("So the reasoning is sound. It fails on two things that are specific to this system."))

    F.append(H("5.2 Objection 1 - the masked key shares must stay secret", 2))
    F.append(P(
        "In FheFL each vehicle uploads two things per round: the ciphertext "
        "<i>[f<sup>u</sup>]</i>, and its <b>masked key share</b> "
        "<i>ss<sub>u</sub> = s<sub>u</sub> + Sum<sub>j!=u</sub> s<sub>u,j</sub></i>. The server sums "
        "those to recover the key that decrypts the aggregate:"))
    F.append(Paragraph("Sum<sub>u</sub> ss<sub>u</sub>  =  Sum<sub>u</sub> s<sub>u</sub>  =  s",
                       S["code"]))
    F.append(P(
        "The masking makes an individual <i>ss<sub>u</sub></i> useless on its own — but the "
        "<b>set</b> of them is exactly the server's decryption capability. If they travel in the "
        "clear, any passive listener that hears the whole round reconstructs <i>s</i> and becomes a "
        "second aggregating party."))
    F.append(box(
        "<b>Why that breaks the security argument.</b> FheFL's Theorem 1 states that compromising "
        "one honest vehicle requires colluding with U-1 vehicles. That count assumes the server is "
        "the <i>only</i> party holding <i>s</i>. Publishing the shares silently adds every "
        "eavesdropper to the set of parties holding <i>s</i> — so an attacker who listens to "
        "the radio and additionally corrupts U-2 vehicles breaks the remaining one, without ever "
        "touching the server. The whole collusion analysis has to be redone, and it comes out "
        "weaker.", "warn"))
    F.append(P(
        "A signature does not fix this, because a signature authenticates a message without hiding "
        "it. These values need <b>confidentiality</b>, and confidentiality against the network is "
        "exactly what an encrypted channel provides."))

    F.append(H("5.3 Objection 2 - a bare signature is a tracking beacon", 2))
    F.append(P(
        "A signature identifies its signer. That is its purpose. But it means anyone with a radio "
        "receiver can read, from an unencrypted frame:"))
    F.append(B("<b>which</b> vehicle transmitted (from the key or certificate),"))
    F.append(B("<b>when</b> it transmitted,"))
    F.append(B("<b>roughly where</b> it was, from signal strength and direction."))
    F.append(P(
        "Log that over a city and you have a movement history per vehicle — built out of the "
        "privacy-preserving protocol itself. This attacks asset A4 (fleet membership and identity) "
        "in the threat model and makes threat P7 (traffic analysis) far worse than it already is."))
    F.append(P(
        "With an ECDH-derived AES session the identity sits <i>inside</i> the encrypted envelope; a "
        "listener sees only opaque bytes of roughly constant size. This is not a hypothetical "
        "concern in vehicular networking — it is why IEEE 1609.2 defines rotating pseudonym "
        "certificates. Location privacy is a first-class requirement in V2X, and a plaintext "
        "signature is directly at odds with it."))

    F.append(H("5.4 Objection 3 - defence in depth", 2))
    F.append(P(
        "CKKS is young and its security assumptions have moved recently: Li and Micciancio "
        "(Eurocrypt 2021) showed CKKS is not IND-CPA<sup>D</sup>, meaning released decryption "
        "results leak key information. Parameters get revised; attacks improve. If the FHE layer is "
        "the <i>only</i> thing protecting the payload on the wire, any weakening of it is total. "
        "With a transport layer underneath, an FHE weakness still leaves an attacker facing "
        "AES-256."))

    F.append(H("5.5 And it would not be accepted anyway", 2))
    F.append(P(
        "Automotive V2X deployment is governed by IEEE 1609.2 and the ETSI ITS security standards, "
        "which mandate authenticated and, for many message classes, encrypted channels. “We use "
        "homomorphic encryption instead” is not an available answer at certification. The "
        "channel is going to be there regardless of what the research prototype does."))

    # ── 6 ────────────────────────────────────────────────────────────────
    F.append(PageBreak())
    F.append(H("6. Then why AES-GCM specifically?", 1))
    F.append(P(
        "Given that both confidentiality and integrity are needed on the wire, the question becomes "
        "whether to use two primitives (encrypt, then sign) or one that does both. "
        "<b>AEAD</b> — Authenticated Encryption with Associated Data — is the standard "
        "answer, and AES-256-GCM is the standard AEAD."))
    F.append(tbl([
        ["Option", "Confidentiality", "Integrity", "Cost", "Verdict"],
        ["Signature only", "no", "yes", "~50 us/msg", "Fails objections 1 and 2"],
        ["Encrypt-then-MAC", "yes", "yes", "two primitives, easy to get wrong",
         "Works, but AEAD exists precisely to remove the footguns"],
        ["AES-256-GCM (AEAD)", "yes", "yes", "hardware-accelerated, GB/s",
         "Chosen - one primitive, both properties"],
    ], [3.4 * cm, 2.2 * cm, 1.7 * cm, 3.6 * cm, 4.2 * cm]))
    F.append(P(
        "There is also no efficiency argument for dropping it. AES-GCM runs at gigabytes per second "
        "with AES-NI hardware support. Against a measured 18.0 ms for a single encrypted "
        "squared-distance operation, and roughly 3.6 MB of ciphertext per vehicle per round, the "
        "channel is free in comparison. Removing it saves nothing measurable and costs four "
        "security properties."))
    F.append(box(
        "<b>The associated-data field is the point of GCM here.</b> AEAD lets you bind extra "
        "context to the frame without encrypting it. Putting the round number in that field is what "
        "makes replay detection work: a captured round-3 frame replayed in round 9 fails "
        "verification because the bound round number no longer matches. This is currently "
        "<b>not wired up</b> — see section 8.", "note"))

    # ── 7 ────────────────────────────────────────────────────────────────
    F.append(H("7. The real gap this question exposes", 1))
    F.append(P(
        "The proposal is right that a signature offers something AES-GCM does not, and the current "
        "design does not have it."))
    F.append(P(
        "GCM's authentication tag is a <b>symmetric</b> MAC: vehicle and server share one key. So "
        "the server can compute any tag the vehicle could. It follows that:"))
    F.append(B("the server cannot <b>prove to a third party</b> that a given update came from a "
               "particular vehicle — it could have produced that frame itself;"))
    F.append(B("a vehicle caught poisoning the model can plausibly deny it;"))
    F.append(B("the Byzantine-robustness machinery can down-weight a bad update, but the system has "
               "no basis to <b>attribute</b> it, and therefore no basis to evict or revoke."))
    F.append(P(
        "In the current implementation Ed25519 is used only during the handshake, to authenticate "
        "the key exchange. It is not applied per message. So the moment the session is established, "
        "everything after it rests on a shared symmetric key."))
    F.append(box(
        "<b>Recommendation, arising directly from this question.</b> Add a per-message Ed25519 "
        "signature over <font face='Courier'>(round_id || client_id || ciphertext_digest)</font>, "
        "carried <i>inside</i> the AES-GCM envelope. Inside, not outside — that keeps "
        "objection 2 closed, because the identity stays encrypted while still being verifiable by "
        "the server. This is roughly a day of work and it converts Byzantine detection into "
        "Byzantine <b>accountability</b>: the server can then prove which vehicle sent which "
        "update, which is what revocation and eviction require.", "ok"))

    # ── 8 ────────────────────────────────────────────────────────────────
    F.append(H("8. What should change in the code", 1))
    F.append(tbl([
        ["#", "Change", "Effort", "Closes"],
        ["1", "Bind the round number into the AEAD associated data:\n"
              "channel.encrypt(payload, aad=round_id.to_bytes(8,'big'))",
         "1 hour", "Replay (threat S5). Already tracked as P0.2"],
        ["2", "Carry ss_u inside the encrypted envelope, never alongside it",
         "already correct - keep it that way", "Objection 1"],
        ["3", "Add a per-message Ed25519 signature inside the envelope",
         "1 day", "Non-repudiation; enables eviction and revocation"],
        ["4", "Bind the vehicle's identity key to hardware attestation at enrolment",
         "depends on the embedded track", "Sybil (threat S4)"],
    ], [0.8 * cm, 7.4 * cm, 3.0 * cm, 3.8 * cm]))

    # ── 9 ────────────────────────────────────────────────────────────────
    F.append(H("9. Summary", 1))
    F.append(tbl([
        ["Claim", "Verdict"],
        ["“FHE already encrypts it, so the channel is redundant”",
         "False. FHE protects the update from the SERVER; the channel protects it from the NETWORK. "
         "Different adversaries. AES can never protect you from the recipient."],
        ["“Integrity is the missing property”",
         "Correct, and it is the core of the issue. FHE is malleable by construction, so it cannot "
         "supply integrity - and that malleability is exactly what makes homomorphic aggregation work."],
        ["“So a signature scheme alone would do”",
         "No. The masked key shares need confidentiality, not just authenticity, and a plaintext "
         "signature turns the protocol into a vehicle-tracking oracle."],
        ["“Then the channel should be AEAD”",
         "Yes. AES-256-GCM gives confidentiality and integrity in one primitive, is effectively free "
         "next to CKKS, and its associated-data field is what makes replay protection possible."],
        ["“But a signature adds something AES-GCM cannot”",
         "Correct, and this is the useful part. GCM's tag is symmetric, so the server could forge a "
         "vehicle's update. Per-message signatures are needed for accountability, and are missing today."],
    ], [5.6 * cm, 9.4 * cm], fs=8.4))
    F.append(box(
        "<b>Net position.</b> Neither layer is redundant, and the two are not alternatives: FHE "
        "answers “can the server read my data”, the channel answers “is this really "
        "my data, unmodified, and fresh”. Layering them is ordinary practice - HTTPS does not "
        "make end-to-end encryption pointless in a messaging app, for exactly this reason. Removing "
        "FHE would reduce the project to the FedIoV baseline; removing the channel would not "
        "simplify it, only break it.", "ok"))

    F.append(H("Related documents", 1))
    F.append(B("<font face='Courier'>08_threat_model.md</font> — threats N1-N3 (network), "
               "S4 (Sybil), S5 (replay), P7 (traffic analysis)"))
    F.append(B("<font face='Courier'>09_security_specification.md</font> §6 — the channel "
               "construction; §5 — FheFL key sharing"))
    F.append(B("<font face='Courier'>04_decision_audit.md</font> §12 — why removing the "
               "channel in Month 4 was a regression"))
    F.append(B("<font face='Courier'>12_next_steps.md</font> — P0.2 (round binding), "
               "P0.3 (noise flooding)"))


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "13_why_AES_with_FHE.pdf"

    doc = BaseDocTemplate(
        str(out), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="Why FHE Still Needs an Authenticated Encrypted Channel",
        author="LGSI IoV Project",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="n")
    doc.addPageTemplates([
        PageTemplate(id="title", frames=[frame]),
        PageTemplate(id="body", frames=[frame], onPage=on_page),
    ])
    F = []
    content(F)
    doc.build(F)
    print(f"wrote {out}  ({out.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
