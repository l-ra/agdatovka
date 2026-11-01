# Synthetic management UI

This is a dependency-free, accessible management UI vertical slice. It uses
only the versioned `/api/v1` contract and is intended for the local
`ag-synthetic` endpoint. Serve `ui/` with a static file server and start the
API with `python3 -m ag_datovka.server --host 127.0.0.1 --port 8080`.

The UI never contains production hosts, credentials, raw private keys, or a
legacy AGDatovka runtime dependency. It does not claim delivery until a local
synthetic worker projects the queued operation and receipt.
