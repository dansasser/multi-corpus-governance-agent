# 🤝 Contributing to Multi-Corpus Governance Agent

Thank you for your interest in improving the **Multi-Corpus Governance Agent**!
This project follows a **governance-first development style** — contributions are welcome, but must align with the existing structure and rules.

---

## 📜 Contribution Guidelines

1. **Fork the repo** and create a feature branch.

   * Branch names should be descriptive:

     * `feature/add-connector-twitter`
     * `fix/critic-rag-loop`

2. **Follow governance structure**:

   * Any new code must align with the five-agent pipeline (Ideator → Drafter → Critic → Revisor → Summarizer).
   * Each role’s permissions and responsibilities are defined in [`governance.md`](./governance.md).
   * Do not bypass governance checks or add undocumented shortcuts.

3. **Document changes**:

   * Update related docs (`governance.md`, `routing-matrix.md`, `context-assembly.md`, etc.) if your change affects them.
   * Include diagrams or metadata examples where needed.

4. **Style rules**:

   * Code should follow PEP8 (Python).
   * Markdown files should use emoji headings (consistent with `README.md`).
   * No em dashes — follow repo writing style rules.

---

## 🧪 Testing

* Include **unit tests** for any new connectors, validators, or agents.
* Run existing test suites before submitting a pull request.
* Add at least one **metadata bundle example** (JSON) showing how your change logs attribution, tone, or keywords.

---

## 🗂 Pull Request Process

1. Ensure your branch is up to date with `main`.
2. Submit a pull request with:

   * A clear description of the change.
   * A link to updated documentation.
   * Any limitations or known trade-offs.
3. One of the maintainers will review based on:

   * Alignment with governance.
   * Clarity of documentation.
   * Passing tests.

---

## 🌟 Contribution Ideas

* New connectors (email, calendar, CRM).
* Additional MVLMs for different tones or personas.
* Improved metadata extraction (SEO, long-tail keywords).
* Enhancements to governance rules (e.g., stricter attribution, new tone checks).

---

## 📬 Getting Help

* Open an [issue](./issues) for bug reports or feature requests.
* Use the Discussions tab for brainstorming or proposing larger governance changes.
* Tag maintainers if your contribution touches critical paths (Critic, Revisor, Summarizer).


