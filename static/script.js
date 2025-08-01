// Global application object
const DailyCloseApp = {
    // Initialize the application
    init() {
        this.initializeDropdowns();
        this.initializeDailyClose();
        this.initializeModuleCards();
        this.initializeFormHandlers();
    },

    // Initialize dropdown functionality
    initializeDropdowns() {
        // Custom dropdown handling for better control
        const dropdownToggle = document.getElementById('profileDropdown');
        const dropdownMenu = dropdownToggle?.nextElementSibling;

        if (dropdownToggle && dropdownMenu) {
            // Toggle dropdown on click
            dropdownToggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const isOpen = dropdownMenu.classList.contains('show');
                
                // Close all dropdowns first
                this.closeAllDropdowns();
                
                // Toggle current dropdown
                if (!isOpen) {
                    dropdownMenu.classList.add('show');
                    dropdownToggle.setAttribute('aria-expanded', 'true');
                }
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', (e) => {
                if (!dropdownToggle.contains(e.target) && !dropdownMenu.contains(e.target)) {
                    this.closeAllDropdowns();
                }
            });

            // Close dropdown on escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.closeAllDropdowns();
                }
            });
        }
    },

    // Close all dropdown menus
    closeAllDropdowns() {
        const dropdowns = document.querySelectorAll('.dropdown-menu.show');
        const toggles = document.querySelectorAll('.dropdown-toggle[aria-expanded="true"]');
        
        dropdowns.forEach(dropdown => dropdown.classList.remove('show'));
        toggles.forEach(toggle => toggle.setAttribute('aria-expanded', 'false'));
    },

    // Initialize daily close calculations
    initializeDailyClose() {
        if (!document.getElementById('dailyCloseForm')) return;

        // Get all input fields
        const inputs = {
            mainReading: document.getElementById('mainReading'),
            drSmashed: document.getElementById('drSmashed'),
            ahmadExpenses: document.getElementById('ahmadExpenses'),
            dailyExpenses: document.getElementById('dailyExpenses'),
            dailyAdvances: document.getElementById('dailyAdvances'),
            creditSales: document.getElementById('creditSales'),
            cashback: document.getElementById('cashback')
        };

        // Get calculated field displays
        const displays = {
            adjustedReading: document.getElementById('adjustedReading'),
            fivePercent: document.getElementById('fivePercent'),
            actualCash: document.getElementById('actualCash')
        };

        // Add event listeners for real-time calculations
        Object.values(inputs).forEach(input => {
            if (input) {
                input.addEventListener('input', () => this.calculateValues(inputs, displays));
                input.addEventListener('change', () => this.calculateValues(inputs, displays));
            }
        });

        // Initial calculation
        this.calculateValues(inputs, displays);
    },

    // Calculate all values in real-time
    calculateValues(inputs, displays) {
        try {
            // Get input values with default 0 for empty fields
            const values = {
                mainReading: parseFloat(inputs.mainReading?.value) || 0,
                drSmashed: parseFloat(inputs.drSmashed?.value) || 0,
                ahmadExpenses: parseFloat(inputs.ahmadExpenses?.value) || 0,
                dailyExpenses: parseFloat(inputs.dailyExpenses?.value) || 0,
                dailyAdvances: parseFloat(inputs.dailyAdvances?.value) || 0,
                creditSales: parseFloat(inputs.creditSales?.value) || 0,
                cashback: parseFloat(inputs.cashback?.value) || 0
            };

            // Calculate Adjusted Reading: Main Reading - Dr Smashed - Credit Sales + Cashback
            const adjustedReading = values.mainReading - values.drSmashed - values.creditSales + values.cashback;

            // Calculate 5% of Adjusted Reading
            const fivePercent = adjustedReading * 0.05;

            // Calculate Actual Cash: Adjusted Reading - Ahmad Mistrah - Daily Expenses - Advances
            const actualCash = adjustedReading - values.ahmadExpenses - values.dailyExpenses - values.dailyAdvances;

            // Update display fields
            if (displays.adjustedReading) {
                displays.adjustedReading.textContent = this.formatCurrency(adjustedReading);
            }
            if (displays.fivePercent) {
                displays.fivePercent.textContent = this.formatCurrency(fivePercent);
            }
            if (displays.actualCash) {
                displays.actualCash.textContent = this.formatCurrency(actualCash);
                
                // Add visual feedback for negative values
                if (actualCash < 0) {
                    displays.actualCash.style.background = 'linear-gradient(135deg, #e74c3c, #c0392b)';
                } else {
                    displays.actualCash.style.background = 'linear-gradient(135deg, #f39c12, #e67e22)';
                }
            }

        } catch (error) {
            console.error('Error calculating values:', error);
        }
    },

    // Format number as currency
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
        }).format(amount);
    },

    // Initialize module card interactions
    initializeModuleCards() {
        const moduleCards = document.querySelectorAll('.module-card');
        
        moduleCards.forEach(card => {
            card.addEventListener('click', () => {
                const module = card.dataset.module;
                this.handleModuleClick(module, card);
            });

            // Add keyboard support
            card.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    const module = card.dataset.module;
                    this.handleModuleClick(module, card);
                }
            });

            // Make cards focusable
            card.setAttribute('tabindex', '0');
        });
    },

    // Handle module card clicks
    handleModuleClick(module, cardElement) {
        // Add visual feedback
        cardElement.style.transform = 'scale(0.95)';
        setTimeout(() => {
            cardElement.style.transform = '';
        }, 150);

        // Simulate module loading (prepare for Flask integration)
        this.showStatusMessage(`Loading ${module} module...`, 'info');
        
        // Simulate AJAX call that will later connect to Flask
        this.simulateModuleLoad(module);
    },

    // Simulate module loading (prepare for Flask backend)
    simulateModuleLoad(module) {
        // This simulates what will be an actual AJAX call to Flask backend
        const requestData = {
            module: module,
            timestamp: new Date().toISOString(),
            action: 'load_module'
        };

        // Simulate network delay
        setTimeout(() => {
            console.log(`Module ${module} loaded (simulated)`, requestData);
            this.showStatusMessage(`${module.charAt(0).toUpperCase() + module.slice(1)} module ready`, 'success');
        }, 1000);

        // Future Flask integration point:
        /*
        fetch('/api/modules/' + module, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('Module loaded:', data);
            // Handle module data
        })
        .catch(error => {
            console.error('Error loading module:', error);
            this.showStatusMessage('Error loading module', 'danger');
        });
        */
    },

    // Initialize form handlers
    initializeFormHandlers() {
        const dailyCloseForm = document.getElementById('dailyCloseForm');
        const clearButton = document.getElementById('clearForm');

        if (dailyCloseForm) {
            dailyCloseForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleDailyCloseSubmit();
            });
        }

        if (clearButton) {
            clearButton.addEventListener('click', () => {
                this.clearDailyCloseForm();
            });
        }
    },

    // Handle daily close form submission
    handleDailyCloseSubmit() {
        const formData = this.collectFormData();
        
        if (!this.validateFormData(formData)) {
            this.showStatusMessage('Please fill in all required fields', 'danger');
            return;
        }

        // Show loading state
        this.showStatusMessage('Saving daily close data...', 'info');
        
        // Simulate AJAX submission (prepare for Flask integration)
        this.simulateDailyCloseSubmission(formData);
    },

    // Collect form data
    collectFormData() {
        const inputs = [
            'mainReading', 'drSmashed', 'ahmadExpenses', 'dailyExpenses',
            'dailyAdvances', 'creditSales', 'cashback'
        ];

        const data = {
            timestamp: new Date().toISOString(),
            inputs: {},
            calculations: {}
        };

        inputs.forEach(inputId => {
            const element = document.getElementById(inputId);
            data.inputs[inputId] = parseFloat(element?.value) || 0;
        });

        // Add calculated values
        const adjustedReading = data.inputs.mainReading - data.inputs.drSmashed - data.inputs.creditSales + data.inputs.cashback;
        const fivePercent = adjustedReading * 0.05;
        const actualCash = adjustedReading - data.inputs.ahmadExpenses - data.inputs.dailyExpenses - data.inputs.dailyAdvances;

        data.calculations = {
            adjustedReading,
            fivePercent,
            actualCash
        };

        return data;
    },

    // Validate form data
    validateFormData(data) {
        // Basic validation - ensure main reading is provided
        return data.inputs.mainReading > 0;
    },

    // Simulate daily close submission (prepare for Flask backend)
    simulateDailyCloseSubmission(data) {
        // Simulate network delay
        setTimeout(() => {
            console.log('Daily close submitted (simulated):', data);
            this.showStatusMessage('Daily close saved successfully!', 'success');
        }, 1500);

        // Future Flask integration point:
        /*
        fetch('/api/daily-close', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            console.log('Daily close saved:', result);
            this.showStatusMessage('Daily close saved successfully!', 'success');
        })
        .catch(error => {
            console.error('Error saving daily close:', error);
            this.showStatusMessage('Error saving daily close', 'danger');
        });
        */
    },

    // Clear the daily close form
    clearDailyCloseForm() {
        const inputs = document.querySelectorAll('#dailyCloseForm input[type="number"]');
        inputs.forEach(input => {
            input.value = '';
        });

        // Trigger calculation update to reset calculated fields
        const inputsObj = {
            mainReading: document.getElementById('mainReading'),
            drSmashed: document.getElementById('drSmashed'),
            ahmadExpenses: document.getElementById('ahmadExpenses'),
            dailyExpenses: document.getElementById('dailyExpenses'),
            dailyAdvances: document.getElementById('dailyAdvances'),
            creditSales: document.getElementById('creditSales'),
            cashback: document.getElementById('cashback')
        };

        const displaysObj = {
            adjustedReading: document.getElementById('adjustedReading'),
            fivePercent: document.getElementById('fivePercent'),
            actualCash: document.getElementById('actualCash')
        };

        this.calculateValues(inputsObj, displaysObj);
        this.showStatusMessage('Form cleared', 'info');
    },

    // Show status messages
    showStatusMessage(message, type = 'info') {
        const statusElement = document.getElementById('statusMessage');
        if (!statusElement) return;

        const alertClass = `alert alert-${type === 'info' ? 'primary' : type}`;
        statusElement.className = alertClass;
        statusElement.innerHTML = `
            <i class="fas fa-${this.getStatusIcon(type)} me-2"></i>
            ${message}
        `;
        statusElement.style.display = 'block';

        // Auto-hide success and info messages
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                statusElement.style.display = 'none';
            }, 3000);
        }
    },

    // Get appropriate icon for status type
    getStatusIcon(type) {
        const icons = {
            success: 'check-circle',
            danger: 'exclamation-triangle',
            warning: 'exclamation-circle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
};

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    DailyCloseApp.init();
});

// Export for potential future use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DailyCloseApp;
}
