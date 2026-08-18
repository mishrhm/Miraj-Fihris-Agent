# Documentation index

Start with [PROJECT.md](PROJECT.md) for the architecture overview, then:

| Doc | Read this for |
|---|---|
| [PROJECT.md](PROJECT.md) | What the system does, how the pieces fit together, directory layout |
| [SETUP.md](SETUP.md) | Installing, configuring `.env`, running locally, verifying credentials safely |
| [API.md](API.md) | The one HTTP endpoint: request/response fields, examples, error codes |
| [DECISIONS.md](DECISIONS.md) | Why the code is shaped the way it is — every non-obvious workaround and the incident that caused it |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Symptom → cause → fix, indexed by error message |
| [AGENTS.md](AGENTS.md) | Rules specifically for AI coding agents working in this repo — read before running anything that publishes or uploads |

If you only read one file before making a change: **AGENTS.md** if you're an AI
agent, **DECISIONS.md** if you're human and about to "simplify" something that
looks like a workaround.
