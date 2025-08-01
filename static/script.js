// Global application object
const DailyCloseApp = {
    // Categories cache
    categoriesCache: {
        expense: [],
        advance: [],
        credit: [],
        cashback: [],
        'samer-expense': []
    },

    // Initialize the application
    init() {
        this.initializeDropdowns();
        this.initializeDailyClose();
        this.initializeModuleCards();
        this.initializeFormHandlers();
        this.initializeSimpleExpenseSections();
        this.initializeDateHandling();
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
            ahmadExpenses: document.getElementById('ahmadExpenses')
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
                input.addEventListener('input', () => this.calculateValues());
                input.addEventListener('change', () => this.calculateValues());
            }
        });

        // Initial calculation
        this.calculateValues();
    },

    // Calculate all values in real-time
    calculateValues() {
        try {
            // Get basic input values
            const mainReading = parseFloat(document.getElementById('mainReading')?.value) || 0;
            const drSmashed = parseFloat(document.getElementById('drSmashed')?.value) || 0;
            const ahmadExpenses = parseFloat(document.getElementById('ahmadExpenses')?.value) || 0;

            // Calculate totals from sections
            const totalExpenses = this.calculateSectionTotal('.expense-amount');
            const totalAdvances = this.calculateSectionTotal('.advance-amount');
            const totalCredits = this.calculateSectionTotal('.credit-amount');
            const totalCashback = this.calculateSectionTotal('.cashback-amount');
            const totalSamerExpenses = this.calculateSectionTotal('.samer-expense-amount');

            // Update section totals
            this.updateSectionTotal('#totalExpenses', totalExpenses);
            this.updateSectionTotal('#totalAdvances', totalAdvances);
            this.updateSectionTotal('#totalCredits', totalCredits);
            this.updateSectionTotal('#totalCashback', totalCashback);
            this.updateSectionTotal('#totalSamerExpenses', totalSamerExpenses);

            // Calculate Adjusted Reading: Main Reading - Dr Smashed - Total Credits + Total Cashback
            const adjustedReading = mainReading - drSmashed - totalCredits + totalCashback;

            // Calculate 5% of Adjusted Reading
            const fivePercent = adjustedReading * 0.05;

            // Calculate Actual Cash: Adjusted Reading - Ahmad Mistrah - Total Expenses - Total Advances - Total Samer Expenses
            const actualCash = adjustedReading - ahmadExpenses - totalExpenses - totalAdvances - totalSamerExpenses;

            // Update calculated field displays
            const displays = {
                adjustedReading: document.getElementById('adjustedReading'),
                fivePercent: document.getElementById('fivePercent'),
                actualCash: document.getElementById('actualCash')
            };

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

    // Calculate total for a section
    calculateSectionTotal(selector) {
        const inputs = document.querySelectorAll(selector);
        let total = 0;
        inputs.forEach(input => {
            total += parseFloat(input.value) || 0;
        });
        return total;
    },

    // Update section total display
    updateSectionTotal(selector, total) {
        const element = document.querySelector(selector);
        if (element) {
            element.textContent = this.formatCurrency(total);
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

    // Submit daily close form
    async submitDailyClose() {
        try {
            const closeDate = document.getElementById('closeDate')?.value;
            
            // Collect basic inputs
            const basicInputs = {
                close_date: closeDate,
                main_reading: parseFloat(document.getElementById('mainReading')?.value) || 0,
                dr_smashed: parseFloat(document.getElementById('drSmashed')?.value) || 0,
                ahmad_expenses: parseFloat(document.getElementById('ahmadExpenses')?.value) || 0
            };

            // Collect expense data
            const expenses = this.collectSectionData('.expense-item', '.expense-category', '.expense-amount');
            const advances = this.collectSectionData('.advance-item', '.advance-category', '.advance-amount');
            const credits = this.collectSectionData('.credit-item', '.credit-category', '.credit-amount');
            const cashbacks = this.collectSectionData('.cashback-item', '.cashback-category', '.cashback-amount');
            const samer_expenses = this.collectSectionData('.samer-expense-item', '.samer-expense-category', '.samer-expense-amount');

            // Calculate totals and calculated fields
            const calculations = {
                adjusted_reading: parseFloat(document.getElementById('adjustedReading')?.textContent.replace('$', '').replace(',', '')) || 0,
                five_percent: parseFloat(document.getElementById('fivePercent')?.textContent.replace('$', '').replace(',', '')) || 0,
                actual_cash: parseFloat(document.getElementById('actualCash')?.textContent.replace('$', '').replace(',', '')) || 0
            };

            // Calculate totals from individual sections
            const totalExpenses = this.calculateSectionTotal('.expense-amount');
            const totalAdvance = this.calculateSectionTotal('.advance-amount');
            const totalCredit = this.calculateSectionTotal('.credit-amount');
            const totalCashback = this.calculateSectionTotal('.cashback-amount');

            const formData = {
                date: closeDate,
                total_expenses: totalExpenses,
                total_advance: totalAdvance,
                total_credit: totalCredit,
                total_cashback: totalCashback,
                five_percent: calculations.five_percent,
                total_cashout: totalExpenses + totalAdvance, // Simple calculation
                actual_cash: calculations.actual_cash,
                expenses: expenses // Individual expense records
            };

            this.showStatusMessage('Saving daily close data...', 'info');

            const response = await fetch('/api/daily-closing', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                this.showStatusMessage('Daily close saved successfully', 'success');
                this.clearDailyCloseForm();
            } else {
                this.showStatusMessage('Error saving daily close: ' + (data.message || 'Unknown error'), 'danger');
            }
        } catch (error) {
            console.error('Error submitting daily close:', error);
            this.showStatusMessage('Error saving daily close', 'danger');
        }
    },

    // Collect section data for submission
    collectSectionData(itemSelector, categorySelector, amountSelector) {
        const items = document.querySelectorAll(itemSelector);
        const data = [];
        
        items.forEach(item => {
            const categorySelect = item.querySelector(categorySelector);
            const amountInput = item.querySelector(amountSelector);
            
            if (categorySelect && amountInput && categorySelect.value && amountInput.value) {
                data.push({
                    category_id: parseInt(categorySelect.value),
                    amount: parseFloat(amountInput.value) || 0,
                    description: ''
                });
            }
        });
        
        return data;
    },

    // Clear the daily close form
    clearDailyCloseForm() {
        // Clear basic input fields
        const inputs = document.querySelectorAll('#dailyCloseForm input[type="number"]');
        inputs.forEach(input => {
            input.value = '';
        });

        // Reset date to today and lock it
        const dateInput = document.getElementById('closeDate');
        const editBtn = document.getElementById('editDateBtn');
        if (dateInput && editBtn) {
            const today = new Date().toISOString().split('T')[0];
            dateInput.value = today;
            dateInput.setAttribute('readonly', 'readonly');
            editBtn.innerHTML = '<i class="fas fa-edit"></i> Edit';
            editBtn.onclick = () => this.showAdminPasswordModal();
        }

        // Clear all description fields
        const descriptions = document.querySelectorAll('#dailyCloseForm input[type="text"]');
        descriptions.forEach(input => {
            if (input.id !== 'closeDate') { // Don't clear the date field
                input.value = '';
            }
        });

        // Reset all expense sections to single items
        this.resetExpenseSection('#expensesSection', 'expense');
        this.resetExpenseSection('#advancesSection', 'advance');
        this.resetExpenseSection('#creditsSection', 'credit');
        this.resetExpenseSection('#cashbacksSection', 'cashback');
        this.resetExpenseSection('#samerExpensesSection', 'samer-expense');

        // Recalculate values
        this.calculateValues();
        this.showStatusMessage('Form cleared', 'info');
    },

    // Reset expense section to single item
    resetExpenseSection(sectionSelector, type) {
        const section = document.querySelector(sectionSelector);
        if (!section) return;

        const items = section.querySelectorAll('[class*="item"]');
        
        // Remove all items except the first one
        items.forEach((item, index) => {
            if (index > 0) {
                item.remove();
            }
        });

        // Clear the first item
        const firstItem = section.querySelector('[class*="item"]');
        if (firstItem) {
            const select = firstItem.querySelector('select');
            const input = firstItem.querySelector('input[type="number"]');
            if (select) select.selectedIndex = 0;
            if (input) input.value = '';
        }

        // Update remove button visibility
        this.updateRemoveButtons(sectionSelector);
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
    },

    // Initialize simplified expense sections
    initializeSimpleExpenseSections() {
        if (!document.getElementById('dailyCloseForm')) return;

        // Add event listeners for add/remove buttons
        this.initializeSectionButtons('.add-expense', '.remove-expense', '#expensesSection', 'expense');
        this.initializeSectionButtons('.add-advance', '.remove-advance', '#advancesSection', 'advance');
        this.initializeSectionButtons('.add-credit', '.remove-credit', '#creditsSection', 'credit');
        this.initializeSectionButtons('.add-cashback', '.remove-cashback', '#cashbacksSection', 'cashback');
        this.initializeSectionButtons('.add-samer-expense', '.remove-samer-expense', '#samerExpensesSection', 'samer-expense');

        // Add event listeners for calculations
        this.initializeSimpleCalculationHandlers();
    },

    // Initialize section buttons
    initializeSectionButtons(addSelector, removeSelector, sectionSelector, type) {
        document.addEventListener('click', (e) => {
            if (e.target.closest(addSelector)) {
                e.preventDefault();
                this.addSectionItem(sectionSelector, type);
            }
            
            if (e.target.closest(removeSelector)) {
                e.preventDefault();
                this.removeSectionItem(e.target.closest(removeSelector), sectionSelector);
            }
        });
    },

    // Add section item
    addSectionItem(sectionSelector, type) {
        const section = document.querySelector(sectionSelector);
        if (!section) return;

        const template = this.getSectionTemplate(type);
        section.insertAdjacentHTML('beforeend', template);

        // Update dropdown for new item
        setTimeout(() => {
            this.updateCategoryDropdowns(type);
            this.updateRemoveButtons(sectionSelector);
        }, 10);
    },

    // Remove section item
    removeSectionItem(button, sectionSelector) {
        const item = button.closest(`[class*="${sectionSelector.slice(1).replace('Section', '-item')}"]`);
        if (item) {
            item.remove();
            this.updateRemoveButtons(sectionSelector);
            this.calculateValues(); // Recalculate totals
        }
    },

    // Update remove buttons visibility
    updateRemoveButtons(sectionSelector) {
        const section = document.querySelector(sectionSelector);
        if (!section) return;

        const items = section.querySelectorAll('[class*="item"]');
        items.forEach((item, index) => {
            const removeBtn = item.querySelector('.btn-outline-danger');
            if (removeBtn) {
                removeBtn.style.display = items.length > 1 ? 'block' : 'none';
            }
        });
    },

    // Get section template
    getSectionTemplate(type) {
        const templates = {
            'expense': `
                <div class="expense-item mb-3">
                    <div class="row g-2">
                        <div class="col-md-5">
                            <select class="form-control expense-category" data-type="expense">
                                <option value="">Select or type expense category</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <div class="input-group">
                                <span class="input-group-text">$</span>
                                <input type="number" class="form-control expense-amount" placeholder="0.00" step="0.01">
                            </div>
                        </div>
                        <div class="col-md-2">
                            <button type="button" class="btn btn-outline-success add-expense" title="Add Expense">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                        <div class="col-md-1">
                            <button type="button" class="btn btn-outline-danger remove-expense" title="Remove Expense">
                                <i class="fas fa-minus"></i>
                            </button>
                        </div>
                    </div>
                </div>`,
            'advance': `
                <div class="advance-item mb-3">
                    <div class="row g-2">
                        <div class="col-md-5">
                            <select class="form-control advance-category" data-type="advance">
                                <option value="">Select or type advance category</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <div class="input-group">
                                <span class="input-group-text">$</span>
                                <input type="number" class="form-control advance-amount" placeholder="0.00" step="0.01">
                            </div>
                        </div>
                        <div class="col-md-2">
                            <button type="button" class="btn btn-outline-success add-advance" title="Add Advance">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                        <div class="col-md-1">
                            <button type="button" class="btn btn-outline-danger remove-advance" title="Remove Advance">
                                <i class="fas fa-minus"></i>
                            </button>
                        </div>
                    </div>
                </div>`,
            'credit': `
                <div class="credit-item mb-3">
                    <div class="row g-2">
                        <div class="col-md-5">
                            <select class="form-control credit-category" data-type="credit">
                                <option value="">Select or type credit category</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <div class="input-group">
                                <span class="input-group-text">$</span>
                                <input type="number" class="form-control credit-amount" placeholder="0.00" step="0.01">
                            </div>
                        </div>
                        <div class="col-md-2">
                            <button type="button" class="btn btn-outline-success add-credit" title="Add Credit">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                        <div class="col-md-1">
                            <button type="button" class="btn btn-outline-danger remove-credit" title="Remove Credit">
                                <i class="fas fa-minus"></i>
                            </button>
                        </div>
                    </div>
                </div>`,
            'cashback': `
                <div class="cashback-item mb-3">
                    <div class="row g-2">
                        <div class="col-md-5">
                            <select class="form-control cashback-category" data-type="cashback">
                                <option value="">Select or type cashback category</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <div class="input-group">
                                <span class="input-group-text">$</span>
                                <input type="number" class="form-control cashback-amount" placeholder="0.00" step="0.01">
                            </div>
                        </div>
                        <div class="col-md-2">
                            <button type="button" class="btn btn-outline-success add-cashback" title="Add Cashback">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                        <div class="col-md-1">
                            <button type="button" class="btn btn-outline-danger remove-cashback" title="Remove Cashback">
                                <i class="fas fa-minus"></i>
                            </button>
                        </div>
                    </div>
                </div>`,
            'samer-expense': `
                <div class="samer-expense-item mb-3">
                    <div class="row g-2">
                        <div class="col-md-5">
                            <select class="form-control samer-expense-category" data-type="samer-expense">
                                <option value="">Select or type Samer's expense category</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <div class="input-group">
                                <span class="input-group-text">$</span>
                                <input type="number" class="form-control samer-expense-amount" placeholder="0.00" step="0.01">
                            </div>
                        </div>
                        <div class="col-md-2">
                            <button type="button" class="btn btn-outline-success add-samer-expense" title="Add Samer Expense">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                        <div class="col-md-1">
                            <button type="button" class="btn btn-outline-danger remove-samer-expense" title="Remove Samer Expense">
                                <i class="fas fa-minus"></i>
                            </button>
                        </div>
                    </div>
                </div>`
        };

        return templates[type] || '';
    },

    // Initialize simplified calculation handlers
    initializeSimpleCalculationHandlers() {
        // Handle input events for real-time calculation
        document.addEventListener('input', (e) => {
            if (e.target.matches('.expense-amount, .advance-amount, .credit-amount, .cashback-amount, .samer-expense-amount')) {
                this.calculateValues();
            }
        });
    },

    // Initialize date handling
    initializeDateHandling() {
        if (!document.getElementById('closeDate')) return;

        // Set today's date
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('closeDate').value = today;

        // Add event listener for edit date button
        const editDateBtn = document.getElementById('editDateBtn');
        if (editDateBtn) {
            editDateBtn.addEventListener('click', () => {
                this.showAdminPasswordModal();
            });
        }

        // Handle enter key in password field
        const adminPasswordInput = document.getElementById('adminPassword');
        if (adminPasswordInput) {
            adminPasswordInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.verifyAdminPassword();
                }
            });
        }
    },

    // Show admin password modal
    showAdminPasswordModal() {
        const modal = new bootstrap.Modal(document.getElementById('adminPasswordModal'));
        document.getElementById('adminPassword').value = '';
        document.getElementById('passwordError').classList.add('d-none');
        modal.show();
        
        // Focus on password field when modal is shown
        setTimeout(() => {
            document.getElementById('adminPassword').focus();
        }, 500);
    },

    // Verify admin password
    verifyAdminPassword() {
        const password = document.getElementById('adminPassword').value;
        const adminPassword = 'admin123'; // This should be stored securely in production
        
        if (password === adminPassword) {
            // Correct password - unlock date field
            const dateInput = document.getElementById('closeDate');
            const editBtn = document.getElementById('editDateBtn');
            
            dateInput.removeAttribute('readonly');
            dateInput.focus();
            editBtn.innerHTML = '<i class="fas fa-lock"></i> Lock';
            editBtn.onclick = () => this.lockDateField();
            
            // Hide modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('adminPasswordModal'));
            modal.hide();
            
            this.showStatusMessage('Date field unlocked for editing', 'success');
        } else {
            // Incorrect password
            document.getElementById('passwordError').classList.remove('d-none');
            document.getElementById('adminPassword').value = '';
            document.getElementById('adminPassword').focus();
        }
    },

    // Lock date field
    lockDateField() {
        const dateInput = document.getElementById('closeDate');
        const editBtn = document.getElementById('editDateBtn');
        
        dateInput.setAttribute('readonly', 'readonly');
        editBtn.innerHTML = '<i class="fas fa-edit"></i> Edit';
        editBtn.onclick = () => this.showAdminPasswordModal();
        
        this.showStatusMessage('Date field locked', 'info');
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
