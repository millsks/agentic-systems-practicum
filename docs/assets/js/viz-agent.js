/* Agent visualizers: the agent loop (who talks to whom, and how the message list grows) and a token meter. */
(() => {
  "use strict";
  const { registerViz } = window.PPViz;

  const U = (text) => ({ role: "user", kind: "text", text });
  const A = (text) => ({ role: "assistant", kind: "text", text });
  const CALL = (name, input, id) => ({ role: "assistant", kind: "tool_use", text: `${name}(${JSON.stringify(input)})`, id });
  const RESULT = (id, text, error = false) => ({ role: "user", kind: "tool_result", text, id, error });

  /* A step: who acts, the arrow it travels, what it says, and blocks it appends to the message list. */
  const SCENARIOS = {
    weather: {
      title: "One tool call, start to finish",
      steps: [
        { at: "code", say: "Your code builds the request: the user's question plus the tool definitions.", add: [U("What's the weather in Paris?")] },
        { at: "model", arrow: "code-model", say: "messages.create(...) sends the WHOLE list. The model sees one user message and one tool it may use." },
        { at: "code", arrow: "model-code", say: "Response: stop_reason = \"tool_use\". The model did not run anything; it asked you to.", add: [CALL("get_weather", { city: "Paris" }, "toolu_1")], stop: "tool_use" },
        { at: "tool", arrow: "code-tool", say: "Your code runs get_weather(city=\"Paris\") itself. Tools run in your process, with your permissions." },
        { at: "code", arrow: "tool-code", say: "The result is wrapped in a tool_result block that echoes the same id, toolu_1.", add: [RESULT("toolu_1", "18°C, light rain")] },
        { at: "model", arrow: "code-model", say: "Second request: the same list, now four blocks long. The model has no memory; the list IS its memory." },
        { at: "code", arrow: "model-code", say: "stop_reason = \"end_turn\": no more tool calls. The loop ends and you show the text.", add: [A("It's 18°C with light rain in Paris; take an umbrella.")], stop: "end_turn" },
      ],
    },
    chain: {
      title: "Two tools in sequence, then two in parallel",
      steps: [
        { at: "code", say: "The user asks something that needs several lookups.", add: [U("Is it warmer in Lisbon or Oslo right now, and what time is it in each?")] },
        { at: "model", arrow: "code-model", say: "Request 1." },
        { at: "code", arrow: "model-code", say: "The model asks for two independent calls in ONE response (parallel tool use).", add: [CALL("get_weather", { city: "Lisbon" }, "toolu_1"), CALL("get_weather", { city: "Oslo" }, "toolu_2")], stop: "tool_use" },
        { at: "tool", arrow: "code-tool", say: "Run both. They do not depend on each other, so you may run them concurrently." },
        { at: "code", arrow: "tool-code", say: "Return BOTH results in a single user message, each matched by id.", add: [RESULT("toolu_1", "21°C, sunny"), RESULT("toolu_2", "4°C, cloudy")] },
        { at: "model", arrow: "code-model", say: "Request 2." },
        { at: "code", arrow: "model-code", say: "Now it needs the times. Each answer can lead to the next question: that is what makes it a loop.", add: [CALL("get_time", { city: "Lisbon" }, "toolu_3"), CALL("get_time", { city: "Oslo" }, "toolu_4")], stop: "tool_use" },
        { at: "tool", arrow: "code-tool", say: "Run both time lookups." },
        { at: "code", arrow: "tool-code", say: "Append the results.", add: [RESULT("toolu_3", "14:05"), RESULT("toolu_4", "15:05")] },
        { at: "model", arrow: "code-model", say: "Request 3: eight blocks of history, all re-sent." },
        { at: "code", arrow: "model-code", say: "end_turn. Three requests, four tool calls, one answer.", add: [A("Lisbon is warmer (21°C vs 4°C). It's 14:05 in Lisbon and 15:05 in Oslo.")], stop: "end_turn" },
      ],
    },
    error: {
      title: "A tool fails, and the model recovers",
      steps: [
        { at: "code", say: "The user mistypes a city.", add: [U("Weather in Pariss?")] },
        { at: "model", arrow: "code-model", say: "Request 1." },
        { at: "code", arrow: "model-code", say: "The model passes the name through as given.", add: [CALL("get_weather", { city: "Pariss" }, "toolu_1")], stop: "tool_use" },
        { at: "tool", arrow: "code-tool", say: "The tool raises CityNotFound. Crashing the program here would end the conversation." },
        { at: "code", arrow: "tool-code", say: "Instead, catch it and send the error back as data: a tool_result with is_error = true and a helpful message.", add: [RESULT("toolu_1", "Unknown city 'Pariss'. Did you mean 'Paris'?", true)] },
        { at: "model", arrow: "code-model", say: "Request 2: the model reads the error like any other result." },
        { at: "code", arrow: "model-code", say: "It corrects itself and tries again.", add: [CALL("get_weather", { city: "Paris" }, "toolu_2")], stop: "tool_use" },
        { at: "tool", arrow: "code-tool", say: "This time the tool succeeds." },
        { at: "code", arrow: "tool-code", say: "Append the result.", add: [RESULT("toolu_2", "18°C, light rain")] },
        { at: "model", arrow: "code-model", say: "Request 3." },
        { at: "code", arrow: "model-code", say: "end_turn. A good error message turned a crash into a one-step detour.", add: [A("I assumed you meant Paris: 18°C with light rain.")], stop: "end_turn" },
      ],
    },
    runaway: {
      title: "A loop with no stop condition",
      steps: [
        { at: "code", say: "A task the tools cannot actually solve.", add: [U("Find the 2031 census population of Atlantis.")] },
        { at: "model", arrow: "code-model", say: "Request 1." },
        { at: "code", arrow: "model-code", say: "Search.", add: [CALL("search", { q: "Atlantis census 2031" }, "toolu_1")], stop: "tool_use" },
        { at: "code", arrow: "tool-code", say: "No results.", add: [RESULT("toolu_1", "0 results")] },
        { at: "code", arrow: "model-code", say: "Search again, slightly differently.", add: [CALL("search", { q: "Atlantis population 2031" }, "toolu_2")], stop: "tool_use" },
        { at: "code", arrow: "tool-code", say: "No results. Every turn re-sends the growing list, so each request costs more than the last.", add: [RESULT("toolu_2", "0 results")] },
        { at: "code", arrow: "model-code", say: "And again.", add: [CALL("search", { q: "Atlantis 2031 census data" }, "toolu_3")], stop: "tool_use" },
        { at: "code", arrow: "tool-code", say: "Your step limit (3) is reached. A well-built loop stops here and reports, instead of spending forever.", add: [RESULT("toolu_3", "0 results")], halt: "Stopped: max_steps = 3" },
      ],
    },
  };

  const NODES = { code: { x: 130, y: 70, label: "Your code", sub: "the loop" }, model: { x: 390, y: 70, label: "Model API", sub: "messages.create" }, tool: { x: 130, y: 210, label: "Tools", sub: "your functions" } };
  const ARROWS = {
    "code-model": ["code", "model", -10], "model-code": ["model", "code", 10],
    "code-tool": ["code", "tool", -12], "tool-code": ["tool", "code", 12],
  };

  registerViz("agent-loop", (el, config, api) => {
    const { h, s } = api;
    const names = Object.keys(SCENARIOS);
    let scenario = SCENARIOS[config.scenario] ? config.scenario : "weather";
    const ui = api.shell(el, { title: SCENARIOS[scenario].title, kind: "Agent loop" });
    const wrap = h("div", { style: "display:grid;grid-template-columns:minmax(260px,1fr) minmax(240px,1fr);gap:14px;align-items:start" });
    const svg = s("svg", { viewBox: "0 0 520 280", width: "100%", role: "img", "aria-label": "Agent loop diagram", style: "max-width:520px;height:auto;font-family:var(--font-sans)" });
    const list = h("ol", { class: "viz-messages", style: "list-style:none;margin:0;padding:0;font:0.78rem/1.4 var(--font-mono);display:flex;flex-direction:column;gap:6px;max-height:300px;overflow:auto" });
    wrap.append(svg, h("div", {}, h("div", { style: "font-size:0.75rem;color:var(--fg-muted);margin-bottom:6px", text: "messages (what the next request sends)" }), list));
    ui.stage.append(wrap);
    ui.setLegend([["user turn", "var(--viz-1)"], ["assistant turn", "var(--viz-2)"], ["tool_result", "var(--viz-3)"], ["error result", "var(--bad)"]]);

    const color = (b) => (b.kind === "tool_result" ? (b.error ? "var(--bad)" : "var(--viz-3)") : b.role === "user" ? "var(--viz-1)" : "var(--viz-2)");

    function frames() {
      const out = [];
      let msgs = [];
      let requests = 0;
      for (const step of SCENARIOS[scenario].steps) {
        if (step.arrow === "code-model") requests += 1;
        msgs = [...msgs, ...(step.add || [])];
        out.push({ step, msgs, requests });
      }
      return out;
    }

    function render(frame) {
      svg.replaceChildren();
      const defs = s("defs", {}, s("marker", { id: "al-arrow", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" }, s("path", { d: "M0 0L10 5L0 10z", fill: "var(--accent)" })));
      svg.append(defs);
      for (const [key, [from, to, off]] of Object.entries(ARROWS)) {
        const a = NODES[from];
        const b = NODES[to];
        const active = frame.step.arrow === key;
        const horizontal = a.y === b.y;
        const x1 = horizontal ? a.x + (b.x > a.x ? 70 : -70) : a.x + off;
        const x2 = horizontal ? b.x + (b.x > a.x ? -70 : 70) : b.x + off;
        const y1 = horizontal ? a.y + off : a.y + (b.y > a.y ? 32 : -32);
        const y2 = horizontal ? b.y + off : b.y + (b.y > a.y ? -32 : 32);
        svg.append(s("line", { x1, y1, x2, y2, stroke: active ? "var(--accent)" : "var(--border-strong)", "stroke-width": active ? 3 : 1.25, "marker-end": active ? "url(#al-arrow)" : null, "stroke-dasharray": active ? null : "4 4" }));
      }
      for (const [key, n] of Object.entries(NODES)) {
        const active = frame.step.at === key;
        svg.append(
          s("rect", { x: n.x - 70, y: n.y - 32, width: 140, height: 64, rx: 10, fill: active ? "var(--accent-soft)" : "var(--bg-elev)", stroke: active ? "var(--accent)" : "var(--border-strong)", "stroke-width": active ? 2.5 : 1.25 }),
          s("text", { x: n.x, y: n.y - 4, "text-anchor": "middle", "font-size": 14, "font-weight": 600, fill: "var(--fg)", text: n.label }),
          s("text", { x: n.x, y: n.y + 15, "text-anchor": "middle", "font-size": 11, fill: "var(--fg-muted)", text: n.sub }),
        );
      }
      const stop = frame.step.stop ? `stop_reason: ${frame.step.stop}` : frame.step.halt || "";
      svg.append(
        s("text", { x: 390, y: 170, "text-anchor": "middle", "font-size": 12, fill: "var(--fg-muted)", text: `requests sent: ${frame.requests}` }),
        s("text", { x: 390, y: 192, "text-anchor": "middle", "font-size": 12, fill: "var(--fg-muted)", text: `blocks in history: ${frame.msgs.length}` }),
        s("text", { x: 390, y: 222, "text-anchor": "middle", "font-size": 13, "font-weight": 600, fill: frame.step.halt ? "var(--bad)" : "var(--accent)", text: stop }),
      );
      list.replaceChildren(...frame.msgs.map((b, i) => h("li", { style: `border-left:4px solid ${color(b)};background:var(--bg-sunk);padding:4px 8px;border-radius:4px;${i >= frame.msgs.length - (frame.step.add || []).length ? "outline:1px solid var(--accent)" : ""}` },
        h("span", { style: "color:var(--fg-muted)", text: `${b.role} · ${b.kind}${b.id ? ` [${b.id}]` : ""}` }), h("br"), b.text)));
      list.scrollTop = list.scrollHeight;
      ui.setLog(api.esc(frame.step.say));
    }

    const play = api.player(ui.controls, render, { speed: 900 });
    ui.controls.prepend(api.select(names.map((n) => [n, SCENARIOS[n].title]), scenario, (v) => { scenario = v; el.querySelector(".w-title").textContent = SCENARIOS[v].title; play.load(frames()); }));
    play.load(frames());
  });

  /* Token meter: approximate tokens, context share, and cost for a piece of text. */
  registerViz("token-meter", (el, config, api) => {
    const { h } = api;
    const ui = api.shell(el, { title: config.title || "How big is this prompt?", kind: "Token meter" });
    const PRICES = { "claude-opus-5-5": [4, 20], "claude-sonnet-5-5": [2, 10], "claude-haiku-5-5": [0.1, 0.5] };
    const area = h("textarea", { rows: 6, style: "width:100%;font:0.85rem/1.45 var(--font-mono);padding:8px;border:1px solid var(--border);border-radius:6px;background:var(--bg-code);color:var(--fg)" });
    area.value = config.text || "You are a helpful assistant. Summarize the attached incident report in three bullet points for an on-call engineer.";
    let model = "claude-opus-5-5";
    const repeat = h("input", { type: "number", min: 1, max: 1000000, value: config.calls || 1000, style: "width:7em" });
    const pieces = h("div", { style: "font:0.8rem/1.9 var(--font-mono);margin-top:10px;word-break:break-word" });
    const out = h("div", { style: "display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:10px" });
    ui.stage.append(area, pieces, out);
    ui.controls.append(api.select(Object.keys(PRICES).map((m) => [m, m]), model, (v) => { model = v; update(); }), api.label("requests", repeat));
    const tile = (k, v) => h("div", { style: "background:var(--bg-sunk);border:1px solid var(--border);border-radius:6px;padding:6px 10px" }, h("div", { style: "font-size:0.72rem;color:var(--fg-muted)", text: k }), h("div", { style: "font-weight:600", text: v }));
    function chunks(text) {
      const out = [];
      for (const word of text.match(/\s*\S+/g) || []) {
        for (let i = 0; i < word.length; i += 4) out.push(word.slice(i, i + 4));
      }
      return out;
    }
    function update() {
      const parts = chunks(area.value);
      const tokens = Math.ceil(area.value.length / 4);
      const [inPrice] = PRICES[model];
      const n = Math.max(1, Number(repeat.value) || 1);
      pieces.replaceChildren(...parts.slice(0, 160).map((p, i) => h("span", { style: `background:${i % 2 ? "var(--accent-soft)" : "var(--bg-sunk)"};border-radius:3px;padding:1px 0;white-space:pre`, text: p })), parts.length > 160 ? h("span", { text: ` … +${parts.length - 160} more` }) : "");
      out.replaceChildren(
        tile("characters", area.value.length.toLocaleString()),
        tile("≈ tokens (chars ÷ 4)", tokens.toLocaleString()),
        tile("share of a 1M window", `${((tokens / 1e6) * 100).toFixed(4)}%`),
        tile(`input cost × ${n.toLocaleString()} requests`, `$${((tokens * n * inPrice) / 1e6).toFixed(4)}`),
      );
      ui.setLog("Shaded runs approximate how a tokenizer splits text. Real tokenizers differ by model and language; use messages.count_tokens for exact counts.");
    }
    area.addEventListener("input", update);
    repeat.addEventListener("input", update);
    update();
  });
})();
