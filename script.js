// Function to update the label when a file is picked
function updateFileName() {
    const fileInput = document.getElementById('evidenceFile');
    const display = document.getElementById('fileNameDisplay');
    if (fileInput.files.length > 0) {
        display.innerText = fileInput.files[0].name;
        display.classList.add('text-blue-600', 'font-medium');
    }
}

// ── FIR Proof Upload ────────────────────────────────────────────
let selectedProofFiles = [];

function renderProofFileList() {
    const input = document.getElementById('proofFileInput');
    selectedProofFiles = Array.from(input.files);
    const list = document.getElementById('proofFileList');

    list.innerHTML = selectedProofFiles.map((f, i) => `
        <div class="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 text-sm">
            <span class="truncate text-blue-700 font-medium">${f.name} (${(f.size/1024).toFixed(1)} KB)</span>
            <button type="button" onclick="removeProofFile(${i})" class="text-red-500 font-bold">×</button>
        </div>
    `).join('');
}

function removeProofFile(index) {
    selectedProofFiles.splice(index, 1);
    const dt = new DataTransfer();
    selectedProofFiles.forEach(f => dt.items.add(f));
    document.getElementById('proofFileInput').files = dt.files;
    renderProofFileList();
}

// Call this AFTER generateFIR() succeeds, passing the fir_no from the server response
async function uploadProofsForFIR(firNo) {
    if (!selectedProofFiles.length) return;

    for (const file of selectedProofFiles) {
        const fd = new FormData();
        fd.append('fir_no', firNo);
        fd.append('file', file);

        try {
            const res = await fetch('/upload-evidence', { method: 'POST', body: fd });
            const data = await res.json();
            if (!res.ok) console.error('Proof upload failed:', data.error);
        } catch (e) {
            console.error('Proof upload error:', e);
        }
    }
    selectedProofFiles = [];
    document.getElementById('proofFileList').innerHTML = '';
}

// NOTE: handleEvidenceUpload, updateFileLabel, loadEvidenceGrid, and loadEvidence
// are intentionally NOT defined here anymore — they live in the inline <script>
// block at the bottom of the HTML and are the versions actually wired to the
// Evidence Locker UI (they're FIR-scoped via ?fir_no=...). Duplicate stub
// versions previously here were dead code shadowed by the inline ones; removed
// to avoid drift/bugs if script load order ever changes.

function handleSearch() {
    const input = document.getElementById('userInput').value;
    if (input.trim() !== "") {
        // Here you would normally redirect or update the UI
        alert("Connecting to Nyaya AI for: " + input);

        /* In a real app, you would use:
        window.location.href = `chat.html?query=${encodeURIComponent(input)}`;
        */
    } else {
        alert("Please enter a legal query.");
    }
}

// Add Enter key support
document.getElementById('userInput')?.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        handleSearch();
    }
});

// ══════════════════════════════════════════════════════════════
// Law Browser Modal — IPC / CrPC section browser
// ══════════════════════════════════════════════════════════════
let lbData = [];
let lbFiltered = [];
let lbCurrentAct = '';
let lbPage = 1;
const LB_PAGE_SIZE = 20;
let lbSearchTimeout = null;

async function openLawBrowser(act) {
    lbCurrentAct = act;
    lbPage = 1;

    const searchEl = document.getElementById('lbSearch');
    if (searchEl) searchEl.value = '';

    document.getElementById('lbTitle').textContent =
        act === 'IPC' ? 'Indian Penal Code' : 'Criminal Procedure Code';
    document.getElementById('lbBadge').textContent = act;
    document.getElementById('lbList').innerHTML =
        '<div class="px-6 py-8 text-center text-slate-400">Loading…</div>';

    const modal = document.getElementById('lawBrowserModal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');

    try {
        const res = await fetch(`/api/sections/${act}?limit=1000&all=true`);
        if (!res.ok) throw new Error('Failed to load sections');
        const raw = await res.json();

        // Normalize whatever shape the API returns into a plain array
        if (Array.isArray(raw)) {
            lbData = raw;
        } else if (Array.isArray(raw.sections)) {
            lbData = raw.sections;
        } else if (Array.isArray(raw.data)) {
            lbData = raw.data;
        } else if (Array.isArray(raw.results)) {
            lbData = raw.results;
        } else {
            console.error('Unexpected /api/sections response shape:', raw);
            throw new Error('Unexpected response shape from /api/sections');
        }

        lbFiltered = lbData;
        lbRenderPage();
    } catch (err) {
        console.error('Law browser load error:', err);
        document.getElementById('lbList').innerHTML =
            '<div class="px-6 py-8 text-center text-red-500">Failed to load sections.</div>';
    }
}

function closeLawBrowser() {
    const modal = document.getElementById('lawBrowserModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

function debouncedSearch() {
    clearTimeout(lbSearchTimeout);
    lbSearchTimeout = setTimeout(() => {
        const q = (document.getElementById('lbSearch').value || '').trim().toLowerCase();
        lbFiltered = !q
            ? lbData
            : lbData.filter(s =>
                String(s.section).toLowerCase().includes(q) ||
                (s.title || '').toLowerCase().includes(q)
            );
        lbPage = 1;
        lbRenderPage();
    }, 300);
}

function lbRenderPage() {
    const listEl = document.getElementById('lbList');
    const total = lbFiltered.length;
    const totalPages = Math.max(1, Math.ceil(total / LB_PAGE_SIZE));
    lbPage = Math.min(lbPage, totalPages);

    const start = (lbPage - 1) * LB_PAGE_SIZE;
    const pageItems = lbFiltered.slice(start, start + LB_PAGE_SIZE);

    document.getElementById('lbTotal').textContent = `${total} sections`;

    listEl.innerHTML = pageItems.length
        ? pageItems.map(s => `
            <div class="px-6 py-3 hover:bg-blue-50 cursor-pointer" onclick="lbShowDetail('${escapeHtml(String(s.section))}')">
                <span class="font-bold text-blue-700">Section ${escapeHtml(String(s.section))}</span>
                <span class="text-slate-600 ml-2">${escapeHtml(s.title || '')}</span>
            </div>`).join('')
        : '<div class="px-6 py-8 text-center text-slate-400">No matching sections.</div>';

    document.getElementById('lbPageInfo').textContent = `Page ${lbPage} of ${totalPages}`;
    document.getElementById('lbPrev').disabled = lbPage <= 1;
    document.getElementById('lbNext').disabled = lbPage >= totalPages;
}

function lbChangePage(delta) {
    lbPage += delta;
    lbRenderPage();
}

async function lbShowDetail(section) {
    const listEl = document.getElementById('lbList');
    const footerPageInfo = document.getElementById('lbPageInfo');
    const prevBtn = document.getElementById('lbPrev');
    const nextBtn = document.getElementById('lbNext');
    const searchEl = document.getElementById('lbSearch');

    // Hide list controls while showing detail
    if (searchEl) searchEl.parentElement.classList.add('hidden');
    if (footerPageInfo) footerPageInfo.classList.add('hidden');
    if (prevBtn) prevBtn.classList.add('hidden');
    if (nextBtn) nextBtn.classList.add('hidden');

    listEl.innerHTML = `
        <div class="px-6 py-8 text-center text-slate-400">
            <div class="inline-block w-6 h-6 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin"></div>
            <p class="mt-3 text-sm">Loading section detail…</p>
        </div>`;

    try {
        const res = await fetch(`/api/section-detail/${lbCurrentAct}/${encodeURIComponent(section)}`);
        const data = await res.json();

        if (!res.ok) {
            listEl.innerHTML = `
                <div class="px-6 py-8 text-center text-red-500">
                    Could not load Section ${escapeHtml(section)}.
                </div>
                <div class="px-6 pb-6 text-center">
                    <button onclick="lbBackToList()"
                        class="px-4 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-50 rounded-lg transition">
                        ← Back to list
                    </button>
                </div>`;
            return;
        }

        listEl.innerHTML = `
            <div class="px-6 py-6">
                <button onclick="lbBackToList()"
                    class="mb-4 text-sm font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1 transition">
                    ← Back to list
                </button>
                <div class="bg-blue-50 border border-blue-100 rounded-xl p-5">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="text-xs font-bold bg-blue-600 text-white px-2 py-0.5 rounded-full">${escapeHtml(lbCurrentAct)}</span>
                        <span class="font-bold text-blue-900 text-lg">Section ${escapeHtml(section)}</span>
                    </div>
                    <p class="font-semibold text-slate-800 mb-3">${escapeHtml(data.title || '')}</p>
                    <p class="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">${escapeHtml(data.description || 'No description available.')}</p>
                </div>
            </div>`;
    } catch (err) {
        console.error('Section detail error:', err);
        listEl.innerHTML = `
            <div class="px-6 py-8 text-center text-red-500">
                Failed to load section detail.
            </div>
            <div class="px-6 pb-6 text-center">
                <button onclick="lbBackToList()"
                    class="px-4 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-50 rounded-lg transition">
                    ← Back to list
                </button>
            </div>`;
    }
}

function lbBackToList() {
    const footerPageInfo = document.getElementById('lbPageInfo');
    const prevBtn = document.getElementById('lbPrev');
    const nextBtn = document.getElementById('lbNext');
    const searchEl = document.getElementById('lbSearch');

    if (searchEl) searchEl.parentElement.classList.remove('hidden');
    if (footerPageInfo) footerPageInfo.classList.remove('hidden');
    if (prevBtn) prevBtn.classList.remove('hidden');
    if (nextBtn) nextBtn.classList.remove('hidden');

    lbRenderPage();
}

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('lawBrowserModal');
    modal?.addEventListener('click', function (e) {
        if (e.target === this) closeLawBrowser();
    });
});