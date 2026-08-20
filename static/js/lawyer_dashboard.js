document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("case-search");
  const cards = Array.from(document.querySelectorAll(".case-card"));

  // Live search across FIR number and client name
  searchInput.addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    cards.forEach((card) => {
      const text = card.innerText.toLowerCase();
      card.style.display = text.includes(q) ? "" : "none";
    });
  });

  computeStats(cards);

  // Sidebar nav — placeholder views not built yet
  document.querySelectorAll(".nav-link").forEach((link) => {
    link.addEventListener("click", (e) => {
      if (link.dataset.view === "cases") return;
      e.preventDefault();
    });
  });

  // Enter key triggers claim
  document.getElementById("claim-fir-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") claimCase();
  });
});

function computeStats(cards) {
  const counts = { investigation: 0, "court-proceedings": 0 };
  let hearingThisWeek = 0;
  const now = new Date();
  const weekAhead = new Date();
  weekAhead.setDate(now.getDate() + 7);

  cards.forEach((card) => {
    const status = card.dataset.status;
    if (counts[status] !== undefined) counts[status]++;

    const hearingText = card.querySelector(".case-hearing")?.textContent || "";
    const match = hearingText.match(/(\d{4}-\d{2}-\d{2}|\d{2}\/\d{2}\/\d{4})/);
    if (match) {
      const d = new Date(match[1]);
      if (!isNaN(d) && d >= now && d <= weekAhead) hearingThisWeek++;
    }
  });

  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };
  set("stat-investigation", counts["investigation"]);
  set("stat-court", counts["court-proceedings"]);
  set("stat-hearing", hearingThisWeek);
}

// ──────────────────────────────────────────────
// Claim a case  →  POST /api/fir-records/:fir_no/assign-lawyer
// ──────────────────────────────────────────────
async function claimCase() {
  const input = document.getElementById("claim-fir-input");
  const btn = document.getElementById("claim-btn");
  const msg = document.getElementById("claim-msg");
  const firNo = input.value.trim();

  if (!firNo) {
    showClaimMsg("Enter an FIR number.", "error");
    return;
  }

  btn.disabled = true;
  btn.textContent = "Adding…";

  try {
    const res = await fetch(`/api/fir-records/${encodeURIComponent(firNo)}/assign-lawyer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });
    const data = await res.json();

    if (!res.ok) {
      showClaimMsg(data.error || "Could not add case.", "error");
      return;
    }

    showClaimMsg("Case added. Refreshing…", "success");
    setTimeout(() => window.location.reload(), 700);
  } catch (e) {
    showClaimMsg("Network error. Please try again.", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Add Case";
  }
}

function showClaimMsg(text, type) {
  const msg = document.getElementById("claim-msg");
  msg.textContent = text;
  msg.className = `claim-msg ${type}`;
}