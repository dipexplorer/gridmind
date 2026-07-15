window.__NARRATION = {
  voiceId: "pNInz6obpgqjVWt2A4g9", // Pre-fill a good male/neutral voice (e.g. ElevenLabs default)
  modelId: "eleven_multilingual_v2",
  gapSeconds: 0.8,

  slides: [
    // ── Slide 1: Title Slide ──────────────────────
    { lines: [
      "Welcome, Respected GM Sir and project guide. Today, I am presenting GridMind A.I., a predictive maintenance intelligence platform developed for electrical distribution networks like A.P.D.C.L."
    ] },

    // ── Slide 2: The Problem ──────────────────────
    { lines: [
      "Let's look at the core challenge in grid operations today.",
      "Traditional maintenance is entirely reactive. We inspect transformers manually or wait until they fail under stress, causing sudden localized power outages and costly emergency replacements.",
      "GridMind shifts operations to proactive health mode. By continuously analyzing telemetry streams, the system identifies degradation patterns early, allowing A.P.D.C.L. to schedule maintenance weeks before a failure occurs."
    ] },

    // ── Slide 3: How GridMind Works ───────────────
    { lines: [
      "Here is how the data flows through the GridMind system.",
      "First, SCADA systems feed real-time telemetry: Load Factor, Oil Temperature, Voltage, and Current.",
      "Second, our machine learning engine, using the Isolation Forest algorithm, compares these signals simultaneously to identify anomalies, such as high temperature under low load.",
      "Third, we use explainable A.I. with S.H.A.P. values. This breaks down the exact telemetry feature driving the risk score, so field engineers can diagnose the specific root cause."
    ] },

    // ── Slide 4: Weather Integration ──────────────
    { lines: [
      "Now, let's explore Phase 1: Live Weather Integration.",
      "Distribution transformers rely on ambient air for cooling. When outdoor temperatures exceed thirty-five degrees Celsius, their heat dissipation efficiency drops dramatically, speeding up insulation breakdown.",
      "GridMind integrates with the Open-Meteo A.P.I. directly. Using the GPS coordinates of the transformer, it fetches local ambient temperature in real-time and applies up to a fifteen percent risk penalty if thermal stress is detected."
    ] },

    // ── Slide 5: Load Forecasting ─────────────────
    { lines: [
      "In Phase 2, we introduce Load Forecasting to foresee grid stress.",
      "Electricity demand is cyclic. GridMind uses a time-series model to map these daily patterns, modeling the evening peak consumption from six to ten P.M., and the night-time dip from two to six A.M.",
      "By predicting transformer load twenty-four hours in advance, grid operators can proactively shift loads or reschedule high-stress operations to prevent thermal runaway."
    ] },

    // ── Slide 6: Live Web App Demo ────────────────
    { lines: [
      "Let's transition to the live interactive demo of the GridMind web application.",
      "On the GIS map, you can see all substation transformers color-coded by real-time risk level.",
      "Clicking a transformer opens its telemetry dashboard, showing live sensor readings and forecasted future load curves.",
      "The enhanced risk card breaks down the final score, showing exactly how much of the risk is due to base operational anomalies versus live weather stress."
    ] },

    // ── Slide 7: Next Steps & Value ───────────────
    { lines: [
      "To conclude, let's look at the practical value GridMind brings.",
      "The best part is that it requires no new hardware. GridMind runs on telemetry data A.P.D.C.L. is already collecting, adding an intelligent layer on top.",
      "Implementing this can minimize sudden burnouts, extend transformer asset life by fifteen to twenty percent, and ensure grid stability during peak summer seasons. Thank you, and I am happy to answer any questions."
    ] }
  ]
};
