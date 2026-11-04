# Synthetic management UI

This is a dependency-free, accessible management UI vertical slice. It uses
only the versioned `/api/v1` contract and is intended for the local
`ag-synthetic` endpoint. Serve `ui/` with a static file server and start the
API with `python3 -m ag_datovka.server --host 127.0.0.1 --port 8080`.

The Compose `web` service packages both static applications in
`deploy/web.Dockerfile`. The management UI is served at `/`; a request whose
host starts with `user.` receives `ui/user/`. During the image build, a digest
of the source assets is injected into the JS/CSS URLs. Nginx revalidates HTML
and gives only those versioned JS/CSS URLs an immutable one-year cache. This
keeps browser or proxy caches from hiding assets after an upgrade.

The UI never contains production hosts, credentials, raw private keys, or a
legacy AGDatovka runtime dependency. It supports box, identity, membership,
message/attachment, operation/lifecycle, search, export, and audit views. It
does not claim delivery until a local synthetic worker projects the queued
operation and receipt. See `evidence/AGDA-28/README.md` for reproduction and
the manual scenario record.
