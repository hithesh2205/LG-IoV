# ⚠️ Superseded — see `5th Month Progress/`

This folder held the **first pass** of the Month-5 audit write-up (documents
01–07). It has been superseded.

**The canonical location is now:**

```
5th Month Progress/Documentation/
```

## Why this folder is stale

The copies of `01`–`07` here were written *during* the audit, when all seven
defects were still open. The versions in `5th Month Progress/Documentation/`
are the same documents **plus resolution banners** recording what actually
happened — including two findings that measurement later corrected:

* The encrypted squared distance (FheFL eq. 11) was predicted to need a longer
  modulus chain. It does not — it fits at N=8192 in 18.0 ms.
* VeReMi's failure was attributed to CAN-shaped features. The measured cause is
  that windowing ran across *mixed senders*.

Reading the copies here would give you the diagnosis without the outcome.

## What replaced it

| Here | Canonical |
|---|---|
| `01`–`07` (audit trail, no outcomes) | `5th Month Progress/Documentation/01`–`07` **with resolution banners** |
| — | `08`–`10` — the three overdue LG deliverables |
| — | `11_current_status.md` — generated from live results |
| — | `12_next_steps.md` — prioritised roadmap |
| — | `13_why_AES_with_FHE.pdf` — channel design note |
| — | `14`–`16` — packing module, NTT, hardware baseline |
| — | `00_MASTER_DOCUMENTATION.pdf` — the primary document |

## Keep or delete?

Safe to delete. Nothing references it, and everything in it exists in a more
current form under `5th Month Progress/`. It is left in place only so that a
link someone saved earlier does not dead-end.
