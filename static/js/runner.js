export class RunnerAnalyses {
    constructor({
        status="",
        race_id = 0,
        runner_splits = {},
        analyses = {}
    } = {}) {
        this.#validateInputs(analyses);

        this.status = status;
        this.race_id = race_id;
        this.runner_splits = runner_splits;
        this.analyses = analyses;
    }

    #validateInputs(analyses) {
        if (analyses.status === "failed") {
            throw new Error(analyses.error || 'Analysis failed');
        }
    }
}

export class Runners {
    allRunners = [];
    #selectedRunners = [];
    runnerSelectionAction = () => {};
    #eventListenersSet = false;

    /**
     * Get currently selected runners.
     * @returns {Array[Number]} - Array of selected runner IDs.
     */
    get selectedRunners() {
        return this.#selectedRunners;
    }

    /**
     * Select or deselect a runner for analysis.
     * @param {number} runnerId - ID of the runner to select/deselect.
     * @returns {void}
     */
    set selectedRunners(runnerId) {
        this.#selectRunner(runnerId);
    }

    /**
     * Internal method to handle runner selection logic.
     * @param {number} runnerId - ID of the runner to select/deselect.
     * @returns {void}
     */
    #selectRunner(runnerId) {
        const card = document.querySelector(`[data-runner-id="${runnerId}"]`);
        
        if (this.#selectedRunners.includes(runnerId)) {
            // Remove from selection
            this.#selectedRunners = this.#selectedRunners.filter(id => id !== runnerId);
            card.classList.remove('selected');
        } else {
            // Add to selection (limit to 5)
            if (this.#selectedRunners.length < 5) {
                this.#selectedRunners.push(runnerId);
                card.classList.add('selected');
            } else {
                alert('Maximum 5 runners can be selected for comparison');
                return;
            }
        }

        // Trigger any additional actions on selection change
        this.runnerSelectionAction();
    }

    /**
     * Load runners from the server and display them.
     * @returns {void}
     */
    loadRunners() {
        fetch('/api/runners')
            .then(response => response.json())
            .then(data => {
                this.allRunners = data;
                this.displayRunners(data);
            })
            .catch(error => {
                console.error('Error loading runners:', error);
            });
    }

    /**
     * Display runners as cards in the UI.
     * @returns {void}
     */
    displayRunners() {
        const container = document.getElementById('runnerResults');
        
        if (this.allRunners.length === 0) {
            container.innerHTML = '<div class="col-12 text-center text-muted">No runners found</div>';
            return;
        }

        const cardsHtml = this.allRunners.map(runner => `
            <div class="col-md-4 col-lg-3 mb-3">
                <div class="card runner-card h-100" data-runner-id="${runner.id}" 
                    <div class="card-body p-3">
                        <div class="d-flex justify-content-between mb-2">
                            <strong>${runner.first_name} ${runner.last_name}</strong>
                            <span class="badge bg-secondary">${runner.place || 'N/A'}</span>
                        </div>
                        <div class="small text-muted">
                            <div><i class="fas fa-id-badge"></i> Bib ${runner.bib_number || 'N/A'}</div>
                            <div><i class="fas fa-clock"></i> ${runner.finish_time || 'DNF'}</div>
                        </div>
                        <div class="small text-muted mt-1">
                            ${runner.city ? runner.city : ''}${runner.city && (runner.state || runner.country) ? ', ' : ''}${runner.state || (runner.country === 'USA' ? 'USA' : runner.country || '')}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = cardsHtml;

        // Add event delegation for runner card clicks
        if (!this.#eventListenersSet) {
            container.addEventListener('click', (event) => {
                const card = event.target.closest(`[data-runner-id]`);
                if (card) {
                    const runnerId = parseInt(card.dataset.runnerId);
                    this.#selectRunner(runnerId);
                }
            });

            this.#eventListenersSet = true;
        }
        
        // Restore selected state for previously selected runners
        this.#selectedRunners.forEach(runnerId => {
            const card = document.querySelector(`[data-runner-id="${runnerId}"]`);
            if (card) {
                card.classList.add('selected');
            }
        });
    }

    /**
     * Filter runners based on search input.
     * @returns {void}
     */
    filterRunners() {
        const searchTerm = document.getElementById('searchInput').value.toLowerCase();
        
        if (!searchTerm) {
            displayRunners(this.allRunners);
            return;
        }

        const filtered = this.allRunners.filter(runner => {
            const matchesSearch = !searchTerm || 
                (runner.first_name && runner.first_name.toLowerCase().includes(searchTerm)) ||
                (runner.last_name && runner.last_name.toLowerCase().includes(searchTerm)) ||
                (runner.city && runner.city.toLowerCase().includes(searchTerm)) ||
                (runner.state && runner.state.toLowerCase().includes(searchTerm)) ||
                (runner.country && runner.country.toLowerCase().includes(searchTerm)) ||
                (runner.bib_number && runner.bib_number.toString().includes(searchTerm)) ||
                (`${runner.first_name} ${runner.last_name}`.toLowerCase().includes(searchTerm)) ||
                (`${runner.city}, ${runner.state || (runner.country === 'USA' ? 'USA' : runner.country)}`.toLowerCase().includes(searchTerm));
                
            return matchesSearch;
        });

        displayRunners(filtered);
    }

    /**
     * Clear all selected runners and update UI.
     * @returns {void}
     */
    clearSelections() {
        this.#selectedRunners = [];

        // Clear selected class from all cards
        document.querySelectorAll('.runner-card.selected').forEach(card => {
            card.classList.remove('selected');
        });

        // Trigger any additional actions on selection change
        this.runnerSelectionAction();
    }
}