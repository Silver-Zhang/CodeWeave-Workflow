# Sim interaction sources

Upstream: https://github.com/simstudioai/sim/tree/df3db64ed17a5eb73fef8ccc95da180b0a1cf4b5

Copyright 2026 Sim Studio. Apache-2.0. LICENSE and NOTICE retained here.

- `use-drag-resize.ts`: upstream hook unchanged except attribution header.
- `use-canvas-context-menu.ts`: upstream interaction code, Sim-specific type imports replaced with structural DevFlower UI types; modified file is marked.

DevFlower binds these presentation hooks to its existing draft editor only. They cannot execute agents or change runtime authority.
