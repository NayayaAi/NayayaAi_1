// Judge Portal — Orders & Drafts. Depends on globals from judge_dashboard.html: escapeHtml, API_BASE, lucide.
const ORDER_TYPES = ["Bail Order", "Adjournment Order", "Summons", "Notice", "Interim Order",
    "Remand Order", "Warrant", "Charge Order", "Final Judgment", "Custom"];
let editingOrder = null;   // order object being edited, or null for new

function ordMsg(text, ok = false) {
    const el = document.getElementById("ordMsg");
    el.textContent = text || "";
    el.className = "text-sm " + (text ? (ok ? "text-green-600" : "text-red-500") : "hidden");
}

async function loadOrders() {
    const el = document.getElementById("ordList");
    const status = document.getElementById("ordFilter").value;
    try {
        const res = await fetch("/judge/orders" + (status ? `?status=${status}` : ""));
        const rows = await res.json();
        window._orders = rows;
        if (!rows.length) {
            el.innerHTML = `<div class="px-6 py-10 text-center text-slate-400 text-sm">No orders yet. Click “New Order”.</div>`;
            return;
        }
        el.innerHTML = rows.map(o => `
            <div class="px-6 py-4 flex items-center justify-between hover:bg-slate-50">
                <div class="min-w-0">
                    <p class="font-semibold text-slate-800 truncate">${escapeHtml(o.title)}</p>
                    <p class="text-xs text-slate-400 mt-1">
                        <span class="font-mono text-blue-700">${escapeHtml(o.case_id)}</span> ·
                        ${escapeHtml(o.order_type)} · updated ${escapeHtml((o.updated_at || "").slice(0, 16).replace("T", " "))}
                        ${o.ai_generated ? " · ✨ AI-assisted" : ""}
                    </p>
                </div>
                <div class="flex items-center gap-3 shrink-0">
                    <span class="px-2.5 py-1 rounded-full text-xs font-bold ${o.status === "finalised" ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}">${escapeHtml(o.status)}</span>
                    <button onclick="openOrderEditor(${o.id})" class="text-blue-700 hover:underline text-sm font-semibold">${o.status === "finalised" ? "View" : "Edit"}</button>
                </div>
            </div>`).join("");
    } catch {
        el.innerHTML = `<div class="px-6 py-8 text-center text-red-500 text-sm">Could not load orders.</div>`;
    }
}

async function openOrderEditor(id = null) {
    editingOrder = id ? (window._orders || []).find(o => o.id === id) : null;
    ordMsg("");

    // Case dropdown from the judge's docket (unique case ids)
    const docket = await (await fetch(API_BASE)).json();
    const cases = [...new Set(docket.map(e => e.case_id))];
    const caseSel = document.getElementById("ordCase");
    caseSel.innerHTML = cases.length
        ? cases.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("")
        : `<option value="">No cases in docket</option>`;
    document.getElementById("ordType").innerHTML =
        ORDER_TYPES.map(t => `<option>${t}</option>`).join("");

    const o = editingOrder;
    if (o) { caseSel.value = o.case_id; document.getElementById("ordType").value = o.order_type; }
    document.getElementById("ordTitle").value = o ? o.title : "";
    document.getElementById("ordContent").value = o ? o.content : "";
    document.getElementById("ordInstructions").value = "";
    document.getElementById("ordEditorTitle").textContent = o ? (o.status === "finalised" ? "View Order" : "Edit Order") : "New Order";

    const locked = !!(o && o.status === "finalised");
    ["ordCase", "ordType", "ordTitle", "ordContent", "ordInstructions"].forEach(i =>
        document.getElementById(i).disabled = locked || (i === "ordCase" && !!o));
    document.getElementById("ordAiBox").classList.toggle("hidden", locked);
    document.getElementById("ordSaveBtn").classList.toggle("hidden", locked);
    document.getElementById("ordFinaliseBtn").classList.toggle("hidden", locked);
    document.getElementById("ordPdfBtn").classList.toggle("hidden", !o);
    document.getElementById("ordDeleteBtn").classList.toggle("hidden", !o || locked);

    const ed = document.getElementById("ordEditor");
    ed.classList.remove("hidden");
    ed.scrollIntoView({ behavior: "smooth", block: "start" });
}

function closeOrderEditor() {
    document.getElementById("ordEditor").classList.add("hidden");
    editingOrder = null;
}

async function generateOrderDraft() {
    const case_id = document.getElementById("ordCase").value;
    if (!case_id) return ordMsg("Select a case first.");
    const btn = document.getElementById("ordGenBtn");
    btn.disabled = true; btn.textContent = "Drafting…"; ordMsg("");
    try {
        const res = await fetch("/judge/orders/generate", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                case_id,
                order_type: document.getElementById("ordType").value,
                instructions: document.getElementById("ordInstructions").value,
            }),
        });
        const data = await res.json();
        if (!res.ok) return ordMsg(data.message || "Draft failed.");
        document.getElementById("ordContent").value = data.content;
        window._aiDrafted = true;
        ordMsg("Draft generated — review and edit before saving.", true);
    } catch { ordMsg("Network error."); }
    finally { btn.disabled = false; btn.textContent = "✨ Generate Draft"; }
}

async function saveOrder(finalise) {
    const content = document.getElementById("ordContent").value.trim();
    if (!content) return ordMsg("Order text is empty.");
    if (finalise && !confirm("Finalise this order? It can no longer be edited or deleted.")) return;

    const payload = {
        case_id: document.getElementById("ordCase").value,
        order_type: document.getElementById("ordType").value,
        title: document.getElementById("ordTitle").value,
        content,
    };
    if (!payload.case_id) return ordMsg("Select a case.");

    try {
        let res;
        if (editingOrder) {
            if (finalise) payload.status = "finalised";
            res = await fetch(`/judge/orders/${editingOrder.id}`, {
                method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        } else {
            payload.ai_generated = !!window._aiDrafted;
            res = await fetch("/judge/orders", {
                method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
            if (res.ok && finalise) {
                const created = await res.json();
                res = await fetch(`/judge/orders/${created.id}`, {
                    method: "PUT", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ status: "finalised" }) });
            }
        }
        const data = await res.json();
        if (!res.ok) return ordMsg(data.message || "Save failed.");
        window._aiDrafted = false;
        closeOrderEditor();
        loadOrders();
    } catch { ordMsg("Network error."); }
}

function downloadOrderPdf() {
    if (editingOrder) window.location.href = `/judge/orders/${editingOrder.id}/pdf`;
}

async function deleteOrder(id) {
    if (!confirm("Delete this draft?")) return;
    await fetch(`/judge/orders/${id}`, { method: "DELETE" });
    loadOrders();
}
