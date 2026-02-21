// Repo2Dataset Web UI - Frontend Logic

class DatasetGenerator {
    constructor() {
        this.currentJobId = null;
        this.pollInterval = null;

        // DOM elements
        this.repoUrlInput = document.getElementById('repo_url');
        this.outputNameInput = document.getElementById('output_name');
        this.startBtn = document.getElementById('start_btn');
        this.resetBtn = document.getElementById('reset_btn');
        this.statusContainer = document.getElementById('status_container');
        this.progressSection = document.getElementById('progress_section');
        this.statusText = document.getElementById('status_text');
        this.progressPercent = document.getElementById('progress_percent');
        this.progressFill = document.getElementById('progress_fill');
        this.logsOutput = document.getElementById('logs_output');
        this.copyLogsBtn = document.getElementById('copy_logs_btn');
        this.resultsSection = document.getElementById('results_section');

        // Initialize
        this.bindEvents();
    }

    bindEvents() {
        this.startBtn.addEventListener('click', () => this.startJob());
        this.resetBtn.addEventListener('click', () => this.resetUI());
        this.copyLogsBtn.addEventListener('click', () => this.copyLogs());
    }

    async startJob() {
        const repoUrl = this.repoUrlInput.value.trim();

        if (!repoUrl) {
            this.showError('Please enter a GitHub repository URL');
            return;
        }

        if (!repoUrl.startsWith('https://github.com/')) {
            this.showError('Please enter a valid GitHub repository URL (must start with https://github.com/)');
            return;
        }

        try {
            this.startBtn.disabled = true;
            this.startBtn.textContent = 'Starting...';

            const outputName = this.outputNameInput.value.trim() || null;
            const options = this.getOptions();

            const response = await fetch('/api/jobs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    repo_url: repoUrl,
                    output_name: outputName,
                    options: options,
                }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to start job');
            }

            const data = await response.json();
            this.currentJobId = data.job_id;

            // Update UI for running job
            this.startBtn.style.display = 'none';
            this.resetBtn.style.display = 'inline-flex';
            this.disableForm(true);
            this.pollInterval = setInterval(() => this.pollJob(), 1000);

            // Initial status update
            this.updateStatus('running', 'Job started...');
            this.showProgressSection();

        } catch (error) {
            this.showError(error.message);
            this.startBtn.disabled = false;
            this.startBtn.textContent = 'Start Generation';
        }
    }

    async pollJob() {
        if (!this.currentJobId) return;

        try {
            const response = await fetch(`/api/jobs/${this.currentJobId}`);

            if (!response.ok) {
                throw new Error('Failed to fetch job status');
            }

            const job = await response.json();

            // Update progress
            this.updateProgress(job.progress);

            // Update status text
            this.updateStatus(job.state, job.state.charAt(0).toUpperCase() + job.state.slice(1));

            // Update logs
            this.updateLogs(job.logs);

            // Handle job completion
            if (job.state === 'done') {
                clearInterval(this.pollInterval);
                this.showResults(job);
            } else if (job.state === 'error') {
                clearInterval(this.pollInterval);
                this.showError(job.error_message || 'Job failed');
            }

        } catch (error) {
            console.error('Polling error:', error);
        }
    }

    async showResults(job) {
        // Fetch detailed results
        try {
            const response = await fetch(`/api/jobs/${this.currentJobId}/result`);

            if (!response.ok) {
                throw new Error('Failed to fetch job results');
            }

            const result = await response.json();

            // Update stats
            document.getElementById('stat_total').textContent = result.counts.total || 0;
            document.getElementById('stat_train').textContent = result.counts.train || 0;
            document.getElementById('stat_valid').textContent = result.counts.valid || 0;

            document.getElementById('repo_sha').textContent = result.sha || '-';
            document.getElementById('output_dir').textContent = result.output_dir || '-';

            // Show results section
            this.resultsSection.style.display = 'block';

            // Scroll to results
            this.resultsSection.scrollIntoView({ behavior: 'smooth' });

        } catch (error) {
            this.showError('Failed to load job results: ' + error.message);
        }
    }

    updateStatus(state, message) {
        // Remove all status classes
        this.statusText.className = '';

        // Add appropriate class
        this.statusText.classList.add(`status-${state}`);
        this.statusText.textContent = message;
    }

    updateProgress(percent) {
        this.progressPercent.textContent = `${percent}%`;
        this.progressFill.style.width = `${percent}%`;
    }

    updateLogs(logs) {
        if (!logs || logs.length === 0) return;

        // Show only last 200 logs
        const recentLogs = logs.slice(-200);
        this.logsOutput.textContent = recentLogs.join('\n');

        // Auto-scroll to bottom
        const logsContainer = document.getElementById('logs_container');
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }

    showError(message) {
        this.statusContainer.innerHTML = `
            <div class="status-message error">
                <p style="color: var(--danger);">❌ Error: ${message}</p>
            </div>
        `;

        // Add to logs
        this.logsOutput.textContent += `\n[ERROR] ${message}`;
    }

    showProgressSection() {
        this.progressSection.style.display = 'block';
        this.statusContainer.innerHTML = `
            <div class="status-message">
                <p>Job ID: <code>${this.currentJobId}</code></p>
            </div>
        `;
    }

    copyLogs() {
        const logsText = this.logsOutput.textContent;

        if (!logsText) {
            alert('No logs to copy');
            return;
        }

        navigator.clipboard.writeText(logsText).then(() => {
            this.copyLogsBtn.textContent = 'Copied!';
            setTimeout(() => {
                this.copyLogsBtn.textContent = 'Copy Logs';
            }, 2000);
        }).catch(err => {
            alert('Failed to copy logs: ' + err.message);
        });
    }

    disableForm(disabled) {
        // Disable all form inputs
        const inputs = document.querySelectorAll('.config-panel input');
        inputs.forEach(input => {
            input.disabled = disabled;
        });

        // Disable advanced options toggle
        const details = document.querySelector('.advanced-options');
        if (disabled) {
            details.style.pointerEvents = 'none';
            details.style.opacity = '0.7';
        } else {
            details.style.pointerEvents = 'auto';
            details.style.opacity = '1';
        }
    }

    resetUI() {
        // Clear current job
        this.currentJobId = null;
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }

        // Reset buttons
        this.startBtn.style.display = 'inline-flex';
        this.startBtn.disabled = false;
        this.startBtn.textContent = 'Start Generation';
        this.resetBtn.style.display = 'none';

        // Enable form
        this.disableForm(false);

        // Clear logs and progress
        this.logsOutput.textContent = '';
        this.updateProgress(0);
        this.updateStatus('running', 'Ready');

        // Hide sections
        this.progressSection.style.display = 'none';
        this.resultsSection.style.display = 'none';

        // Reset status container
        this.statusContainer.innerHTML = `
            <div class="status-message">
                <p>Configure your repository and click "Start Generation" to begin.</p>
            </div>
        `;

        // Clear form inputs (except repo URL for convenience)
        this.outputNameInput.value = '';
    }

    getOptions() {
        return {
            allow_llm: document.getElementById('allow_llm').checked,
            max_tokens: parseInt(document.getElementById('max_tokens').value) || 4096,
            min_tokens: parseInt(document.getElementById('min_tokens').value) || 48,
            file_cap: parseInt(document.getElementById('file_cap').value) || 15,
            md_max_questions_per_section: parseInt(document.getElementById('md_max_questions').value) || 4,
            md_window_tokens: parseInt(document.getElementById('md_window_tokens').value) || 800,
            py_chunking: document.getElementById('py_chunking').checked,
            py_chunk_max: parseInt(document.getElementById('py_chunk_max').value) || 5,
            py_chunk_min_lines: parseInt(document.getElementById('py_chunk_min_lines').value) || 6,
            include_validation: document.getElementById('include_validation').checked,
            include_errors: document.getElementById('include_errors').checked,
            include_config: document.getElementById('include_config').checked,
            include_logging: document.getElementById('include_logging').checked,
        };
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new DatasetGenerator();
});