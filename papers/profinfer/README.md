# ProfInfer

ProfInfer is presented by its authors as an eBPF-based, fine-grained LLM inference profiler. This catalogue preserves the arXiv manuscript separately from its reproducibility artifact.

- Manuscript: [`paper/profinfer-arxiv-2601.20755v2.pdf`](paper/profinfer-arxiv-2601.20755v2.pdf)
- Artifact, installation, and usage: [`artifact/README.md`](artifact/README.md)
- Detailed Linux CPU reproduction: [`artifact/REPRODUCING.md`](artifact/REPRODUCING.md)
- Paper metadata: [`metadata/paper.json`](metadata/paper.json)
- Artifact metadata: [`metadata/artifact.json`](metadata/artifact.json)
- Entities and relationships: [`metadata/entities.json`](metadata/entities.json), [`metadata/relationships.json`](metadata/relationships.json)
- Experiment lineage: [`artifact/experiments/index.json`](artifact/experiments/index.json)

The Linux CPU/x86 path has local run outputs, but ARM PMU, OpenHarmony, RKNPU/RKNN, Mali/OpenCL, and paper-identical hardware results have not been reproduced in this workspace. Model weights and the external `llama.cpp` checkout are intentionally excluded from Git.

