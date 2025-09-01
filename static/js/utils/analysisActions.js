import { Runners } from '../runner.js';

export class AnalysisButton {
    constructor() {
        this.button = document.getElementById('runAnalysis');
    }

    /**
     * Update the analysis button state and label based on selected runners.
     * @param {Runners} runners - Instance of the Runners class.
     * @returns {void}
     */
    update(runners) {
        console.log(`Updating analysis button for ${runners.selectedRunners.length} selected runners`, this.button);
        this.button.disabled = runners.selectedRunners.length === 0;

        switch (runners.selectedRunners.length) {
            case 0:
                this.button.innerHTML = '<i class="fas fa-play"></i> Run Advanced Analysis';
                break;
            case 1:
                this.button.innerHTML = '<i class="fas fa-play"></i> Run Single Runner Analysis';
                break;
            default:
                this.button.innerHTML = `<i class="fas fa-play"></i> Compare ${runners.selectedRunners.length} Runners`;
        }
    }
}