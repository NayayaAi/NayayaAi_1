// Function to update the label when a file is picked
function updateFileName() {
    const fileInput = document.getElementById('evidenceFile');
    const display = document.getElementById('fileNameDisplay');
    if (fileInput.files.length > 0) {
        display.innerText = fileInput.files[0].name;
        display.classList.add('text-blue-600', 'font-medium');
    }
}

// Function to handle the actual upload
async function handleEvidenceUpload(event) {
    event.preventDefault(); // must be first — stops native submit no matter what happens after

    const firNo = document.getElementById('evidenceFirNo')?.value
               || event.target.querySelector('[name="fir_no"]')?.value;
    const fileInput = document.getElementById('evidenceFileInput')
               || event.target.querySelector('[name="file"]');

    if (!firNo || !fileInput?.files?.length) {
        alert("Please provide both an FIR number and a file.");
        return false;
    }

    const formData = new FormData();
    formData.append('fir_no', firNo);
    formData.append('file', fileInput.files[0]);

    try {
        const response = await fetch('/upload-evidence', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            alert("Upload failed: " + (result.error || "Unknown error"));
            return false;
        }

        alert("Evidence successfully secured in locker.");
        fileInput.value = "";
        const label = document.getElementById('selectedFileLabel');
        if (label) label.classList.add('hidden');
        loadEvidence();
    } catch (error) {
        console.error("Upload error:", error);
        alert("Something went wrong uploading the file. Check the console for details.");
    }

    return false; // belt-and-braces, in case preventDefault didn't stick
}


function updateFileLabel(input) {
    const label = document.getElementById('selectedFileLabel');
    const nameSpan = document.getElementById('selectedFileName');
    if (input.files.length > 0) {
        nameSpan.textContent = input.files[0].name;
        label.classList.remove('hidden');
    } else {
        label.classList.add('hidden');
    }
}

function loadEvidenceGrid() {
    return loadEvidence();
}


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

async function loadEvidence() {
    try {
        const res = await fetch('/api/evidence');
        const data = await res.json();

        const grid = document.getElementById('evidenceGrid');
        const empty = document.getElementById('evidenceEmptyState');

        grid.innerHTML = '';

        if (!data.length) {
            empty.classList.remove('hidden');
            return;
        }

        empty.classList.add('hidden');

        data.forEach(file => {
            grid.innerHTML += `
                <div class="bg-slate-50 p-3 rounded border">
                    <p class="text-xs truncate">${file.name}</p>
                    <a href="${file.url}" target="_blank"
                       class="text-blue-500 text-xs font-bold">
                       VIEW
                    </a>
                </div>
            `;
        });

    } catch (err) {
        console.error("Failed to load evidence", err);
    }
}