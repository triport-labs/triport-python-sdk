# Public contract snapshots

`methods.json` records the reviewed method names and parameter styles from the
public OpenRPC contracts for all nine networks. Supplier-specific method
extensions are excluded from the exported public registry.

`reads.json` contains one synthetic, read-only request/response example per
network. Heights and other response values are artificial test data. These
fixtures contain no captured traffic, credentials or deployment metadata.

Update the manifest alongside generated bindings when public contracts change.
The tests fail if a network disappears or a generated registry diverges from
the reviewed manifest.
