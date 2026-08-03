"""Document text extraction and chunking pipeline.

Submodules are imported directly rather than re-exported here. Importing
`pipeline` at package level created a cycle: `document_chunk_repository`
imports `ingestion.chunking`, which executes this module, which imports
`pipeline`, which imports `document_chunk_repository` again while it is still
initializing. Nothing imported `ingest_document` from the package, so the
re-export only ever made the import order load-bearing.
"""
