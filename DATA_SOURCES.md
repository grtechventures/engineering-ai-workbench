# Source discovery and data sources

Source discovery registers source-code folders or files for bounded, read-only inspection. Data sources registers CSV, application binary, HDF5, database, and other input references, plus descriptions, units/schema notes and reader references. Registration grants no access and never runs code.

An administrator must set `EWB_RESOURCE_ROOTS` to a JSON array of absolute approved filesystem roots before starting the service. The default is an empty list. Use narrowly scoped directories containing only material suitable for inspection. Local folders and explicitly approved mounted shares can be used; GitHub is not required and URLs are never fetched. OS permissions and firewall policy remain necessary, especially for mapped network drives. Do not enter passwords or connection strings containing secrets.

Inspection checks the allowlist on every call, rejects symlinks and parent traversal, and limits source previews to 20 supported text files, 64 KB each and 256 KB total. Hidden directories, common dependency folders and runtime data folders are skipped during directory scans. Large files are skipped. CSV preview is limited to 64 KB, displays ten data rows, and preserves values as text without inferring physical units. Preview hashes identify the bytes inspected.

Binary, HDF5 and database entries are metadata only until their approved readers are integrated. CSV preview is not yet an analysis input snapshot. Automatic retrieval of registered source code into model prompts, attaching datasets to Python tasks, database queries, and executable adapter generation are not implemented. Source inspection does not authorize any compilation or execution.

Use Inspect after registering a location. Remove registration deletes the reference, never the underlying files. Existing registrations persist in the local workspace database. Restart the service after changing approved roots.
