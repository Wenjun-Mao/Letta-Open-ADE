# Interfig Presentation Adaptation

The edge-routing algorithm in `flow-model.js` is adapted from
`hindsight-interfig/src/geometry.ts` in
[vectorize-io/hindsight](https://github.com/vectorize-io/hindsight/blob/9269b88417ed263e5a8350f2e416ca2b322756b1/hindsight-interfig/src/geometry.ts),
pinned to `9269b88417ed263e5a8350f2e416ca2b322756b1`.

The local renderer uses interfig's group/node/edge/step schema and presentation
ideas from `src/index.tsx`: sequential beats, cumulative content, content-sized
cards, moving packets, narration and independent tours. It is a small standalone
SVG/DOM adaptation, not a vendored React renderer or ADE runtime dependency.
Controls add manual stepping and stop at the end instead of cycling into another
tour. The focused view projects the same inventory layout to current endpoints;
the whole-architecture view retains all ownership frames and records.
The ADE presentation adds a card-aware Manhattan fallback for obstructed active
transfers; otherwise it retains the adapted upstream cubic routing.

No Hindsight product architecture or figure data is included. All ADE content is
from the source-backed local specification. This notice is distributed beside
the editable sources and embedded in both generated presentations.

## Upstream MIT License

MIT License

Copyright (c) 2025 Vectorize AI Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
