"""Federated server — global model init + broadcast (paper §3.1, eq. 1).

Phase 1 responsibility:

* Instantiate the global ``KANConvNet`` ``M_G^(0)`` on the server.
* Optionally load a *pre-trained* checkpoint (paper says the global
  model is initialised "with pre-trained weights").
* Establish a SecureChannel with every client ``D_i``, i ∈ {1..N}.
* Serialise the global ``state_dict`` and ship it through each channel.
* Verify every client decodes an identical model (hash check).

Federated *training* (local epochs, GA evolution, TOPSIS+Multi-Krum
aggregation) is Phase 2+.
"""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import torch

from models import KANConvNet

from .secure_channel import IdentityKey, SecureChannel, handshake_pair


# ─── State-dict (de)serialisation ────────────────────────────────────────


def _serialise_state_dict(sd: Dict[str, torch.Tensor]) -> bytes:
    buf = io.BytesIO()
    torch.save(sd, buf)
    return buf.getvalue()


def _deserialise_state_dict(blob: bytes) -> Dict[str, torch.Tensor]:
    return torch.load(io.BytesIO(blob), map_location="cpu", weights_only=True)


def _state_dict_digest(sd: Dict[str, torch.Tensor]) -> str:
    h = hashlib.sha256()
    for k in sorted(sd.keys()):
        h.update(k.encode())
        h.update(sd[k].detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


# ─── Simulated client ────────────────────────────────────────────────────


@dataclass
class FederatedClient:
    """In-process simulated vehicle ``D_i``."""

    client_id: int
    name: str
    identity: IdentityKey
    sample_indices: "Optional[object]" = None    # numpy array of train indices
    channel: Optional[SecureChannel] = None
    model: Optional[KANConvNet] = None
    received_model_digest: Optional[str] = None

    def receive_model(self, ciphertext: bytes, model_factory) -> None:
        """Decrypt, load state_dict, instantiate local model."""
        if self.channel is None:
            raise RuntimeError(f"client {self.name}: no SecureChannel")
        blob = self.channel.decrypt(ciphertext, aad=b"global_model")
        sd = _deserialise_state_dict(blob)
        self.received_model_digest = _state_dict_digest(sd)
        m = model_factory()
        m.load_state_dict(sd)
        self.model = m


# ─── Federated server ────────────────────────────────────────────────────


@dataclass
class FederatedServer:
    """In-process simulated central server."""

    model: KANConvNet
    identity: IdentityKey
    model_kwargs: Dict[str, object] = field(default_factory=dict)
    clients: List[FederatedClient] = field(default_factory=list)
    channels: Dict[int, SecureChannel] = field(default_factory=dict)
    pretrained_path: Optional[Path] = None
    pretrained_loaded: bool = False

    # ── factory ────────────────────────────────────────────────────────
    @classmethod
    def initialise(
        cls,
        in_features: int,
        n_classes: int,
        layer_size: int,
        dropout: float,
        fourier_modes: int,
        conv_channels,
        kernel_size: int,
        use_conv_backbone: bool,
        pretrained_path: Optional[Path] = None,
        server_name: str = "fedio-server",
    ) -> "FederatedServer":
        kwargs = dict(
            in_features=in_features, n_classes=n_classes,
            layer_size=layer_size, dropout=dropout,
            fourier_modes=fourier_modes, conv_channels=conv_channels,
            kernel_size=kernel_size, use_conv_backbone=use_conv_backbone,
        )
        model = KANConvNet(**kwargs)
        loaded = False
        if pretrained_path is not None and Path(pretrained_path).exists():
            ckpt = torch.load(pretrained_path, map_location="cpu",
                              weights_only=True)
            sd = ckpt.get("model_state_dict", ckpt)
            # Allow shape mismatches on the final classification head if
            # n_classes differs from the pretrained checkpoint.
            missing, unexpected = model.load_state_dict(sd, strict=False)
            loaded = True
            print(f"[server] loaded pretrained {Path(pretrained_path).name} "
                  f"(missing={len(missing)} unexpected={len(unexpected)})")
        else:
            print("[server] initialised global model with fresh weights")
        return cls(
            model=model,
            identity=IdentityKey.generate(server_name),
            model_kwargs=kwargs,
            pretrained_path=Path(pretrained_path) if pretrained_path else None,
            pretrained_loaded=loaded,
        )

    # ── client registration + handshake ────────────────────────────────
    def register_client(
        self,
        client_id: int,
        sample_indices=None,
        name_prefix: str = "vehicle",
    ) -> FederatedClient:
        name = f"{name_prefix}-{client_id:04d}"
        client = FederatedClient(
            client_id=client_id, name=name,
            identity=IdentityKey.generate(name),
            sample_indices=sample_indices,
        )
        server_chan, client_chan = handshake_pair(self.identity, client.identity)
        self.channels[client_id] = server_chan
        client.channel = client_chan
        self.clients.append(client)
        return client

    # ── broadcast ──────────────────────────────────────────────────────
    def broadcast_global_model(self) -> Dict[str, "str|int"]:
        """Send the current global ``state_dict`` to every client.

        Returns a small audit report.
        """
        sd = self.model.state_dict()
        blob = _serialise_state_dict(sd)
        truth_digest = _state_dict_digest(sd)

        n_ok = 0
        mismatched: List[int] = []
        for client in self.clients:
            chan = self.channels[client.client_id]
            ct = chan.encrypt(blob, aad=b"global_model")
            client.receive_model(ct, model_factory=self._clone_model)
            if client.received_model_digest == truth_digest:
                n_ok += 1
            else:
                mismatched.append(client.client_id)

        return {
            "n_clients": len(self.clients),
            "n_ok": n_ok,
            "n_mismatched": len(mismatched),
            "mismatched_client_ids": mismatched[:10],
            "global_state_dict_sha256": truth_digest,
            "bytes_per_client": len(blob),
            "param_count": sum(p.numel() for p in self.model.parameters()),
        }

    # ── helper ─────────────────────────────────────────────────────────
    def _clone_model(self) -> KANConvNet:
        return KANConvNet(**self.model_kwargs)


# Re-export for ``from federated import broadcast_state_dict``.
def broadcast_state_dict(server: FederatedServer) -> Dict[str, "str|int"]:
    """Functional alias for :meth:`FederatedServer.broadcast_global_model`."""
    return server.broadcast_global_model()
