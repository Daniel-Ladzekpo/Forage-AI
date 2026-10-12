# Constrained packaging: release assets or allow-listed recipes only

Forage downloads and executes code from arbitrary GitHub repositories, so the obvious design — clone any repo and run its own build scripts — would be remote-code-execution as a feature, plus unmaintainable build failures across ecosystems. We decided that `Package` (never "compile") happens via exactly two paths: 1) reuse the repository's published GitHub Release asset, pinned to a tag with provenance/checksum verification, or 2) build from source only through a curated allow-listed recipe (PyInstaller, Tauri, Electron-builder, Go build) with pinned versions; anything else is refused with a clear reason and offered a Shortcut App alternative. Considered and rejected for v1: an unconstrained build runner (RCE + build-hell) and containerized builds (added complexity; revisit only if release-asset coverage proves too low).

Status: accepted
