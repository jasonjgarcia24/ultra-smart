import { RunnerAnalyses, Runners } from "./runner.js";

class BaseRunnerAnalysis {
    #runnerCount = 0;
    #singleDiv = document.getElementById('singleRunnerAnalysis');
    #multiDiv = document.getElementById('multiRunnerAnalysis');
    #fatigueSection = document.getElementById('fatigueProgressionSection');
    #courseSegmentSection = document.getElementById('courseSegmentPerformanceSection');
    #analysisRunnerName = document.getElementById('analysisRunnerName');
    #fatigueChart = document.getElementById('fatigueChart');

    runners = null;
    analyses = {};
    runners_splits = {};

    constructor(runnerCount) {
        this.#runnerCount = runnerCount;
    }

    init(analyses, runners) {
        this.#validateInputs(analyses, runners);

        this.runners = runners;
        this.analyses = analyses.analyses;
        this.runners_splits = analyses.runner_splits;

        this.#runnerCount = this.runners.selectedRunners.length;

        this.#singleDiv.style.display = 'block';
        this.#multiDiv.style.display = this.#isMulti() ? 'block' : 'none';
        this.#fatigueSection.style.display = this.#isMulti() ? 'block' : 'none';
        this.#fatigueChart.style.display = this.#isMulti() ? 'none' : 'block';
        this.#courseSegmentSection.style.display = 'block';

        const summaryCards = this.#singleDiv.querySelector('.row .col-12 .card .card-body .row');
        if (summaryCards) {
            summaryCards.style.display = this.#isMulti() ? 'none' : 'flex';
        }
    }

    #validateInputs(analyses, runners) {
        if (!runners.selectedRunners) {
            throw new Error(`Missing runner data: ${runners}`);
        }
        else if (analyses.status === "failed") {
            throw new Error(analyses.error || 'Analysis failed');
        }
    }

    /**
     * Select or deselect a runner for analysis.
     * @param {string} name - String containing header of analysis.
     * @returns {void}
     */
    _analysisRunnerName(name) {
        this.#analysisRunnerName.textContent = name;
    }

    #isMulti() {
        return this.#runnerCount > 1;
    }


    updateSegmentTable(courseSegments) {
        // Use the single-runner segment table but populate with multi-runner data
        const table = document.querySelector('#segmentTable');
        const thead = table?.querySelector('thead tr');
        const tbody = table?.querySelector('tbody');
        
        if (!table || !thead || !tbody) {
            console.error('Segment table elements not found');
            return;
        }
        
        if (!courseSegments || courseSegments.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${5 + this.runners.selectedRunners.length + 1}" class="text-center text-muted">No segment data available</td></tr>`;
            return;
        }
        
        // Update table header to show individual runner performance columns
        thead.innerHTML = `
            <th>Segment</th>
            <th>Miles</th>
            <th>Terrain</th>
            <th>Difficulty</th>
            <th>Avg Pace</th>
            ${this.runners.selectedRunners.map(runnerId => {
                const runner = this.runners.allRunners.find(r => r.id === runnerId);
                return `<th class="text-center">${runner ? `${runner.first_name} ${runner.last_name}` : `Runner ${runnerId}`}<br><small class="text-muted">Performance</small></th>`;
            }).join('')}
            <th>Elevation</th>
        `;
        
        // Create multi-runner segment comparison
        const html = courseSegments.map(segment => {
            // Calculate average pace across all runners for this segment
            const allPaces = [];
            this.runners.selectedRunners.forEach(runnerId => {
                const analysis = this.analyses[runnerId];
                const runnerSegment = analysis?.course_analysis?.segment_analysis?.find(
                    s => s.segment_name === segment.segment_name
                );
                if (runnerSegment && runnerSegment.average_pace > 0) {
                    allPaces.push(runnerSegment.average_pace);
                }
            });
            const avgPace = allPaces.length > 0 ? (allPaces.reduce((a, b) => a + b, 0) / allPaces.length) : 0;
            
            // Generate individual performance columns for each runner
            const runnerPerformanceCells = this.runners.selectedRunners.map(runnerId => {
                const analysis = this.analyses[runnerId];
                const runnerSegment = analysis?.course_analysis?.segment_analysis?.find(
                    s => s.segment_name === segment.segment_name
                );
                
                if (!runnerSegment || !runnerSegment.performance_score) {
                    return '<td class="text-center text-muted">N/A</td>';
                }
                
                const performanceScore = runnerSegment.performance_score;
                const percentage = Math.min(Math.max((performanceScore * 100), 0), 100).toFixed(0);
                const color = performanceScore > 0.8 ? 'success' : performanceScore > 0.6 ? 'warning' : 'danger';
                
                return `
                    <td class="text-center">
                        <div class="progress" style="height: 16px; width: 80px; margin: 0 auto;">
                            <div class="progress-bar bg-${color}" style="width: ${percentage}%">
                                <small>${percentage}%</small>
                            </div>
                        </div>
                    </td>
                `;
            }).join('');
            
            // Format elevation display to match single-runner format
            const gain = parseFloat(segment.elevation_gain_feet) || 0;
            const loss = parseFloat(segment.elevation_loss_feet) || 0;
            const net = parseFloat(segment.net_elevation_change_feet) || 0;
            
            let elevationDisplay;
            if (gain > 0 || loss > 0) {
                elevationDisplay = `<small>+${Math.round(gain)}ft / -${Math.round(loss)}ft<br>` +
                                    `Net: ${net >= 0 ? '+' : ''}${Math.round(net)}ft</small>`;
            } else {
                elevationDisplay = 'Flat';
            }
            
            return `
                <tr>
                    <td>${segment.segment_name}</td>
                    <td>${segment.start_mile.toFixed(1)} - ${segment.end_mile.toFixed(1)}</td>
                    <td><span class="badge bg-secondary">${segment.terrain_type}</span></td>
                    <td>
                        <span class="difficulty-stars" style="color: #ffc107;">
                            ${'★'.repeat(Math.round(segment.difficulty_rating))}
                        </span>
                    </td>
                    <td>${avgPace > 0 ? avgPace.toFixed(1) + ' min/mi' : 'N/A'}</td>
                    ${runnerPerformanceCells}
                    <td>${elevationDisplay}</td>
                </tr>
            `;
        }).join('');
        
        tbody.innerHTML = html;
    }

    createPaceElevationChart() {
        const canvas = document.getElementById('paceElevationChart');
        if (!canvas) {
            console.error('Pace elevation chart canvas not found');
            return;
        }

        const ctx = canvas.getContext('2d');
        
        // Clear any existing chart
        const existingChart = Chart.getChart(ctx);
        if (existingChart) {
            existingChart.destroy();
        }

        // Colors for runners
        const runnerColors = ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff'];
        
        // Build datasets for each runner's pace data
        const paceDatasets = [];
        const restPeriodDatasets = [];
        let maxPace = 0;
        let minPace = Infinity;
        
        this.runners.selectedRunners.forEach((runnerId, index) => {
            const analysis = this.analyses[runnerId];
            const splits = this.runners_splits[runnerId];
            const runner = this.runners.allRunners.find(r => r.id === runnerId);
            const color = runnerColors[index % runnerColors.length];
            
            if (!analysis || !analysis.fatigue_analysis || !analysis.fatigue_analysis.fatigue_progression) {
                return;
            }
            
            // Extract pace data from fatigue progression (fatigue factor * base pace estimate)
            const paceData = analysis.fatigue_analysis.fatigue_progression.map(point => ({
                x: point.mile,
                y: point.fatigue_factor * 12 // Approximate base pace of 12 min/mile
            }));

            const splitsData = splits.map(split => ({
                x: split.mile_number,
                y: split.pace_per_mile
            }));

            // Update max/min pace for chart scaling
            splitsData.forEach(d => {
                if (d.y > maxPace) { maxPace = d.y; }
                if (d.y < minPace) { minPace = d.y; }
            });
            
            paceDatasets.push({
                label: `${runner.first_name} ${runner.last_name} Pace`,
                data: splitsData,
                borderColor: color,
                backgroundColor: color + '20',
                borderWidth: 2,
                fill: false,
                tension: 0.1,
                pointRadius: 0,
                pointHoverRadius: 4,
                yAxisID: 'paceAxis'
            });
            
            // Add rest period markers
            const restPeriods = analysis?.rest_periods?.rest_periods || analysis?.rest_periods || [];
                            
            if (restPeriods.length > 0) {
                const restMarkers = restPeriods
                    .filter(rest => rest.mile || rest.start_mile)
                    .map(rest => ({
                        x: rest.mile || rest.start_mile,
                        y: (rest.estimated_rest_minutes || rest.duration_minutes || 0) + 10 // Offset above pace line
                    }));
                
                restPeriodDatasets.push({
                    label: `${runner.first_name} Rest Periods`,
                    data: restMarkers,
                    backgroundColor: color,
                    borderColor: color,
                    pointRadius: 6,
                    pointStyle: 'circle',
                    showLine: false,
                    yAxisID: 'paceAxis'
                });
            }
        });

        // Get elevation data from course segments or GPX data
        let elevationData = [];
        
        // Try to get elevation from first runner's course analysis
        const firstRunnerData = Object.values(this.analyses)[0];
        if (firstRunnerData?.course_analysis?.segment_analysis) {
            // Create elevation profile from segment data
            firstRunnerData.course_analysis.segment_analysis.forEach(segment => {
                elevationData.push(
                    { x: segment.start_mile, y: segment.start_elevation_feet || 3000 },
                    { x: segment.end_mile, y: segment.end_elevation_feet || 3000 }
                );
            });
        }
        
        // If no segment elevation data, create a simple elevation profile
        if (elevationData.length === 0) {
            // Basic elevation profile for Cocodona 250
            elevationData = [
                { x: 0, y: 2000 }, { x: 30, y: 4500 }, { x: 60, y: 5000 },
                { x: 90, y: 6000 }, { x: 120, y: 4000 }, { x: 150, y: 5500 },
                { x: 180, y: 6500 }, { x: 210, y: 7000 }, { x: 256, y: 7000 }
            ];
        }

        const elevationDataset = {
            label: 'Elevation Profile',
            data: elevationData,
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            borderColor: 'rgba(75, 192, 192, 0.5)',
            borderWidth: 1,
            fill: true,
            tension: 0.4,
            pointRadius: 0,
            yAxisID: 'elevationAxis'
        };

        // Create the chart
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [elevationDataset, ...paceDatasets, ...restPeriodDatasets]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            filter: function(item) {
                                // Only show pace lines and elevation in legend
                                return !item.text.includes('Rest Periods');
                            }
                        }
                    },
                    tooltip: {
                        mode: 'nearest',
                        callbacks: {
                            title: function(tooltipItems) {
                                if (tooltipItems.length > 0) {
                                    const xValue = tooltipItems[0].parsed.x;
                                    return `Mile ${xValue.toFixed(1)}`;
                                }
                                return '';
                            },
                            label: function(context) {
                                const xValue = context.parsed.x;
                                const yValue = context.parsed.y;
                                
                                if (context.dataset.yAxisID === 'elevationAxis') {
                                    return `Elevation: ${Math.round(yValue)}ft`;
                                } else if (context.dataset.label.includes('Rest Periods')) {
                                    return `Rest period: ${Math.round(yValue - 10)} minutes`;
                                } else {
                                    return `${context.dataset.label}: ${yValue.toFixed(1)} min/mi`;
                                }
                            },
                            filter: function(tooltipItem) {
                                // Only show tooltip for the closest dataset
                                return true;
                            }
                        }
                    },
                    zoom: {
                        zoom: {
                            wheel: {
                                enabled: true,
                            },
                            pinch: {
                                enabled: true
                            },
                            mode: 'xy',
                            scaleMode: 'xy'
                        },
                        pan: {
                            enabled: true,
                            mode: 'xy',
                            modifierKey: null
                        },
                        limits: {
                            x: {min: 0, max: 300},
                            paceAxis: {min: 5, max: 60},
                            elevationAxis: {min: 1000, max: 10000}
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'linear',
                        position: 'bottom',
                        title: {
                            display: true,
                            text: 'Distance (miles)'
                        },
                        ticks: {
                            callback: function(value, index, values) {
                                if (value % 25 === 0 && value > 0) return `Mile ${Math.round(value)}`;
                                else if (value === 0) return 'Start';
                                return '';
                            }
                        },
                        min: 0,
                        max: 260
                    },
                    xTop: {
                        type: 'linear',
                        position: 'top',
                        title: {
                            display: false
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                        afterBuildTicks: function(axis) {
                            // Use the aid stations from the CSV data
                            const aidStations = [
                                {mile: 0, name: "Start"}, {mile: 7.4, name: "Cottonwood"}, {mile: 32.5, name: "Lane Mtn"},
                                {mile: 36.6, name: "Crown King"}, {mile: 53, name: "Arrastra"}, {mile: 62.4, name: "Kamp Kipa"},
                                {mile: 69, name: "Wamatochick"}, {mile: 77.3, name: "Whiskey Row"}, {mile: 90.7, name: "Iron King"},
                                {mile: 95.9, name: "Fain Ranch"}, {mile: 108.3, name: "Mingus Mtn"}, {mile: 125.3, name: "Jerome"},
                                {mile: 134, name: "Dead Horse"}, {mile: 148, name: "Deer Pass"}, {mile: 162.3, name: "Sedona"},
                                {mile: 177.4, name: "Foxboro"}, {mile: 193.4, name: "Munds Park"}, {mile: 206, name: "Kelly Canyon"},
                                {mile: 214.4, name: "Fort Tuthill"}, {mile: 230.5, name: "Walnut Canyon"}, {mile: 237.3, name: "Wildcat Hill"},
                                {mile: 252.6, name: "Trinity Heights"}, {mile: 256.5, name: "Finish"}
                            ];
                            
                            axis.ticks = aidStations.map(station => ({
                                value: station.mile,
                                label: station.mile
                            }));
                        },
                        ticks: {
                            callback: function(value, index, values) {
                                // Find the aid station name for this mile
                                const aidStations = [
                                    {mile: 0, name: "Start"}, {mile: 7.4, name: "Cottonwood"}, {mile: 32.5, name: "Lane Mtn"},
                                    {mile: 36.6, name: "Crown King"}, {mile: 53, name: "Arrastra"}, {mile: 62.4, name: "Kamp Kipa"},
                                    {mile: 69, name: "Wamatochick"}, {mile: 77.3, name: "Whiskey Row"}, {mile: 90.7, name: "Iron King"},
                                    {mile: 95.9, name: "Fain Ranch"}, {mile: 108.3, name: "Mingus Mtn"}, {mile: 125.3, name: "Jerome"},
                                    {mile: 134, name: "Dead Horse"}, {mile: 148, name: "Deer Pass"}, {mile: 162.3, name: "Sedona"},
                                    {mile: 177.4, name: "Foxboro"}, {mile: 193.4, name: "Munds Park"}, {mile: 206, name: "Kelly Canyon"},
                                    {mile: 214.4, name: "Fort Tuthill"}, {mile: 230.5, name: "Walnut Canyon"}, {mile: 237.3, name: "Wildcat Hill"},
                                    {mile: 252.6, name: "Trinity Heights"}, {mile: 256.5, name: "Finish"}
                                ];
                                const station = aidStations.find(s => Math.abs(s.mile - value) < 0.5);
                                return station ? station.name : '';
                            },
                            maxRotation: 45,
                            minRotation: 45
                        },
                        min: 0,
                        max: 260
                    },
                    paceAxis: {
                        type: 'linear',
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Pace (min/mile)'
                        },
                        min: minPace < 5 ? Math.floor(minPace / 5) * 5 : 5,
                        max: maxPace > 30 ? Math.ceil(maxPace / 5) * 5 : 30,
                        suggestedMin: 5,
                        suggestedMax: 30
                    },
                    elevationAxis: {
                        type: 'linear',
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Elevation (feet)'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                        min: 2000,
                        max: 7500
                    }
                }
            }
        });
        
        // Add double-click to reset zoom functionality
        canvas.addEventListener('dblclick', function() {
            chart.resetZoom();
        });
    }
}

export class SingleRunnerAnalysis extends BaseRunnerAnalysis {
    #avgFatigue = document.getElementById('avgFatigue');
    #strongestTerrain = document.getElementById('strongestTerrain');
    #restPeriods = document.getElementById('restPeriods');

    constructor() { super(1); }

    /**
     * @param {RunnerAnalyses} analyses - Instance of the RunnerAnalyses class.
     * @param {Runners} runners - Instance of the Runners class.
     */
    init(analyses, runners) {
        super.init(analyses, runners);

        const runner = this.runners.allRunners.find(r => r.id === this.runners.selectedRunners[0]);
        const analysis = this.analyses[this.runners.selectedRunners[0]];
        const runner_splits = this.runners_splits[this.runners.selectedRunners[0]];

        // Update header
        this._analysisRunnerName(`${runner.first_name} ${runner.last_name}`);
        
        // Update summary stats
        this.#avgFatigue.textContent = analysis.fatigue_analysis?.average_fatigue?.toFixed(2) || 'N/A';
        this.#strongestTerrain.textContent = analysis.course_analysis?.strongest_terrain || 'N/A';
        this.#restPeriods.textContent = analysis.rest_periods?.rest_periods?.length || analysis.rest_periods?.length || 0;

        // Create fatigue chart with course segments
        this.#createFatigueChart(
            analysis.fatigue_analysis,
            analysis.course_analysis.segment_analysis
        );

        // Update tables
        this.updateSegmentTable(analysis.course_analysis.segment_analysis);
        this.#updateRestPeriodsList(analysis.rest_periods);
        this.#updateRecommendations(analysis.recommendations);

        // this.#updateMultiRunnerRestPeriods(); // , runner_splits);
    }

    #createFatigueChart(fatigueData, courseSegments) {
        if (!fatigueData || !fatigueData.fatigue_progression) {
            console.error('Invalid fatigue data for chart:', fatigueData);
            return;
        }
        
        const ctx = document.getElementById('fatigueChart').getContext('2d');
                
        // Clear any existing chart
        const existingChart = Chart.getChart(ctx);
        if (existingChart) {
            existingChart.destroy();
        }
        
        const progression = fatigueData.fatigue_progression;
        
        // Use dynamic course segments if provided, otherwise fall back to hardcoded
        let segments = [];
        if (courseSegments && courseSegments.length > 0) {
            // Create segments with two alternating soft colors
            const colors = [
                'rgba(173, 216, 230, 0.15)',  // Light blue
                'rgba(221, 221, 221, 0.15)'   // Light gray
            ];
            
            segments = courseSegments.map((segment, index) => ({
                name: segment.segment_name,
                start: segment.start_mile,
                end: segment.end_mile,
                color: colors[index % colors.length]
            }));
        } else {
            // Fallback to hardcoded segments with two alternating colors
            const colors = ['rgba(173, 216, 230, 0.15)', 'rgba(221, 221, 221, 0.15)'];
            segments = [
                {name: "Desert Start to Crown King", start: 0, end: 36.6, color: colors[0]},
                {name: "Crown King to Whiskey Row", start: 36.6, end: 77.3, color: colors[1]},
                {name: "Whiskey Row to Jerome", start: 77.3, end: 125.3, color: colors[0]},
                {name: "Jerome to Sedona Sleep Station", start: 125.3, end: 162.3, color: colors[1]},
                {name: "Sedona to Fort Tuthill Sleep", start: 162.3, end: 214.4, color: colors[0]},
                {name: "Fort Tuthill to Finish", start: 214.4, end: 256.5, color: colors[1]}
            ];
        }

        // Create aid station markers from segment data
        let aidStations = [];
        if (courseSegments && courseSegments.length > 0) {
            // Extract unique aid stations from segment start/end points
            const stationMiles = new Set();
            courseSegments.forEach(segment => {
                if (!stationMiles.has(segment.start_mile)) {
                    stationMiles.add(segment.start_mile);
                    // Extract station name from segment name (before " to ")
                    const startName = segment.segment_name.split(' to ')[0];
                    aidStations.push({
                        name: startName,
                        mile: segment.start_mile,
                        type: "aid",
                        sleep: false,
                        crew: false
                    });
                }
            });
            // Add the final station
            const lastSegment = courseSegments[courseSegments.length - 1];
            const endName = lastSegment.segment_name.split(' to ')[1];
            aidStations.push({
                name: endName,
                mile: lastSegment.end_mile,
                type: "aid",
                sleep: false,
                crew: false
            });
        } // No longer need fallback - using complete CSV data

        // Define custom plugin for segment backgrounds and aid station markers
        const segmentBackgroundPlugin = {
            id: 'segmentBackground',
            beforeDraw: (chart) => {
                const ctx = chart.ctx;
                const chartArea = chart.chartArea;
                const xScale = chart.scales.x;
                
                if (!xScale || !chartArea) return;
                
                // Draw segment backgrounds
                segments.forEach(segment => {
                    const startX = xScale.getPixelForValue(segment.start);
                    const endX = xScale.getPixelForValue(segment.end);
                    
                    if (startX >= chartArea.left && endX <= chartArea.right) {
                        ctx.save();
                        ctx.fillStyle = segment.color;
                        ctx.fillRect(startX, chartArea.top, endX - startX, chartArea.bottom - chartArea.top);
                        ctx.restore();
                    }
                });
            },
            afterDraw: (chart) => {
                const ctx = chart.ctx;
                const chartArea = chart.chartArea;
                const xScale = chart.scales.x;
                
                if (!xScale || !chartArea) return;
                
                // Draw aid station markers
                aidStations.forEach(station => {
                    const x = xScale.getPixelForValue(station.mile);
                    
                    if (x >= chartArea.left && x <= chartArea.right) {
                        ctx.save();
                        
                        const isWaterStation = station.type === 'water';
                        
                        // Draw vertical line
                        let strokeColor, lineWidth, dashPattern;
                        if (station.sleep) {
                            strokeColor = '#ff6b6b';
                            lineWidth = 3;
                            dashPattern = [];
                        } else if (isWaterStation) {
                            strokeColor = '#17a2b8';
                            lineWidth = 1;
                            dashPattern = [2, 4];
                        } else {
                            strokeColor = '#4ecdc4';
                            lineWidth = 2;
                            dashPattern = [5, 5];
                        }
                        
                        ctx.strokeStyle = strokeColor;
                        ctx.lineWidth = lineWidth;
                        ctx.setLineDash(dashPattern);
                        ctx.beginPath();
                        ctx.moveTo(x, chartArea.top);
                        ctx.lineTo(x, chartArea.bottom);
                        ctx.stroke();
                        
                        // Draw marker symbol
                        if (station.sleep) {
                            ctx.fillStyle = '#ff6b6b';
                            // Sleep station - diamond shape
                            ctx.beginPath();
                            ctx.moveTo(x, chartArea.top - 8);
                            ctx.lineTo(x + 6, chartArea.top - 2);
                            ctx.lineTo(x, chartArea.top + 4);
                            ctx.lineTo(x - 6, chartArea.top - 2);
                            ctx.closePath();
                            ctx.fill();
                        } else if (isWaterStation) {
                            ctx.fillStyle = '#17a2b8';
                            // Water station - small triangle
                            ctx.beginPath();
                            ctx.moveTo(x, chartArea.top - 4);
                            ctx.lineTo(x + 3, chartArea.top + 2);
                            ctx.lineTo(x - 3, chartArea.top + 2);
                            ctx.closePath();
                            ctx.fill();
                        } else {
                            ctx.fillStyle = '#4ecdc4';
                            // Regular aid station - circle
                            ctx.beginPath();
                            ctx.arc(x, chartArea.top - 2, 4, 0, 2 * Math.PI);
                            ctx.fill();
                        }
                        
                        ctx.restore();
                    }
                });
            }
        };

        new Chart(ctx, {
            type: 'line',
            plugins: [segmentBackgroundPlugin],
            data: {
                labels: progression.map(p => p.mile),
                datasets: [{
                    label: 'Fatigue Factor',
                    data: progression.map(p => p.fatigue_factor),
                    borderColor: 'rgb(255, 193, 7)',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    tension: 0.1,
                    pointRadius: 2,
                    pointHoverRadius: 4
                }, {
                    label: 'Terrain Difficulty',
                    data: progression.map(p => p.terrain_difficulty / 5), // Normalize to 0-1
                    borderColor: 'rgb(108, 117, 125)',
                    backgroundColor: 'rgba(108, 117, 125, 0.1)',
                    tension: 0.1,
                    yAxisID: 'y1',
                    pointRadius: 1,
                    pointHoverRadius: 3
                }]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        position: 'top',
                        onClick: function(e, legendItem, legend) {
                            const index = legendItem.datasetIndex;
                            const chart = legend.chart;
                            const meta = chart.getDatasetMeta(index);

                            // Toggle dataset visibility
                            meta.hidden = meta.hidden === null ? !chart.data.datasets[index].hidden : null;
                            chart.update();
                        }
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                return `Mile ${context[0].parsed.x}`;
                            },
                            afterLabel: function(context) {
                                const mile = context.parsed.x;
                                const segment = segments.find(s => mile >= s.start && mile < s.end);
                                const nearbyAid = aidStations.find(a => Math.abs(a.mile - mile) < 1);
                                
                                let info = [];
                                if (segment) {
                                    info.push(`Segment: ${segment.name}`);
                                }
                                if (nearbyAid) {
                                    const icon = nearbyAid.sleep ? '🛏️' : 
                                                nearbyAid.type === 'water' ? '💧' : '🏃';
                                    const suffix = nearbyAid.type === 'water' ? ' (Water Station)' : '';
                                    info.push(`${icon} ${nearbyAid.name}${suffix}`);
                                }
                                return info;
                            },
                            footer: function(context) {
                                // Add additional context for single runner
                                const dataPoint = context[0];
                                if (dataPoint.datasetIndex === 0) { // Fatigue factor
                                    const fatigue = dataPoint.parsed.y;
                                    if (fatigue > 1.5) return 'High fatigue level';
                                    if (fatigue > 1.2) return 'Moderate fatigue';
                                    if (fatigue < 0.8) return 'Strong performance';
                                    return 'Normal fatigue level';
                                }
                                return '';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        position: 'bottom',
                        display: true,
                        title: {
                            display: true,
                            text: 'Mile'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            callback: function(value, index, values) {
                                // Show mile markers every 25 miles
                                if (value % 25 === 0 && value > 0) {
                                    return Math.round(value);
                                } else if (value === 0) {
                                    return 'Start';
                                }
                                return '';
                            },
                            maxTicksLimit: 15
                        }
                    },
                    xTop: {
                        position: 'top',
                        type: 'linear',
                        display: true,
                        title: {
                            display: true,
                            text: 'Aid Stations',
                            font: {
                                size: 11
                            }
                        },
                        grid: {
                            display: false
                        },
                        min: 0,
                        max: 260,
                        afterBuildTicks: function(axis) {
                            // Force ticks at aid station locations
                            axis.ticks = aidStations.map(station => ({
                                value: station.mile,
                                label: station.mile
                            }));
                        },
                        ticks: {
                            callback: function(value, index, values) {
                                // Show aid station names at their exact locations
                                const station = aidStations.find(s => Math.abs(s.mile - value) < 0.1);
                                
                                if (station) {
                                    const shortName = station.name.length > 15 ? 
                                        station.name.substring(0, 12) + '...' : station.name;
                                    const sleepIcon = station.sleep ? ' 🛏️' : '';
                                    const crewIcon = station.crew ? ' 👥' : '';
                                    return `${shortName}${sleepIcon}${crewIcon}`;
                                }
                                return '';
                            },
                            font: {
                                size: 9
                            },
                            color: '#666'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Fatigue Factor'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Terrain Difficulty (normalized)'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                }
            }
        });
    }

    #updateRestPeriodsList(restData) {
        const container = document.getElementById('restPeriodsList');
        
        // Handle new data structure
        const restPeriods = restData.rest_periods || restData || [];
        const aidStationStops = restData.aid_station_stops || [];
        const patterns = restData.aid_station_patterns || {};
        
        if (restPeriods.length === 0) {
            container.innerHTML = '<p class="text-muted">No significant rest periods detected.</p>';
            return;
        }
        
        let html = '';
        
        // Add aid station patterns summary if available
        if (patterns && Object.keys(patterns).length > 0) {
            html += `
                <div class="alert alert-success mb-3">
                    <h6><i class="fas fa-chart-bar"></i> Aid Station Usage Pattern</h6>
                    <div class="row">
                        <div class="col-md-4">
                            <small><strong>Strategy:</strong> ${patterns.rest_strategy?.replace(/_/g, ' ') || 'N/A'}</small><br>
                            <small><strong>Total Aid Stops:</strong> ${patterns.total_aid_station_stops || 0}</small><br>
                        </div>
                        <div class="col-md-4">
                            <small><strong>Sleep Stations Used:</strong> ${patterns.sleep_station_usage || 0}/4</small><br>
                            <small><strong>Crew Rest Usage:</strong> ${patterns.crew_rest_usage || 0}/6</small><br>
                        </div>
                        <div class="col-md-4">
                            <small><strong>Longest Rest:</strong> ${patterns.longest_rest_station || 'N/A'}</small><br>
                            <small><strong>Duration:</strong> ${(patterns.longest_rest_duration || 0).toFixed(1)} minutes</small>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Display individual rest periods
        html += restPeriods.map(rest => {
            const isCrewRest = rest.rest_type?.startsWith('crew');
            const alertClass = rest.is_sleep_station ? 'alert-warning' : 
                                isCrewRest ? 'alert-primary' :
                                rest.rest_type === 'medical' ? 'alert-danger' : 'alert-info';
            const icon = rest.is_sleep_station ? 'fas fa-bed' :
                        isCrewRest ? 'fas fa-users' :
                        rest.rest_type === 'medical' ? 'fas fa-medkit' :
                        rest.rest_type === 'resupply' ? 'fas fa-box' : 'fas fa-clock';
            
            return `
                <div class="alert ${alertClass}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <div class="mb-1">
                                <i class="${icon}"></i> <strong>Mile ${rest.mile}</strong>
                                ${rest.nearby_aid_station ? ` - ${rest.nearby_aid_station}` : ''}
                                ${rest.is_sleep_station ? '<span class="badge bg-warning ms-2">Sleep Station</span>' : ''}
                            </div>
                            <small class="text-muted d-block">${rest.likely_reason}</small>
                            ${rest.aid_services && rest.aid_services.length > 0 ? 
                                `<small class="text-muted">Services: ${rest.aid_services.join(', ')}</small>` : ''
                            }
                        </div>
                        <div class="text-end">
                            <div><small><strong>${rest.estimated_rest_minutes.toFixed(1)} min</strong> rest</small></div>
                            <div><small class="text-muted">${(rest.pace_ratio).toFixed(1)}x slower</small></div>
                            <small class="badge bg-secondary">${rest.confidence} confidence</small>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = html;
    }

    #updateRecommendations(recommendations) {
        // Overall strategy
        document.getElementById('overallStrategy').textContent = recommendations.overall_strategy;
        
        // Segment recommendations
        const tbody = document.querySelector('#recommendationsTable tbody');
        const html = recommendations.segment_recommendations.map(rec => `
            <tr>
                <td>${rec.segment}</td>
                <td>${rec.miles}</td>
                <td>
                    <div class="progress" style="height: 20px;">
                        <div class="progress-bar ${rec.recommended_effort > 0.8 ? 'bg-danger' : rec.recommended_effort > 0.7 ? 'bg-warning' : 'bg-success'}" 
                                style="width: ${rec.recommended_effort * 100}%">
                            ${Math.round(rec.recommended_effort * 100)}%
                        </div>
                    </div>
                </td>
                <td>${rec.key_strategy}</td>
            </tr>
        `).join('');
        tbody.innerHTML = html;
        
        // Critical segments
        const criticalContainer = document.getElementById('criticalSegments');
        const criticalHtml = recommendations.critical_segments.map(segment => `
            <div class="list-group-item list-group-item-warning">
                <i class="fas fa-exclamation-triangle"></i> ${segment}
            </div>
        `).join('');
        criticalContainer.innerHTML = criticalHtml || '<div class="list-group-item">No critical segments identified</div>';
    }

    #updateMultiRunnerRestPeriods() {
        const container = document.getElementById('multiRunnerRestPeriods');
        
        if (!container) {
            console.warn('Multi-runner rest periods container not found');
            return;
        }
        
        if (!this.analyses || Object.keys(this.analyses).length === 0) {
            container.innerHTML = '<p class="text-center text-muted">No rest period data available</p>';
            return;
        }
        
        let html = '<div class="row">';
        
        this.runners.selectedRunners.forEach(runnerId => {
            const analysis = this.analyses[runnerId];
            const runner = this.runners.allRunners.find(r => r.id === runnerId);
            const restPeriods = analysis?.rest_periods?.rest_periods || analysis?.rest_periods || [];
            console.log(`Runner ${runnerId} (${runner.first_name} ${runner.last_name}) has ${restPeriods} rest periods`);
            
            html += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card h-100">
                        <div class="card-header">
                            <strong>${runner.first_name} ${runner.last_name}</strong>
                        </div>
                        <div class="card-body">
                            ${restPeriods.length === 0 ? 
                                '<p class="text-muted small">No significant rest periods detected</p>' :
                                restPeriods.slice(0, 3).map(rest => `
                                    <div class="alert alert-info alert-sm py-2 px-2 mb-2">
                                        <div class="d-flex justify-content-between">
                                            <strong>Mile ${rest.start_mile}</strong>
                                            <small>${rest.duration_minutes.toFixed(0)} min</small>
                                        </div>
                                        <small class="text-muted">${rest.location_name || 'Rest stop'}</small>
                                    </div>
                                `).join('') + 
                                (restPeriods.length > 3 ? `<small class="text-muted">...and ${restPeriods.length - 3} more</small>` : '')
                            }
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        container.innerHTML = html;
    }
}

export class MutipleRunnerAnalysis extends BaseRunnerAnalysis {
    constructor() { super(2); }

    /**
     * @param {RunnerAnalyses} analyses - An instance of the RunnerAnalyses class.
     * @param {Runners} runners - An instance of the Runners class.
     */
    init(analyses, runners) {
        super.init(analyses, runners);
        console.log("After super: ", this.analyses);

        // Update header
        console.log(runners);

        const runnerNames = [];

        this.runners.selectedRunners.forEach(runnerId => {
            const r = this.runners.allRunners.find(r => r.id === runnerId);
            runnerNames.push(`${r.first_name} ${r.last_name}`);
        });

        this._analysisRunnerName(runnerNames.join(", "));

        // Get course segments from first runner's analysis
        const firstRunnerData = Object.values(this.analyses)[0];
        const courseSegments = firstRunnerData?.course_analysis?.segment_analysis;

        // Update the multi-runner summary table
        this.#updateMultiRunnerTable();

        // Create multi-runner fatigue chart
        this.#createMultiRunnerFatigueChart(courseSegments);

        // Update the single-runner sections with multi-runner data
        this.updateSegmentTable(courseSegments);
        this.#updateRestPeriodsListMultiRunner();
        this.#updateRecommendationsMultiRunner();

        // Make sure recommendations section is visible for multi-runner  
        const overallStrategyEl = document.getElementById('overallStrategy');
        if (overallStrategyEl) {
            const recommendationsCard = overallStrategyEl.closest('.card');
            if (recommendationsCard) {
                recommendationsCard.style.display = 'block';
                console.log('Made recommendations section visible');
            } else {
                console.log('Could not find recommendations card');
            }
        } else {
            console.log('Could not find overallStrategy element');
        }
    }

    #updateMultiRunnerTable() {
        const tbody = document.querySelector('#multiRunnerTable tbody');
        
        if (!tbody) {
            console.error('Multi-runner table tbody not found');
            return;
        }
        
        const html = this.runners.selectedRunners.map(runnerId => {
            const runner = this.runners.allRunners.find(r => r.id === runnerId);
            const analysis = this.analyses[runnerId];
            
            if (!runner || !analysis) {
                return `
                    <tr>
                        <td colspan="6" class="text-center text-muted">Analysis data not available for runner ID ${runnerId}</td>
                    </tr>
                `;
            }
            
            // Safe access to data with fallbacks
            const avgFatigue = analysis.fatigue_analysis?.average_fatigue?.toFixed(2) || 'N/A';
            const peakMile = analysis.fatigue_analysis?.peak_fatigue_mile || 'N/A';
            const restCount = analysis.rest_periods?.rest_periods?.length || analysis.rest_periods?.length || 0;
            const strongestTerrain = analysis.course_analysis?.strongest_terrain || 'Unknown';
            const elevationTolerance = analysis.course_analysis?.elevation_tolerance || 'Unknown';
            
            return `
                <tr>
                    <td><strong>${runner.first_name} ${runner.last_name}</strong></td>
                    <td>${avgFatigue}</td>
                    <td>${peakMile}</td>
                    <td>${restCount}</td>
                    <td><span class="badge bg-success">${strongestTerrain}</span></td>
                    <td>${elevationTolerance}</td>
                </tr>
            `;
        }).join('');
        
        tbody.innerHTML = html;
    }

    #createMultiRunnerFatigueChart(courseSegments) {
        const ctx = document.getElementById('multiRunnerFatigueChart').getContext('2d');
        
        // Clear any existing chart
        const existingChart = Chart.getChart(ctx);
        if (existingChart) {
            existingChart.destroy();
        }
        
        // Validate inputs
        if (!this.analyses || Object.keys(this.analyses).length === 0) {
            console.error('No analysis data provided for multi-runner chart');
            return;
        }
        
        // Use dynamic course segments if provided, otherwise fall back to hardcoded
        let segments = [];
        if (courseSegments && courseSegments.length > 0) {
            // Create segments with two alternating soft colors
            const colors = [
                'rgba(173, 216, 230, 0.1)',   // Light blue (even lighter for multi-runner)
                'rgba(221, 221, 221, 0.1)'    // Light gray (even lighter for multi-runner)
            ];
            
            segments = courseSegments.map((segment, index) => ({
                name: segment.segment_name,
                start: segment.start_mile,
                end: segment.end_mile,
                color: colors[index % colors.length]
            }));
        } else {
            // Fallback to hardcoded segments with two alternating colors
            const colors = ['rgba(173, 216, 230, 0.1)', 'rgba(221, 221, 221, 0.1)'];
            segments = [
                {name: "Desert Start to Crown King", start: 0, end: 36.6, color: colors[0]},
                {name: "Crown King to Whiskey Row", start: 36.6, end: 77.3, color: colors[1]},
                {name: "Whiskey Row to Jerome", start: 77.3, end: 125.3, color: colors[0]},
                {name: "Jerome to Sedona Sleep Station", start: 125.3, end: 162.3, color: colors[1]},
                {name: "Sedona to Fort Tuthill Sleep", start: 162.3, end: 214.4, color: colors[0]},
                {name: "Fort Tuthill to Finish", start: 214.4, end: 256.5, color: colors[1]}
            ];
        }

        const datasets = this.runners.selectedRunners.map((runnerId, index) => {
            console.log(`Runner data: ${this.runners.selectedRunners}`);
            const runner = this.runners.allRunners.find(r => r.id === runnerId);
            const analysis = this.analyses[runnerId];
            const colors = ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff'];
            
            // Check if fatigue data exists
            console.log(analysis);
            console.log(this.analyses);
            let fatigueData = [];
            if (analysis && analysis.fatigue_analysis && analysis.fatigue_analysis.fatigue_progression) {
                fatigueData = analysis.fatigue_analysis.fatigue_progression.map(p => ({x: p.mile, y: p.fatigue_factor}));
            } else {
                console.warn(`Missing fatigue data for runner ${runnerId}: ${runner.first_name} ${runner.last_name}`);
                // Create empty dataset so chart still renders for other runners
                fatigueData = [];
            }
            
            return {
                label: `${runner.first_name} ${runner.last_name}`,
                data: fatigueData,
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length] + '20',
                tension: 0.1,
                fill: false,
                pointRadius: 2,
                pointHoverRadius: 5,
                borderWidth: 2
            };
        }).filter(dataset => dataset.data.length > 0); // Remove empty datasets

        // Check if we have any valid datasets before creating the chart
        if (datasets.length === 0) {
            console.error('No valid fatigue data available for multi-runner chart');
            // Show a message in the chart area
            ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
            ctx.fillStyle = '#666';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('No fatigue data available for selected runners', ctx.canvas.width / 2, ctx.canvas.height / 2);
            return;
        }

        console.log(`Creating multi-runner chart with ${datasets.length} datasets`);

        // Use same comprehensive aid station data as single runner chart
        const multiRunnerAidStations = [
            {name: "Deep Canyon Ranch", mile: 0, type: "major_aid", sleep: false, crew: true},
            {name: "Cottonwood Creek", mile: 7.4, type: "aid", sleep: false, crew: false},
            {name: "Water Station", mile: 10.4, type: "water", sleep: false, crew: false},
            {name: "Water Station", mile: 24.6, type: "water", sleep: false, crew: false},
            {name: "Lane Mtn by UltrAspire", mile: 32.5, type: "aid", sleep: false, crew: false},
            {name: "Crown King by Tailwind", mile: 36.6, type: "major_aid", sleep: false, crew: true},
            {name: "Arrastra Creek", mile: 53, type: "aid", sleep: false, crew: false},
            {name: "Kamp Kipa", mile: 62.4, type: "aid", sleep: true, crew: false},
            {name: "Camp Wamatochick", mile: 69, type: "aid", sleep: true, crew: false},
            {name: "Whiskey Row", mile: 77.3, type: "major_aid", sleep: true, crew: true},
            {name: "Iron King", mile: 90.7, type: "aid", sleep: false, crew: true},
            {name: "Fain Ranch by Satisfy", mile: 95.9, type: "aid", sleep: false, crew: true},
            {name: "Mingus Mountain Camp", mile: 108.3, type: "major_aid", sleep: true, crew: true},
            {name: "Jerome Historic State Park", mile: 125.3, type: "aid", sleep: false, crew: true},
            {name: "Dead Horse Ranch", mile: 134, type: "major_aid", sleep: true, crew: true},
            {name: "Deer Pass Trailhead", mile: 148, type: "aid", sleep: false, crew: true},
            {name: "Water Station", mile: 154.7, type: "water", sleep: false, crew: false},
            {name: "Sedona Posse Grounds", mile: 162.3, type: "major_aid", sleep: true, crew: true},
            {name: "Water Station", mile: 173.6, type: "water", sleep: false, crew: false},
            {name: "Foxboro Ranch", mile: 177.4, type: "aid", sleep: false, crew: true},
            {name: "Munds Park", mile: 193.4, type: "major_aid", sleep: true, crew: true},
            {name: "Kelly Canyon", mile: 206, type: "aid", sleep: false, crew: false},
            {name: "Fort Tuthill", mile: 214.4, type: "major_aid", sleep: true, crew: true},
            {name: "Walnut Canyon", mile: 230.5, type: "aid", sleep: false, crew: true},
            {name: "Wildcat Hill", mile: 237.3, type: "aid", sleep: false, crew: true},
            {name: "Trinity Heights", mile: 252.6, type: "aid", sleep: false, crew: false},
            {name: "Heritage Square", mile: 256.5, type: "major_aid", sleep: false, crew: true}
        ];

        // Define custom plugin for segment backgrounds and aid station markers
        const multiRunnerSegmentPlugin = {
            id: 'multiRunnerSegmentBackground',
            beforeDraw: (chart) => {
                const ctx = chart.ctx;
                const chartArea = chart.chartArea;
                const xScale = chart.scales.x;
                
                if (!xScale || !chartArea) return;
                
                // Draw segment backgrounds
                segments.forEach(segment => {
                    const startX = xScale.getPixelForValue(segment.start);
                    const endX = xScale.getPixelForValue(segment.end);
                    
                    if (startX < chartArea.right && endX > chartArea.left) {
                        ctx.save();
                        ctx.fillStyle = segment.color;
                        ctx.fillRect(Math.max(startX, chartArea.left), chartArea.top, 
                                    Math.min(endX, chartArea.right) - Math.max(startX, chartArea.left), 
                                    chartArea.bottom - chartArea.top);
                        ctx.restore();
                    }
                });
            },
            afterDraw: (chart) => {
                const ctx = chart.ctx;
                const chartArea = chart.chartArea;
                const xScale = chart.scales.x;
                
                if (!xScale || !chartArea) return;
                
                // Draw aid station markers
                multiRunnerAidStations.forEach(station => {
                    const x = xScale.getPixelForValue(station.mile);
                    
                    if (x >= chartArea.left && x <= chartArea.right) {
                        ctx.save();
                        
                        const isWaterStation = station.type === 'water';
                        
                        // Draw vertical line (lighter for multi-runner)
                        let strokeColor, lineWidth, dashPattern;
                        if (station.sleep) {
                            strokeColor = '#ff6b6b80';
                            lineWidth = 2;
                            dashPattern = [];
                        } else if (isWaterStation) {
                            strokeColor = '#17a2b880';
                            lineWidth = 1;
                            dashPattern = [2, 4];
                        } else {
                            strokeColor = '#4ecdc480';
                            lineWidth = 1;
                            dashPattern = [5, 5];
                        }
                        
                        ctx.strokeStyle = strokeColor;
                        ctx.lineWidth = lineWidth;
                        ctx.setLineDash(dashPattern);
                        ctx.beginPath();
                        ctx.moveTo(x, chartArea.top);
                        ctx.lineTo(x, chartArea.bottom);
                        ctx.stroke();
                        
                        // Draw marker symbol (smaller for multi-runner)
                        if (station.sleep) {
                            ctx.fillStyle = '#ff6b6b';
                            // Sleep station - diamond shape
                            ctx.beginPath();
                            ctx.moveTo(x, chartArea.top - 6);
                            ctx.lineTo(x + 4, chartArea.top - 2);
                            ctx.lineTo(x, chartArea.top + 2);
                            ctx.lineTo(x - 4, chartArea.top - 2);
                            ctx.closePath();
                            ctx.fill();
                        } else if (isWaterStation) {
                            ctx.fillStyle = '#17a2b8';
                            // Water station - small triangle
                            ctx.beginPath();
                            ctx.moveTo(x, chartArea.top - 3);
                            ctx.lineTo(x + 2, chartArea.top + 1);
                            ctx.lineTo(x - 2, chartArea.top + 1);
                            ctx.closePath();
                            ctx.fill();
                        } else {
                            ctx.fillStyle = '#4ecdc4';
                            // Regular aid station - circle
                            ctx.beginPath();
                            ctx.arc(x, chartArea.top - 2, 3, 0, 2 * Math.PI);
                            ctx.fill();
                        }
                        
                        ctx.restore();
                    }
                });
            }
        };
        
        try {
            new Chart(ctx, {
            type: 'line',
            plugins: [multiRunnerSegmentPlugin],
            data: { datasets },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        position: 'top',
                        onClick: function(e, legendItem, legend) {
                            const index = legendItem.datasetIndex;
                            const chart = legend.chart;
                            const meta = chart.getDatasetMeta(index);

                            // Toggle dataset visibility
                            meta.hidden = meta.hidden === null ? !chart.data.datasets[index].hidden : null;
                            chart.update();
                        }
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                return `Mile ${context[0].parsed.x}`;
                            },
                            afterLabel: function(context) {
                                const mile = context.parsed.x;
                                const segment = segments.find(s => mile >= s.start && mile < s.end);
                                const nearbyAid = multiRunnerAidStations.find(a => Math.abs(a.mile - mile) < 1);
                                
                                let info = [];
                                if (segment) {
                                    info.push(`Segment: ${segment.name}`);
                                }
                                if (nearbyAid) {
                                    const icon = nearbyAid.sleep ? '🛏️' : 
                                                nearbyAid.type === 'water' ? '💧' : '🏃';
                                    const suffix = nearbyAid.type === 'water' ? ' (Water Station)' : '';
                                    info.push(`${icon} ${nearbyAid.name}${suffix}`);
                                }
                                return info;
                            },
                            footer: function(context) {
                                // Show relative performance
                                const values = context.map(c => c.parsed.y);
                                const min = Math.min(...values);
                                const max = Math.max(...values);
                                if (max > min) {
                                    return `Range: ${min.toFixed(2)} - ${max.toFixed(2)} (${((max-min)/min*100).toFixed(1)}% diff)`;
                                }
                                return '';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        position: 'bottom',
                        type: 'linear',
                        display: true,
                        title: {
                            display: true,
                            text: 'Mile'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            callback: function(value, index, values) {
                                // Show mile markers every 25 miles
                                if (value % 25 === 0 && value > 0) {
                                    return Math.round(value);
                                } else if (value === 0) {
                                    return 'Start';
                                }
                                return '';
                            },
                            maxTicksLimit: 15
                        }
                    },
                    xTop: {
                        position: 'top',
                        type: 'linear',
                        display: true,
                        title: {
                            display: true,
                            text: 'Aid Stations',
                            font: {
                                size: 11
                            }
                        },
                        grid: {
                            display: false
                        },
                        min: 0,
                        max: 260,
                        afterBuildTicks: function(axis) {
                            // Force ticks at aid station locations
                            axis.ticks = multiRunnerAidStations.map(station => ({
                                value: station.mile,
                                label: station.mile
                            }));
                        },
                        ticks: {
                            callback: function(value, index, values) {
                                // Show aid station names at their exact locations
                                const station = multiRunnerAidStations.find(s => Math.abs(s.mile - value) < 0.1);
                                
                                if (station) {
                                    const shortName = station.name.length > 15 ? 
                                        station.name.substring(0, 12) + '...' : station.name;
                                    const sleepIcon = station.sleep ? ' 🛏️' : '';
                                    const crewIcon = station.crew ? ' 👥' : '';
                                    return `${shortName}${sleepIcon}${crewIcon}`;
                                }
                                return '';
                            },
                            font: {
                                size: 9
                            },
                            color: '#666'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Fatigue Factor'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    }
                }
            }
        });
        } catch (error) {
            console.error('Error creating multi-runner fatigue chart:', error);
            // Show error message in chart area
            ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
            ctx.fillStyle = '#666';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Error creating chart', ctx.canvas.width / 2, ctx.canvas.height / 2);
        }
    }

    #updateRestPeriodsListMultiRunner() {
        // Use the single-runner rest periods container but show multi-runner comparison
        const container = document.getElementById('restPeriodsList');
        
        // Function is being called successfully            
        if (!container) {
            console.error('Rest periods container not found');
            return;
        }
        
        if (!this.analyses || Object.keys(this.analyses).length === 0) {
            console.error('No analyses data provided');
            container.innerHTML = '<div class="text-center text-muted py-4"><p>No analysis data available</p></div>';
            return;
        }
        
        if (!this.runners.selectedRunners || this.runners.selectedRunners.length === 0) {
            console.error('No selected runners');
            container.innerHTML = '<div class="text-center text-muted py-4"><p>No runners selected</p></div>';
            return;
        }
        
        // Create pace vs elevation chart first
        let html = `
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h6><i class="fas fa-chart-line"></i> Pace vs Distance with Elevation Profile</h6>
                            <small class="text-muted">Shows pace patterns with detected rest periods and elevation context</small>
                        </div>
                        <div class="card-body">
                            <canvas id="paceElevationChart" height="120"></canvas>
                            <div class="mt-2">
                                <small class="text-muted">
                                    <i class="fas fa-circle" style="color: rgba(255, 99, 132, 0.8);"></i> Pace (left axis) •
                                    <i class="fas fa-square" style="color: rgba(75, 192, 192, 0.3);"></i> Elevation (right axis) •
                                    <i class="fas fa-pause-circle"></i> Rest periods marked as points
                                </small>
                                <br>
                                <small class="text-primary">
                                    <i class="fas fa-mouse-pointer"></i> <strong>Interactive:</strong> 
                                    Drag to pan • Scroll wheel to zoom • Double-click to reset view
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;
        
        html += `
            <div class="row mb-3">
                <div class="col-12">
                    <h6><i class="fas fa-list"></i> Detailed Rest Period Breakdown</h6>
                    
                    <!-- Rest Period Detection Explanation (Collapsible) -->
                    <div class="mb-3">
                        <button class="btn btn-outline-info btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#restPeriodExplanation" aria-expanded="false" aria-controls="restPeriodExplanation">
                            <i class="fas fa-info-circle"></i> Understanding Rest Period Detection
                        </button>
                    </div>
                    
                    <div class="collapse mb-4" id="restPeriodExplanation">
                        <div class="card border-info">
                            <div class="card-body">
                                <h6 class="card-title text-info"><i class="fas fa-pause-circle"></i> How Rest Period Detection Works</h6>
                                <p class="small mb-3">
                                    <strong>Rest periods are automatically detected using pace analysis</strong> to identify when runners 
                                    significantly slow down compared to their surrounding splits.
                                </p>
                                
                                <div class="row">
                                    <div class="col-md-6">
                                        <h6 class="small text-primary"><i class="fas fa-stopwatch"></i> Detection Criteria</h6>
                                        <ul class="small mb-3">
                                            <li><strong>Primary Threshold:</strong> Pace >50% slower than surrounding splits</li>
                                            <li><strong>Context Window:</strong> Analyzes 3 splits before and after current split</li>
                                            <li><strong>Aid Station Correlation:</strong> Within 5-mile radius of aid stations</li>
                                            <li><strong>Valid Data:</strong> Requires valid pace data for analysis</li>
                                        </ul>
                                    </div>
                                    <div class="col-md-6">
                                        <h6 class="small text-primary"><i class="fas fa-calculator"></i> Example Calculation</h6>
                                        <ul class="small mb-3">
                                            <li>Surrounding splits average: 12 min/mile</li>
                                            <li>Threshold for rest period: >18 min/mile (12 × 1.5)</li>
                                            <li>25 min/mile split = significant rest period</li>
                                            <li>Duration estimated from pace differential</li>
                                        </ul>
                                    </div>
                                </div>
                                
                                <div class="alert alert-light border-0 small">
                                    <i class="fas fa-lightbulb text-warning"></i> 
                                    <strong>Note:</strong> The pace chart shows all pace variations, while the cards below 
                                    show only significant rest periods that meet the 50% threshold and correlate with aid station locations.
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row">
        `;
        
        // Collect all rest periods with runner info for grouping
        const allRunnerRestPeriods = [];
        this.runners.selectedRunners.forEach(runnerId => {
            const analysis = this.analyses[runnerId];
            const runner = this.runners.allRunners.find(r => r.id === runnerId);
            const allRestPeriods = analysis?.rest_periods?.rest_periods || analysis?.rest_periods || [];
            
            console.log(`Runner ${runnerId} (${runner?.first_name} ${runner?.last_name}):`, {
                hasAnalysis: !!analysis,
                restPeriodsCount: allRestPeriods.length,
                analysisKeys: analysis ? Object.keys(analysis) : 'none'
            });
            
            // Apply same filtering as chart - only rest periods with location data
            const restPeriods = allRestPeriods.filter(rest => rest.mile || rest.start_mile);
            
            console.log(`Runner ${runnerId} (${runner?.first_name}):`, {
                hasAnalysis: !!analysis,
                allRestPeriods: allRestPeriods.length,
                filteredRestPeriods: restPeriods.length,
                restPeriodsArray: restPeriods
            });
            
            
            // Add runner info to each rest period
            restPeriods.forEach(rest => {
                allRunnerRestPeriods.push({
                    ...rest,
                    runnerId: runnerId,
                    runnerName: `${runner.first_name} ${runner.last_name}`
                });
            });
        });
        
        // Group rest periods by proximity (within 5-mile variance for GPS imprecision)
        const MILE_VARIANCE_THRESHOLD = 5.0;
        const restGroups = [];
        
        // Sort all rest periods by mile marker
        allRunnerRestPeriods.sort((a, b) => {
            const aMile = a.mile || a.start_mile || 0;
            const bMile = b.mile || b.start_mile || 0;
            return aMile - bMile;
        });
        
        // Group rest periods by aid station (only group if same aid station)
        allRunnerRestPeriods.forEach(rest => {
            const restMile = rest.mile || rest.start_mile || 0;
            const restAidStation = rest.nearby_aid_station || 'Unknown';
            let addedToGroup = false;
            
            // Check if this rest period can be added to an existing group (same aid station)
            for (let group of restGroups) {
                const groupAidStation = group[0].nearby_aid_station || 'Unknown';
                const groupAvgMile = group.reduce((sum, r) => sum + (r.mile || r.start_mile || 0), 0) / group.length;
                
                // Only group if same aid station AND within mile variance
                if (restAidStation === groupAidStation && Math.abs(restMile - groupAvgMile) <= MILE_VARIANCE_THRESHOLD) {
                    group.push(rest);
                    addedToGroup = true;
                    break;
                }
            }
            
            // If not added to any group, create a new group
            if (!addedToGroup) {
                restGroups.push([rest]);
            }
        });
        
        // Sort groups by average mile marker
        restGroups.sort((a, b) => {
            const aAvgMile = a.reduce((sum, r) => sum + (r.mile || r.start_mile || 0), 0) / a.length;
            const bAvgMile = b.reduce((sum, r) => sum + (r.mile || r.start_mile || 0), 0) / b.length;
            return aAvgMile - bAvgMile;
        });
        
        // Debug: Log each group with its mile range and runners
        restGroups.forEach((group, index) => {
            const avgMile = group.reduce((sum, r) => sum + (r.mile || r.start_mile || 0), 0) / group.length;
            const runnerIds = group.map(r => r.runnerId);
            const restMiles = group.map(r => `${r.runnerId}:${r.mile || r.start_mile}`);
            
            // Extra debug for groups around mile 96
            if (avgMile >= 95 && avgMile <= 97) {
            }
        });
        
        // Generate runner headers
        html += `
            <div class="row mb-3">
                ${this.runners.selectedRunners.map(runnerId => {
                    const runner = this.runners.allRunners.find(r => r.id === runnerId);
                    return `
                        <div class="col-md-${this.runners.selectedRunners.length === 1 ? '12' : this.runners.selectedRunners.length === 2 ? '6' : '4'}">
                            <h6 class="text-center text-primary mb-0">
                                <i class="fas fa-user"></i> ${runner.first_name} ${runner.last_name}
                            </h6>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
        
        // Function to create a rest period card (preserving original styling)
        function createRestCard(rest, colClass) {
            const isCrewRest = rest.rest_type?.startsWith('crew');
            const alertClass = rest.is_sleep_station ? 'alert-warning' : 
                                isCrewRest ? 'alert-primary' :
                                rest.rest_type === 'medical' ? 'alert-danger' : 'alert-info';
            const icon = rest.is_sleep_station ? 'fas fa-bed' :
                        isCrewRest ? 'fas fa-users' :
                        rest.rest_type === 'medical' ? 'fas fa-medkit' :
                        rest.rest_type === 'resupply' ? 'fas fa-box' : 'fas fa-clock';
            
            return `
                <div class="col-md-${colClass}">
                    <div class="alert ${alertClass} mb-0">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <div class="mb-1">
                                    <i class="${icon}"></i> <strong>Mile ${rest.mile || rest.start_mile}</strong>
                                    ${rest.nearby_aid_station ? ` ${rest.confidence === 'low' && rest.aid_station_distance > 2.0 ? 'near' : 'at'} ${rest.nearby_aid_station}` : ''}
                                    ${rest.is_sleep_station ? '<span class="badge bg-warning ms-2">Sleep Station</span>' : ''}
                                </div>
                                <small class="text-muted d-block">${rest.likely_reason ? (rest.confidence === 'low' && rest.aid_station_distance > 2.0 ? rest.likely_reason.replace(' at ', ' near ') : rest.likely_reason) : 'Rest period detected'}</small>
                                ${rest.aid_services && rest.aid_services.length > 0 ? 
                                    `<small class="text-muted">Services: ${rest.aid_services.join(', ')}</small>` : ''
                                }
                            </div>
                            <div class="text-end">
                                <div><small><strong>${rest.estimated_rest_minutes ? rest.estimated_rest_minutes.toFixed(1) : rest.duration_minutes ? rest.duration_minutes.toFixed(0) : 'N/A'} min</strong> rest</small></div>
                                ${rest.pace_ratio ? `<div><small class="text-muted">${rest.pace_ratio.toFixed(1)}x slower</small></div>` : ''}
                                <small class="badge bg-secondary">${rest.confidence || 'medium'} confidence</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Function to create a placeholder card for runners without rest at this location
        function createPlaceholderCard(avgMile, nearbyAidStation, colClass) {
            return `
                <div class="col-md-${colClass}">
                    <div class="alert alert-light border mb-0" style="opacity: 0.6;">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <div class="mb-1">
                                    <i class="fas fa-minus-circle text-muted"></i> <strong>Mile ~${avgMile.toFixed(1)}</strong>
                                    ${nearbyAidStation ? ` - ${nearbyAidStation}` : ''}
                                </div>
                                <small class="text-muted d-block">No rest detected</small>
                            </div>
                            <div class="text-end">
                                <small class="badge bg-light text-muted">no rest</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Generate horizontally aligned rest period cards
        if (restGroups.length === 0) {
            html += '<div class="text-center text-muted py-4"><p>No rest period data available for selected runners</p></div>';
        }
        else {
            const colClass = this.runners.selectedRunners.length === 1 ? '12' : this.runners.selectedRunners.length === 2 ? '6' : '4';
            
            // Show first 3 rest groups initially 
            const visibleGroups = Math.min(3, restGroups.length);
            
            restGroups.slice(0, visibleGroups).forEach((group, groupIndex) => {
                const avgMile = group.reduce((sum, r) => sum + (r.mile || r.start_mile || 0), 0) / group.length;
                const nearbyAidStation = group.find(r => r.nearby_aid_station)?.nearby_aid_station || '';
                
                html += `<div class="row mb-3 rest-group" data-group-index="${groupIndex}">`;
                
                // Create card for each runner (either rest card or placeholder)
                this.runners.selectedRunners.forEach(runnerId => {
                    // Find the best rest period for this runner prioritizing confidence and slowest pace
                    const runnerRests = group.filter(r => r.runnerId == runnerId);
                    const runnerRest = runnerRests.length > 0 ? 
                        runnerRests.reduce((best, current) => {
                            // Confidence scoring: high=3, medium=2, low=1, undefined=0
                            const getConfidenceScore = (conf) => {
                                switch(conf) {
                                    case 'high': return 3;
                                    case 'medium': return 2;
                                    case 'low': return 1;
                                    default: return 0;
                                }
                            };
                            
                            const bestConf = getConfidenceScore(best.confidence);
                            const currentConf = getConfidenceScore(current.confidence);
                            
                            // 1. Prioritize higher confidence
                            if (currentConf > bestConf) return current;
                            if (bestConf > currentConf) return best;
                            
                            // 2. If same confidence, prioritize slower pace (higher pace_during)
                            const bestPace = best.pace_during || best.actual_pace || 0;
                            const currentPace = current.pace_during || current.actual_pace || 0;
                            if (currentPace > bestPace) return current;
                            if (bestPace > currentPace) return best;
                            
                            // 3. If same confidence and pace, prioritize closer to group average
                            const bestDiff = Math.abs((best.mile || best.start_mile || 0) - avgMile);
                            const currentDiff = Math.abs((current.mile || current.start_mile || 0) - avgMile);
                            return currentDiff < bestDiff ? current : best;
                        }) : null;
                    
                    
                    if (runnerRest) {
                        html += createRestCard(runnerRest, colClass);
                    } else {
                        html += createPlaceholderCard(avgMile, nearbyAidStation, colClass);
                    }
                });
                
                html += `</div>`;
            });
            
            // Add hidden groups for "show more" functionality
            if (restGroups.length > visibleGroups) {
                restGroups.slice(visibleGroups).forEach((group, groupIndex) => {
                    const actualGroupIndex = visibleGroups + groupIndex;
                    const avgMile = group.reduce((sum, r) => sum + (r.mile || r.start_mile || 0), 0) / group.length;
                    const nearbyAidStation = group.find(r => r.nearby_aid_station)?.nearby_aid_station || '';
                    
                    html += `<div class="row mb-3 rest-group hidden-rest-group" data-group-index="${actualGroupIndex}" style="display: none;">`;
                    
                    this.runners.selectedRunners.forEach(runnerId => {
                        // Find the best rest period for this runner prioritizing confidence and slowest pace
                    const runnerRests = group.filter(r => r.runnerId == runnerId);
                    const runnerRest = runnerRests.length > 0 ? 
                        runnerRests.reduce((best, current) => {
                            // Confidence scoring: high=3, medium=2, low=1, undefined=0
                            const getConfidenceScore = (conf) => {
                                switch(conf) {
                                    case 'high': return 3;
                                    case 'medium': return 2;
                                    case 'low': return 1;
                                    default: return 0;
                                }
                            };
                            
                            const bestConf = getConfidenceScore(best.confidence);
                            const currentConf = getConfidenceScore(current.confidence);
                            
                            // 1. Prioritize higher confidence
                            if (currentConf > bestConf) return current;
                            if (bestConf > currentConf) return best;
                            
                            // 2. If same confidence, prioritize slower pace (higher pace_during)
                            const bestPace = best.pace_during || best.actual_pace || 0;
                            const currentPace = current.pace_during || current.actual_pace || 0;
                            if (currentPace > bestPace) return current;
                            if (bestPace > currentPace) return best;
                            
                            // 3. If same confidence and pace, prioritize closer to group average
                            const bestDiff = Math.abs((best.mile || best.start_mile || 0) - avgMile);
                            const currentDiff = Math.abs((current.mile || current.start_mile || 0) - avgMile);
                            return currentDiff < bestDiff ? current : best;
                        }) : null;
                        
                        if (runnerRest) {
                            html += createRestCard(runnerRest, colClass);
                        } else {
                            html += createPlaceholderCard(avgMile, nearbyAidStation, colClass);
                        }
                    });
                    
                    html += `</div>`;
                });
                
                // Add show more button
                html += `
                    <div class="text-center mb-4">
                        <button class="btn btn-outline-secondary" onclick="toggleAllRestGroups(this)">
                            <i class="fas fa-chevron-down"></i> Show ${restGroups.length - visibleGroups} more rest locations
                        </button>
                    </div>
                `;
            }
        }
        
        html += '</div>';
        
        // If no content was generated, show a message
        if (html === '<div class="row"></div>') {
            html = '<div class="text-center text-muted py-4"><p>No rest period data available for selected runners</p></div>';
        }
        
        container.innerHTML = html;
        
        // Create the pace vs elevation chart
        this.createPaceElevationChart();
    }
    
    #updateRecommendationsMultiRunner() {
        console.log('updateRecommendationsMultiRunner called with:', this.analyses);
        
        // Check what data we actually have
        Object.keys(this.analyses).forEach(runnerId => {
            console.log(`Runner ${runnerId} data keys:`, Object.keys(this.analyses[runnerId]));
            if (this.analyses[runnerId].recommendations) {
                console.log(`Runner ${runnerId} recommendations:`, this.analyses[runnerId].recommendations);
            }
        });
        
        // Hide overall strategy section for multi-runner mode
        const overallContainer = document.getElementById('overallStrategy');
        if (overallContainer) {
            const overallCol = overallContainer.closest('.col-md-8');
            if (overallCol) {
                overallCol.style.display = 'none';
            }
        }
        
        // Hide segment recommendations table for multi-runner mode and expand critical segments
        const recommendationsTableContainer = document.querySelector('#recommendationsTable');
        if (recommendationsTableContainer) {
            const tableCard = recommendationsTableContainer.closest('.col-md-4');
            if (tableCard) {
                tableCard.style.display = 'none';
            }
        }
        
        // Expand critical segments to full width for multi-runner mode
        const criticalSegmentsCard = document.getElementById('criticalSegments');
        if (criticalSegmentsCard) {
            const criticalCol = criticalSegmentsCard.closest('.col-md-4');
            if (criticalCol) {
                criticalCol.className = 'col-12';
            }
        }
        
        // Critical segments - find segments where runners struggled most
        const criticalContainer = document.getElementById('criticalSegments');
        if (criticalContainer) {
            const segmentPerformances = [];
            
            this.runners.selectedRunners.forEach(runnerId => {
                const analysis = this.analyses[runnerId];
                if (analysis?.course_analysis?.segment_analysis) {
                    analysis.course_analysis.segment_analysis.forEach(segment => {
                        segmentPerformances.push({
                            name: segment.segment_name,
                            difficulty: segment.difficulty_rating || 0,
                            performance: segment.performance_score || 0,
                            runnerId: runnerId
                        });
                    });
                }
            });
            
            // Group by segment and find average difficulty
            const segmentStats = {};
            segmentPerformances.forEach(perf => {
                if (!segmentStats[perf.name]) {
                    segmentStats[perf.name] = { difficulties: [], performances: [], count: 0 };
                }
                segmentStats[perf.name].difficulties.push(perf.difficulty);
                segmentStats[perf.name].performances.push(perf.performance);
                segmentStats[perf.name].count++;
            });
            
            // Find most challenging segments
            const criticalSegments = Object.entries(segmentStats)
                .map(([name, stats]) => ({
                    name,
                    avgDifficulty: stats.difficulties.reduce((a, b) => a + b, 0) / stats.count,
                    avgPerformance: stats.performances.reduce((a, b) => a + b, 0) / stats.count,
                    count: stats.count
                }))
                .sort((a, b) => b.avgDifficulty - a.avgDifficulty)
                .slice(0, 5);
            
            if (criticalSegments.length > 0) {
                const html = criticalSegments.map(segment => `
                    <div class="list-group-item list-group-item-warning">
                        <strong>${segment.name}</strong>
                        <small class="text-muted d-block">
                            Difficulty Rating: ${segment.avgDifficulty.toFixed(1)}/5.0
                            ${segment.count > 1 ? ` (${segment.count} runners)` : ''}
                        </small>
                    </div>
                `).join('');
                criticalContainer.innerHTML = html;
            } else {
                criticalContainer.innerHTML = '<div class="list-group-item">No segment analysis data available</div>';
            }
        }
    }

}