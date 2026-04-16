// static/js/script.js

let lastMatrix = null;

// --- Dark Mode Toggle ---
document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.getElementById('dark-mode-toggle');
    const body = document.body;
    // Check localStorage for mode
    const darkMode = localStorage.getItem('darkMode');
    if (darkMode !== 'disabled') {
        body.classList.add('dark-mode');
        if (toggleBtn) toggleBtn.innerHTML = '☀️';
    } else {
        if (toggleBtn) toggleBtn.innerHTML = '🌙';
    }
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            body.classList.toggle('dark-mode');
            const enabled = body.classList.contains('dark-mode');
            if (enabled) {
                localStorage.setItem('darkMode', 'enabled');
                toggleBtn.innerHTML = '☀️';
            } else {
                localStorage.setItem('darkMode', 'disabled');
                toggleBtn.innerHTML = '🌙';
            }
        });
    }
});

function runLogic() {
    // 1. Reference UI elements
    const btn = document.getElementById('run-btn');
    const stateRadio = document.querySelector('input[name="state"]:checked');
    const state = stateRadio ? stateRadio.value : 'Bell';
    const number = document.getElementById('number').value;
    const trials = document.getElementById('trials').value;
    const resultsDiv = document.getElementById('results');
    const resNum = document.getElementById('res-num');
    const resMatrix = document.getElementById('res-matrix');
    const resPlot = document.getElementById('res-plot');
    const progressBars = document.getElementById('progress-bars');
    const barItr = document.getElementById('progress-bar-itr');
    const barTrials = document.getElementById('progress-bar-trials');
    const labelItr = document.getElementById('progress-label-itr');
    const labelTrials = document.getElementById('progress-label-trials');

    // 2. UI Feedback: Disable button and show progress bars at 0%
    btn.innerText = "Running…";
    btn.disabled = true;
    progressBars.style.display = 'flex';
    progressBars.classList.add('is-running');
    barItr.style.width = '0%';
    barTrials.style.width = '0%';
    labelItr.innerText = '';
    labelTrials.innerText = '';

    let lastProgress = null;

    const params = new URLSearchParams({ state, number, trials });
    const es = new EventSource(`/run-stream?${params}`);

    es.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.type === 'progress') {
            barItr.style.width = Math.min(100, Math.round((data.itr / data.max_iter) * 100)) + '%';
            barTrials.style.width = Math.min(100, Math.round((data.trials / data.max_trials) * 100)) + '%';
            labelItr.innerText = `${data.itr} / ${data.max_iter}`;
            labelTrials.innerText = `${data.trials} / ${data.max_trials}`;
            lastProgress = data;

        } else if (data.type === 'done') {
            es.close();

            // 4. Update the Value
            resNum.innerText = data.number;

            // 5. Build and Inject the Matrix Table
            lastMatrix = data.matrix;
            resMatrix.innerHTML = formatMatrix(data.matrix);

            // 6. Display the Plot
            resPlot.src = `data:image/png;base64,${data.plot}`;

            // 7. Reveal the results section via CSS transition
            resultsDiv.classList.add('results--visible');

            // 8. Reset button state
            btn.innerText = "Run Analysis";
            btn.disabled = false;
            barItr.style.width = '100%';
            barTrials.style.width = '100%';
            progressBars.classList.remove('is-running');
            if (lastProgress) {
                labelItr.innerText = `${lastProgress.max_iter} / ${lastProgress.max_iter}`;
                labelTrials.innerText = `${lastProgress.max_trials} / ${lastProgress.max_trials}`;
            }
            setTimeout(() => { progressBars.style.display = 'none'; }, 400);

        } else if (data.type === 'error') {
            es.close();
            console.error("Error running find_css:", data.message);
            alert("Execution failed: " + data.message);
            btn.innerText = "Run Analysis";
            btn.disabled = false;
            progressBars.classList.remove('is-running');
            progressBars.style.display = 'none';
        }
    };

    es.onerror = function() {
        es.close();
        console.error("SSE connection error");
        alert("Execution failed. Check the console for details.");
        btn.innerText = "Run Analysis";
        btn.disabled = false;
        progressBars.classList.remove('is-running');
        progressBars.style.display = 'none';
    };
}

/**
 * Downloads the last computed CSS matrix as a CSV file.
 * Each cell is formatted as "re+imi" (standard complex notation).
 */
function downloadMatrixCSV() {
    if (!lastMatrix) return;

    const rows = lastMatrix.map(row =>
        row.map(([re, im]) => {
            const sign = im < 0 ? '-' : '+';
            return `${re.toFixed(6)}${sign}${Math.abs(im).toFixed(6)}i`;
        }).join(',')
    );
    const csv = rows.join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'css_matrix.csv';
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * Helper: Converts a 2D array into a clean HTML table.
 * Each cell is a [re, im] pair from the backend.
 */
function formatMatrix(matrix) {
    if (!matrix || !matrix.length) return "No matrix data returned.";

    let tableHtml = '<table class="matrix-table">';
    matrix.forEach(row => {
        tableHtml += '<tr>';
        row.forEach(([re, im]) => {
            const reStr = re.toFixed(6);
            const sign = im < 0 ? '−' : '+';
            const imStr = Math.abs(im).toFixed(6);
            tableHtml += `<td>${reStr} ${sign} ${imStr}i</td>`;
        });
        tableHtml += '</tr>';
    });
    tableHtml += '</table>';

    return tableHtml;
}