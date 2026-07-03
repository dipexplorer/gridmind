// Root page — redirects to dashboard if logged in, or login if not
// This is a placeholder; full routing logic comes in Week 3
export default function Home() {
  return (
    <main style={{ display: "grid", placeItems: "center", height: "100vh" }}>
      <div style={{ textAlign: "center" }}>
        <h1 style={{ fontSize: "2rem", fontWeight: "bold", color: "#6366f1" }}>
          ⚡ GridMind
        </h1>
        <p style={{ color: "#94a3b8", marginTop: "0.5rem" }}>
          Transformer Intelligence Platform — Loading...
        </p>
        <p style={{ color: "#64748b", fontSize: "0.875rem", marginTop: "1rem" }}>
          API: <a href="http://localhost:8000/api/docs" style={{ color: "#6366f1" }}>
            localhost:8000/api/docs
          </a>
        </p>
      </div>
    </main>
  );
}
