# Amazon product feedback draft — Alexa+ MCP developer experience

> Draft for the hackathon's required product feedback. Constructive and based on
> our actual build experience. Not submitted.

**Context:** We built a self-hosted MCP server (spec 2025-11-25) for the Alexa+
track and read the official Alexa+ MCP Toolkit docs closely while implementing it.

## What worked well
- The MCP Toolkit docs are clear on the **essentials**: Streamable HTTP requirement
  (SSE deprecated), OAuth 2.1 + PKCE **S256**, the `401` + Protected Resource
  Metadata flow, and the Alexa AI CLI onboarding shape (`configure` / `new mcp` /
  `deploy`). The `< 500 ms` round-trip requirement is a great, concrete constraint
  that pushed us to a clean async design.
- The "return stable identifiers and accept them on later calls" guidance in the
  Functional Requirements was exactly the hook we needed for long-running work.

## Gaps that cost us time (each currently NOT STATED in the docs we read)
1. **Async / long-running work.** The `< 500 ms` budget is stated, but there's no
   guidance on the *intended* pattern for work that exceeds it. Does Alexa+ support
   MCP-native **Tasks** (capability negotiation)? Does it ever auto-poll or deliver
   a deferred result, or is it strictly next-turn retrieval? A short "async
   patterns" page would remove a lot of guesswork.
2. **Identity/session in requests.** It's unclear whether Alexa+ passes any stable
   **customer/session/conversation id** to the MCP server, or whether the server
   must derive identity solely from the linked-account OAuth token. We designed for
   the latter (safer), but explicit confirmation would help.
3. **Persistence expectations.** Whether Alexa+ maintains any state for the add-on,
   or the server owns all state, is not stated.
4. **Access path.** The Alexa+ Developer Console shows **"Coming Soon,"** and
   "Alexa+ for Builders is available to select partners." A clear self-serve path
   (or a documented waitlist/request form) and an ETA for general availability
   would help independent developers plan.
5. **Cost / quotas / response-size limits.** Not documented — even a "free during
   developer preview" note would help.
6. **Testing without partner access.** A public **local simulator** (before
   deployment / before partner access) would let far more developers build and
   validate against the real contract.

## Suggestions
- Publish an "Async & Tasks" guidance page and a canonical `start_x/get_x` example.
- Document exactly what identity/context fields reach the MCP server per request.
- Offer a self-serve developer sandbox + local simulator not gated on partner
  status.
- State cost, quotas, timeouts, and response-size limits explicitly.

Overall: the model is well-designed and we were able to build a complete,
spec-conformant server against it. Closing the documentation gaps above and
opening a self-serve path would make it dramatically easier for independent
developers to ship Alexa+ add-ons.
