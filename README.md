# 🎲 Valence Mirage

**An AI-powered narrative engine that balances creative freedom with structured probability.**

---

## What Is It?

Valence Mirage is an interactive storytelling system where players describe actions in natural language and an AI Game Master adjudicates outcomes through explicit probabilistic mechanics — combining the creative freedom of LLMs with the fairness and tension of tabletop dice systems.

Players can attempt anything. Probability decides the cost.

### Core Experience

- **Free-form input** — No restricted command set. Describe what you want to do naturally.
- **Fair outcomes** — Actions are evaluated through probability and resolved with dice, not arbitrary LLM decisions.
- **Rich narration** — An AI Game Master generates immersive story progression, NPC dialogue, and world-building.
- **Strategic depth** — Stats, inventory, and resource constraints create meaningful trade-offs.
- **Anti-exploitation** — Repetition penalties and novelty bonuses encourage diverse, creative play.

---

## How It Works (High-Level)

1. **Player acts** — Describe any action in natural language
2. **System evaluates** — Action is parsed and scored against narrative context, player capabilities, and story coherence
3. **Probability assigned** — Score is converted to a dice threshold
4. **Dice roll resolves** — Success, partial success, or failure
5. **Story continues** — The AI Game Master narrates the outcome and advances the world

---

## Project Status

🧪 **Early Development** — Currently in architecture and prototyping phase.

- [x] Concept & design
- [x] Architecture
- [ ] Core gameplay loop
- [ ] State & constraint systems
- [ ] RAG integration
- [ ] UX layer
- [ ] Playtesting

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python (FastAPI) |
| Frontend | React |
| AI | LLM + Sentence Transformers |
| Search | Vector DB (FAISS) |
| Storage | SQLite → PostgreSQL |

---

## License

TBD

---

*Valence Mirage — Freedom is allowed. Probability decides its cost.*
