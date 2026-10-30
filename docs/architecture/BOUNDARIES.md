# System boundaries

AG Datovka 2 is a standalone reimplementation. It has no code, database,
credentials, or runtime dependency on the former AGDatovka implementation.

Migration of existing databoxes and historical data is a separate project.
This project does define and test the public contracts and observable
workflows that a later migration must preserve.

The architecture must support at least 1,000 messages per minute and large
messages. The initial phase does not execute performance tests. It defines
capacity assumptions, queue and storage boundaries, metrics, failure modes,
and reproducible future test scenarios.
