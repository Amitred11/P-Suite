// psuite/static/js/script.js
class UIUpdater {
    constructor() {
        this.form = document.querySelector('.tool-form');
        this.consoleOutput = document.getElementById('console-output');
        this.processingSection = document.getElementById('processing-section');
        this.resultsSection = document.getElementById('results-section');
        this.postRunActions = document.getElementById('post-run-actions');
    }

    addConsoleLine(message, type = 'info', isHTML = false) {
        if (!this.consoleOutput) return;
        const line = document.createElement('div');
        line.className = `console-line status-${type}`;
        
        const iconMap = {
            'success': 'fa-check-circle',
            'error': 'fa-times-circle',
            'warning': 'fa-exclamation-triangle',
            'info': 'fa-info-circle',
            'default': 'fa-chevron-right'
        };
        const iconClass = iconMap[type] || iconMap['default'];

        const iconHTML = `<span class="icon"><i class="fas ${iconClass}"></i></span>`;
        if (isHTML) {
            line.innerHTML = `${iconHTML}<div>${message}</div>`;
        } else {
            const messageSpan = document.createElement('span');
            messageSpan.textContent = message;
            line.appendChild(new DOMParser().parseFromString(iconHTML, 'text/html').body.firstChild);
            line.appendChild(messageSpan);
        }

        this.consoleOutput.appendChild(line);
        this.consoleOutput.scrollTop = this.consoleOutput.scrollHeight;
    }

    showProcessing() {
        if (this.form) this.form.style.display = 'none';
        if (this.processingSection) this.processingSection.style.display = 'block';
        if (this.resultsSection) this.resultsSection.style.display = 'none';
        if (this.postRunActions) this.postRunActions.style.display = 'none';
        if (this.consoleOutput) this.consoleOutput.innerHTML = '';
    }

    showResults(data) {
        if (this.resultsSection) {
            this.processingSection.style.display = 'none';
            this.resultsSection.style.display = 'block';

            const downloadBtn = this.resultsSection.querySelector('#download-all-btn');
            if(downloadBtn) downloadBtn.href = `/tools/download-all/${data.final_zip_name}`;
            
            this.renderFileTree(data.file_tree);
            this.renderSummaryReport(data.report);
        }
        if (this.postRunActions) this.postRunActions.style.display = 'flex';
    }
    
    showFinalConsole() {
        if (this.postRunActions) this.postRunActions.style.display = 'flex';
    }

    resetUI() {
        if (this.form) {
            this.form.style.display = 'block';
            this.form.reset();
            const submitButton = this.form.querySelector('button[type="submit"]');
            if(submitButton) submitButton.disabled = true;
            
            const dropZone = this.form.querySelector('.drop-zone');
            const fileDisplay = dropZone.querySelector('.file-list-display');
            const prompt = dropZone.querySelector('.drop-zone-prompt');

            if(fileDisplay) fileDisplay.classList.remove('visible');
            if(prompt) prompt.style.visibility = 'visible';
        }
        if (this.processingSection) this.processingSection.style.display = 'none';
        if (this.resultsSection) this.resultsSection.style.display = 'none';
        if (this.postRunActions) this.postRunActions.style.display = 'none';
    }

    updateCredits(credits) {
        const creditsDisplay = document.querySelector('.credits-display');
        if (creditsDisplay) {
            creditsDisplay.innerHTML = `<i class="fas fa-coins"></i> ${credits} Credits`;
        }
    }
    
    renderFileTree(fileTree) {
        const container = document.getElementById('file-tree-container');
        if (!container) return;
        
        const buildTree = (nodes, parentElement) => {
            const ul = document.createElement('ul');
            ul.className = 'file-tree';
            for (const node of nodes) {
                const li = document.createElement('li');
                const nodeDiv = document.createElement('div');
                nodeDiv.className = 'file-tree-node';
                
                const iconClass = node.type === 'directory' ? 'fas fa-folder' : 'fas fa-file-code';
                nodeDiv.innerHTML = `<i class="${iconClass}"></i><span>${node.name}</span>`;
                li.appendChild(nodeDiv);

                if (node.children && node.children.length > 0) {
                    buildTree(node.children, li);
                }
                ul.appendChild(li);
            }
            parentElement.appendChild(ul);
        };
        container.innerHTML = '';
        buildTree(fileTree, container);
    }
    
    renderSummaryReport(report) {
        const container = document.getElementById('report-summary-container');
        if (!container || !report) return;

        let itemsHTML = '';
        for (const [key, item] of Object.entries(report)) {
            let valueClass = '';
            if (item.type === 'positive') valueClass = 'positive';
            if (item.type === 'negative') valueClass = 'negative';

            itemsHTML += `
                <div class="summary-item">
                    <span class="summary-label">${item.label}</span>
                    <span class="summary-value ${valueClass}">${item.value}</span>
                </div>
            `;
        }
        
        container.innerHTML = `
            <div class="summary-report">
                <h4><i class="fas fa-chart-bar"></i> Optimization Summary</h4>
                ${itemsHTML}
            </div>
        `;
    }
}

class ToolHandler {
    constructor(formId, socketEventName, uiUpdater) {
        this.form = document.getElementById(formId);
        if (!this.form) return;

        this.socket = io();
        this.ui = uiUpdater;
        this.socketEventName = socketEventName;
        
        this.fileInput = this.form.querySelector('#file-input');
        this.dropZone = this.form.querySelector('#drop-zone');
        this.submitButton = this.form.querySelector('button[type="submit"]');
        
        this.init();
    }

    init() {
        this.setupFormSubmit();
        this.setupDragAndDrop();
        this.setupSocketListeners();
        this.setupRestartButton();
    }

    handleFiles(files) {
        const prompt = this.dropZone.querySelector('.drop-zone-prompt');
        let fileDisplay = this.dropZone.querySelector('.file-list-display');

        if (!fileDisplay) {
            fileDisplay = document.createElement('div');
            fileDisplay.className = 'file-list-display';
            this.dropZone.appendChild(fileDisplay);
        }

        if (!files.length || !files[0].name.toLowerCase().endsWith('.zip')) {
            alert('Please select a single ZIP file.');
            this.fileInput.value = '';
            this.submitButton.disabled = true;
            fileDisplay.classList.remove('visible');
            prompt.style.visibility = 'visible';
            return;
        }

        fileDisplay.innerHTML = `<i class="fas fa-file-archive"></i><p>${files[0].name}</p>`;
        fileDisplay.classList.add('visible');
        prompt.style.visibility = 'hidden';
        this.submitButton.disabled = false;
    }

    setupDragAndDrop() {
        if (!this.dropZone) return;
        this.dropZone.addEventListener('click', () => this.fileInput.click());
        this.dropZone.addEventListener('dragover', (e) => { e.preventDefault(); this.dropZone.classList.add('drag-over'); });
        this.dropZone.addEventListener('dragleave', () => this.dropZone.classList.remove('drag-over'));
        this.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('drag-over');
            if (e.dataTransfer.files.length) {
                this.fileInput.files = e.dataTransfer.files;
                this.handleFiles(e.dataTransfer.files);
            }
        });
        this.fileInput.addEventListener('change', () => this.handleFiles(this.fileInput.files));
    }
    
    setupFormSubmit() {
        this.form.addEventListener('submit', async (e) => {
            e.preventDefault();
            this.ui.showProcessing();
            this.ui.addConsoleLine('Uploading project ZIP file...', 'info');

            const formData = new FormData(this.form);
            try {
                const response = await fetch('/tools/upload', { method: 'POST', body: formData });
                const result = await response.json();

                if (!response.ok) throw new Error(result.error || 'Upload failed.');
                
                this.ui.addConsoleLine('Upload complete. Starting process...', 'success');
                
                const options = {};
                const formElements = this.form.elements;
                for(const element of formElements) {
                    if (element.name) {
                        if (element.type === 'checkbox') {
                            options[element.name] = element.checked;
                        } else if (element.type === 'radio') {
                            if (element.checked) {
                                options[element.name] = element.value;
                            }
                        }
                    }
                }

                this.socket.emit(this.socketEventName, { session_id: result.session_id, options });

            } catch (error) {
                this.ui.addConsoleLine(`Error: ${error.message}`, 'error');
                this.ui.resetUI();
            }
        });
    }

    setupSocketListeners() {
        this.socket.on('status_update', (data) => this.ui.addConsoleLine(data.message, data.type, data.is_html));
        
        this.socket.on('processing_error', (data) => {
            this.ui.addConsoleLine(`FATAL ERROR: ${data.message}`, 'error');
            this.ui.showFinalConsole();
        });
        
        this.socket.on('credits_updated', (data) => this.ui.updateCredits(data.credits));
        
        this.socket.on('processing_complete', (data) => this.ui.showResults(data));
        
        this.socket.on('analysis_complete', (data) => {
            this.ui.addConsoleLine(data.message || 'Analysis complete.', 'success');
            this.ui.showFinalConsole();
        });
    }

    setupRestartButton() {
        const restartButton = document.getElementById('restart-button');
        if (restartButton) {
            restartButton.addEventListener('click', () => {
                this.ui.resetUI();
            });
        }
    }
}

class PaymentModal {
    constructor() {
        this.modal = document.getElementById('payment-modal');
        if (!this.modal) return;
        
        this.closeBtn = document.getElementById('close-modal-btn');
        this.upgradeBtns = document.querySelectorAll('.upgrade-btn');
        this.modalPlanName = document.getElementById('modal-plan-name');
        this.summaryPlanName = document.getElementById('summary-plan-name');
        this.summaryPlanPrice = document.getElementById('summary-plan-price');
        
        this.init();
    }
    
    init() {
        this.upgradeBtns.forEach(btn => {
            btn.addEventListener('click', (e) => this.open(e.currentTarget));
        });
        this.closeBtn.addEventListener('click', () => this.close());
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.close();
            }
        });
    }
    
    open(btn) {
        const plan = btn.dataset.plan;
        const price = btn.dataset.price;
        
        this.modalPlanName.textContent = plan;
        this.summaryPlanName.textContent = plan;
        this.summaryPlanPrice.textContent = `$${price}`;
        
        this.modal.style.display = 'flex';
        setTimeout(() => this.modal.classList.add('visible'), 10);
    }
    
    close() {
        this.modal.classList.remove('visible');
        setTimeout(() => this.modal.style.display = 'none', 300);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const ui = new UIUpdater();

    if (document.getElementById('frontend-optimizer-form')) {
        new ToolHandler('frontend-optimizer-form', 'run_frontend_optimization', ui);
    }
    if (document.getElementById('backend-analyzer-form')) {
        new ToolHandler('backend-analyzer-form', 'run_backend_analysis', ui);
    }
    if (document.getElementById('security-scanner-form')) {
        new ToolHandler('security-scanner-form', 'run_security_scan', ui);
    }
    
    if (document.getElementById('payment-modal')) {
        new PaymentModal();
    }
});