# Forage AI

Forage AI finds open-source GitHub projects that match a user's plain-English description of a software need and turns the one they choose into something double-clickable on Windows.

## Language

**Discovery Query**:
The user's plain-English description of the software need they want to satisfy.
_Avoid_: prompt, search, request

**Candidate**:
An open-source GitHub repository proposed to the user as a match for a Discovery Query, presented with tradeoffs.
_Avoid_: result, match, repo suggestion

**Build Request**:
The user's selection of one Candidate to install.
_Avoid_: install, compile, selection

**Package**:
Turning a Candidate into a runnable artifact on the user's machine.
_Avoid_: compile, build, install

**Packaged App**:
A runnable artifact installed locally on the user's Windows machine.
_Avoid_: binary, executable, desktop app

**Shortcut App**:
A Windows shortcut plus optional local launcher that opens a web-app Candidate, used when the Candidate is not a desktop program.
_Avoid_: web install, PWA, exe wrapper

**Risk Card**:
The pre-install summary of a Candidate's license, maintenance, provenance, and access requirements, shown before the user consents to a Build Request.
_Avoid_: warning, disclaimer, health check
