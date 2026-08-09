"""SecureChannel — ECDH-P256 + AES-256-GCM + Ed25519 mutual auth.

Implements the paper's ``SecureChannel(Server, D_i)`` primitive (§3.1,
eq. 2). Each side has a *long-term* Ed25519 identity key. The handshake:

1.  Each party generates a fresh ephemeral ECDH-P256 keypair.
2.  Each party signs ``(its_ephemeral_pub || peer_identity_pub)`` with its
    long-term Ed25519 key and exchanges (ephemeral_pub, signature).
3.  Each party verifies the peer's signature against the peer's known
    identity public key (mutual auth).
4.  Shared secret = ``ECDH(my_eph_priv, peer_eph_pub)``.
5.  ``key = HKDF-SHA256(shared, salt=transcript, info=b"FedIoV/v1")`` →
    32-byte AES-256 key.

Each ``SecureChannel.encrypt(plaintext, aad)`` uses a fresh 12-byte
random nonce concatenated to the ciphertext; ``decrypt`` reverses it.
This is sufficient for the simulated federated workflow the paper
describes; in a real DSRC/C-V2X deployment the channel would still
live inside TLS 1.3.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


_HKDF_INFO = b"FedIoV/v1/aes-256-gcm"
_AES_KEY_LEN = 32
_NONCE_LEN = 12


# ─── Long-term identity ──────────────────────────────────────────────────


@dataclass
class IdentityKey:
    """Long-term Ed25519 identity for one party (server or client)."""

    name: str
    private: ed25519.Ed25519PrivateKey
    public: ed25519.Ed25519PublicKey

    @classmethod
    def generate(cls, name: str) -> "IdentityKey":
        sk = ed25519.Ed25519PrivateKey.generate()
        return cls(name=name, private=sk, public=sk.public_key())

    def public_bytes(self) -> bytes:
        return self.public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def fingerprint(self) -> str:
        import hashlib
        return hashlib.sha256(self.public_bytes()).hexdigest()[:16]


# ─── SecureChannel ───────────────────────────────────────────────────────


class HandshakeError(Exception):
    """Raised when peer signature verification fails."""


@dataclass
class SecureChannel:
    """An authenticated, encrypted channel between two parties.

    Use :func:`handshake` to construct symmetrically. Each side calls
    :meth:`encrypt` / :meth:`decrypt` to talk to the other.
    """

    local_name: str
    peer_name: str
    aes_key: bytes      # 32 bytes
    transcript_digest: bytes   # for logging / pinning

    def __post_init__(self) -> None:
        if len(self.aes_key) != _AES_KEY_LEN:
            raise ValueError(f"aes_key must be {_AES_KEY_LEN} bytes")
        self._aead = AESGCM(self.aes_key)

    # ── Wire format: nonce (12B) || ciphertext-with-tag ────────────────
    def encrypt(self, plaintext: bytes, aad: Optional[bytes] = None) -> bytes:
        nonce = os.urandom(_NONCE_LEN)
        ct = self._aead.encrypt(nonce, plaintext, aad)
        return nonce + ct

    def decrypt(self, wire: bytes, aad: Optional[bytes] = None) -> bytes:
        if len(wire) < _NONCE_LEN + 16:
            raise ValueError("wire too short to be a sealed AES-GCM message")
        nonce, ct = wire[:_NONCE_LEN], wire[_NONCE_LEN:]
        return self._aead.decrypt(nonce, ct, aad)

    def key_fingerprint(self) -> str:
        import hashlib
        return hashlib.sha256(self.aes_key).hexdigest()[:16]


# ─── Handshake ───────────────────────────────────────────────────────────


def _ec_pub_bytes(pub: ec.EllipticCurvePublicKey) -> bytes:
    return pub.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )


def _load_ec_pub(raw: bytes) -> ec.EllipticCurvePublicKey:
    return ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw)


def handshake(
    local_id: IdentityKey,
    peer_id_pub: ed25519.Ed25519PublicKey,
    peer_name: str,
) -> Tuple[SecureChannel, "_Pending"]:
    """Start the handshake on the *local* side.

    Returns ``(eventual_channel_placeholder, pending)``. The caller wires
    ``pending`` to its peer (which does the same) and then calls
    :func:`complete_handshake` on each side.

    For the simulated single-process server+client setup used in Phase 1
    we expose :func:`handshake_pair` which does both sides at once.
    """
    eph = ec.generate_private_key(ec.SECP256R1())
    eph_pub_bytes = _ec_pub_bytes(eph.public_key())
    peer_id_pub_bytes = peer_id_pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    signature = local_id.private.sign(eph_pub_bytes + peer_id_pub_bytes)
    pending = _Pending(
        local_id=local_id,
        local_eph_priv=eph,
        local_eph_pub_bytes=eph_pub_bytes,
        local_signature=signature,
        peer_id_pub=peer_id_pub,
        peer_name=peer_name,
    )
    return pending  # type: ignore[return-value]


@dataclass
class _Pending:
    local_id: IdentityKey
    local_eph_priv: ec.EllipticCurvePrivateKey
    local_eph_pub_bytes: bytes
    local_signature: bytes
    peer_id_pub: ed25519.Ed25519PublicKey
    peer_name: str


def complete_handshake(
    pending: _Pending,
    peer_eph_pub_bytes: bytes,
    peer_signature: bytes,
) -> SecureChannel:
    """Verify peer's signature, derive AES key, build the channel."""
    local_id_pub_bytes = pending.local_id.public_bytes()
    try:
        pending.peer_id_pub.verify(
            peer_signature, peer_eph_pub_bytes + local_id_pub_bytes,
        )
    except Exception as exc:  # InvalidSignature et al.
        raise HandshakeError(
            f"Peer {pending.peer_name!r} signature failed verification"
        ) from exc

    peer_eph_pub = _load_ec_pub(peer_eph_pub_bytes)
    shared = pending.local_eph_priv.exchange(ec.ECDH(), peer_eph_pub)

    # Deterministic transcript: sorted by raw pubkey so both sides agree.
    a, b = sorted([pending.local_eph_pub_bytes, peer_eph_pub_bytes])
    transcript = a + b
    aes_key = HKDF(
        algorithm=hashes.SHA256(),
        length=_AES_KEY_LEN,
        salt=transcript,
        info=_HKDF_INFO,
    ).derive(shared)

    import hashlib
    return SecureChannel(
        local_name=pending.local_id.name,
        peer_name=pending.peer_name,
        aes_key=aes_key,
        transcript_digest=hashlib.sha256(transcript).digest(),
    )


def handshake_pair(
    a_id: IdentityKey, b_id: IdentityKey,
) -> Tuple[SecureChannel, SecureChannel]:
    """Convenience: run both sides of the handshake in-process.

    Used by the simulated server↔client setup in Phase 1. Returns
    ``(channel_on_A, channel_on_B)`` — both with the same AES key.
    """
    pa = handshake(a_id, b_id.public, b_id.name)
    pb = handshake(b_id, a_id.public, a_id.name)
    ca = complete_handshake(pa, pb.local_eph_pub_bytes, pb.local_signature)
    cb = complete_handshake(pb, pa.local_eph_pub_bytes, pa.local_signature)
    # Sanity: both ends MUST derive the same key.
    if ca.aes_key != cb.aes_key:
        raise HandshakeError("derived AES keys differ — protocol bug")
    return ca, cb
