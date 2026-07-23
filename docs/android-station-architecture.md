# Android station architecture

## Trust boundaries

The Android app is the only user-authenticated client. It obtains Firebase ID
tokens and sends them to PRANA API for pairing, control and revocation. A station
stores only its independent Ed25519 private key in Credential Manager or Secret
Service. No Firebase refresh token is copied to the station.

Private Firestore collections are `station_registry`, `station_pairings`,
`station_activation_index` and `station_request_nonces`. Mobile-visible
projections live below:

```text
users/{uid}/stations/{station_id}
users/{uid}/stations/{station_id}/sessions/{session_id}
users/{uid}/stations/{station_id}/sessions/{session_id}/results/{request_id}
```

Firestore Rules permit the authenticated owner to read this projection and deny
all client writes. Admin SDK calls from PRANA API continue to use IAM.

## Pairing

For a provisioned Raspberry Pi, `prana-station-provision` registers the station
public key and activation hash, then produces a fixed PNG/SVG device label. The
QR contains a ten-character Setup ID and a sixteen-character activation code;
it never contains the Ed25519 private key. The signed-in phone claims the
station through `POST /v1/station-activations/claim`. The first claim assigns the
owner, repeated scans by the same owner are idempotent, and other accounts are
rejected. Multiple phones signed into the same Firebase account receive the
same Firestore projection without another claim.

The activation code does not expire, but cannot transfer ownership. Revoked or
transferred stations require an audited admin operation. Claim attempts are
rate-limited independently by user, Setup ID and client IP.

Legacy and temporary pairing remains available:

1. `prana-station` creates or loads its persistent Ed25519 identity.
2. It proves possession of the private key to `POST /v1/station-pairings`.
3. The API returns an eight-character one-time code and a `prana-elex:///pair`
   QR deep link. Only the SHA-256 hash is stored, with a ten-minute expiry.
4. The signed-in phone claims the pairing through PRANA API. The transaction
   enforces station ownership and the plan's separate `max_stations` limit.
5. Reuse, expiry, wrong codes and cross-owner operations are rejected.

## Control and realtime data

The station polls desired state every two seconds. A generation counter makes
Start, Stop and language updates latest-wins and idempotent. Retry has its own
counter. Heartbeats are sent every five seconds and include the observed
generation, capture state, session, sequence and app version.

The phone considers a station offline when `last_seen_at` is older than 15
seconds. It observes status and results with Firestore listeners. REST remains the
only mutation path. Start and Stop remain pending in the UI until
`observed_generation` catches up; language selection is optimistic.

Station audio requests reuse the existing WAV validation, Gemini processing,
GCS archive and quota reservation flow. The owner UID is resolved server-side
from the station registry. Successful responses are written to the session result
projection with a 14-day TTL and contain no audio URL.

## Operations

- Provision and generate a Pi label:
  `prana-station-provision --config apps/linux/config/default.toml --output ~/prana-station-label`
- Run a station: `prana-station --config apps/linux/config/default.toml`
- Bootstrap plan defaults after deployment so `max_stations` is present.
- Deploy Firestore Rules and Terraform TTL fields for `results`, pairings and
  station request nonces.
- Keep Cloud Run stateless. Signature replay records, pairing state, desired
  state and idempotency records are all stored in Firestore.
