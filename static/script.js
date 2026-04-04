/**
 * Global Toast Notification System
 * @param {string} title - The title of the toast (or message if no title)
 * @param {string} message - The message to display (optional if only title is passed)
 * @param {string} type - Toast type (success, error, warning, info)
 * @param {number} duration - Auto-close duration in ms (default 4000)
 */
window.showToast = function (title, message = '', type = 'info', duration = 4000) {
    // If only two arguments are passed, assume they are message and type
    if (arguments.length === 2 && !['success', 'error', 'warning', 'info'].includes(message)) {
        type = message;
        message = title;
        title = type.charAt(0).toUpperCase() + type.slice(1);
    } else if (arguments.length === 1) {
        message = title;
        title = 'Notification';
    }

    const toastId = 'toast-' + Date.now();
    const typeConfigs = {
        success: { icon: 'check_circle', colorClass: 'text-emerald-500', bgClass: 'bg-emerald-50 dark:bg-emerald-500/10', borderClass: 'border-emerald-200 dark:border-emerald-500/20' },
        error: { icon: 'error', colorClass: 'text-red-500', bgClass: 'bg-red-50 dark:bg-red-500/10', borderClass: 'border-red-200 dark:border-red-500/20' },
        warning: { icon: 'warning', colorClass: 'text-orange-500', bgClass: 'bg-orange-50 dark:bg-orange-500/10', borderClass: 'border-orange-200 dark:border-orange-500/20' },
        info: { icon: 'info', colorClass: 'text-blue-500', bgClass: 'bg-blue-50 dark:bg-blue-500/10', borderClass: 'border-blue-200 dark:border-blue-500/20' }
    };
    const config = typeConfigs[type] || typeConfigs.info;

    const toastHtml = `
        <div id="${toastId}" class="flex items-start gap-3 p-4 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-100 dark:border-slate-700 pointer-events-auto transition-all duration-300 transform translate-x-full opacity-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="flex-shrink-0 p-2 rounded-lg ${config.bgClass} ${config.borderClass}">
                <span class="material-symbols-outlined ${config.colorClass}">${config.icon}</span>
            </div>
            <div class="flex-1 pt-1 min-w-0">
                <p class="text-sm font-semibold text-slate-900 dark:text-white capitalize">${title}</p>
                ${message ? `<p class="text-sm text-slate-500 dark:text-slate-400 mt-1">${message}</p>` : ''}
            </div>
            <div class="flex-shrink-0 flex items-start">
                <button type="button" class="inline-flex rounded-md bg-transparent text-slate-400 hover:text-slate-500 focus:outline-none" onclick="document.getElementById('${toastId}').remove()">
                    <span class="material-symbols-outlined text-sm">close</span>
                </button>
            </div>
            <div class="absolute bottom-0 left-0 h-1 bg-slate-200 dark:bg-slate-700 w-full rounded-b-xl overflow-hidden">
                <div class="h-full ${config.bgClass.split(' ')[0].replace('bg-', 'bg-').replace('50', '500')} animate-toast-progress" style="animation-duration: ${duration}ms"></div>
            </div>
        </div>
    `;

    // Create container if it doesn't exist
    let container = document.getElementById('global-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'global-toast-container';
        container.className = 'fixed top-4 right-4 z-[9999] flex flex-col gap-3 w-full max-w-sm pointer-events-none';
        document.body.appendChild(container);
    }

    // Add alert to container
    container.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.getElementById(toastId);

    // Trigger animation (Slide in)
    requestAnimationFrame(() => {
        toastElement.classList.remove('translate-x-full', 'opacity-0');
    });

    // Auto-close if duration > 0
    if (duration > 0) {
        setTimeout(() => {
            if (toastElement) {
                // Slide out animation
                toastElement.classList.add('opacity-0', 'translate-x-[120%]');
                setTimeout(() => toastElement.remove(), 300);
            }
        }, duration);
    }
}

// Map showAlert to showToast for backward compatibility
window.showAlert = function (message, type = 'error', duration = 4000) {
    if (type === 'danger') type = 'error';
    window.showToast(type, message, type, duration);
};



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

    // List caches for dropdowns
    employees: [],
    customers: [],
    receivers: [],
    samerReceivers: [],

    // Edit mode state
    editMode: false,
    currentClosingDate: null,

    // Initialize the application
    init() {
        this.initializeDropdowns();
        this.initializeDailyClose();
        this.initializeModuleCards();
        this.initializeFormHandlers();

        // Fetch all identity lists first, then initialize sections
        this.fetchAllLists().then(() => {
            this.initializeSimpleExpenseSections();
        });

        this.initializeDateHandling();
        this.checkAdminValidation();

        // Check for specific date in URL or use today
        const urlParams = new URLSearchParams(window.location.search);
        let urlDate = urlParams.get('date');

        if (!urlDate) {
            urlDate = new Date().toISOString().split('T')[0];
        }

        const dateInput = document.getElementById('closeDate');
        if (dateInput) {
            dateInput.value = urlDate;
            this.fetchDailyClosingData(urlDate);
        }
    },

    // Fetch all active entities for selects
    async fetchAllLists() {
        try {
            const [emps, custs, recs, samer, ahmad] = await Promise.all([
                fetch('/api/employees/list').then(response => response.ok ? response.json() : []),
                fetch('/api/customers/list').then(response => response.ok ? response.json() : []),
                fetch('/api/receivers/list').then(response => response.ok ? response.json() : []),
                fetch('/api/samer-receivers/list').then(response => response.ok ? response.json() : []),
                fetch('/api/ahmad-receivers/list').then(response => response.ok ? response.json() : [])
            ]);

            this.employees = emps;
            this.customers = custs;
            this.receivers = recs;
            this.samerReceivers = samer;
            this.ahmadReceivers = ahmad;
        } catch (error) {
            console.error('Error fetching list data:', error);
        }
    },

    // Initialize a TomSelect dropdown generically
    initializeGenericSelect(element, dataList, placeholder, selectedId = null) {
        if (!element || element.tomselect) return;

        const ts = new TomSelect(element, {
            valueField: 'id',
            labelField: 'name',
            searchField: 'name',
            options: dataList,
            create: false,
            placeholder: placeholder,
            maxItems: 1,
            render: {
                option: function (data, escape) {
                    return '<div>' + escape(data.name) + '</div>';
                },
                item: function (data, escape) {
                    return '<div>' + escape(data.name) + '</div>';
                }
            }
        });

        if (selectedId) {
            ts.setValue(selectedId);
        }

        return ts;
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
            drSmashed: document.getElementById('drSmashed')
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
            const mainReading = parseFloat(document.getElementById('mainReading')?.value) || 0;

            // Calculate totals from sections
            const totalExpenses = this.calculateSectionTotal('.expense-amount');
            const totalAdvances = this.calculateSectionTotal('.advance-amount');
            const totalDeductions = this.calculateSectionTotal('.deduction-amount');
            const totalCredits = this.calculateSectionTotal('.credit-amount');
            const totalCashback = this.calculateSectionTotal('.cashback-amount');
            const totalSamerExpenses = this.calculateSectionTotal('.samer-expense-amount');

            // Update section totals
            this.updateSectionTotal('#totalExpenses', totalExpenses);
            this.updateSectionTotal('#totalAdvances', totalAdvances);
            this.updateSectionTotal('#totalDeductions', totalDeductions);
            this.updateSectionTotal('#totalCredits', totalCredits);
            this.updateSectionTotal('#totalCashback', totalCashback);
            this.updateSectionTotal('#totalSamerExpenses', totalSamerExpenses);

            // Calculate Adjusted Reading: Main Reading - Total Credits + Total Cashback
            const adjustedReading = mainReading - totalCredits + totalCashback;

            // Calculate 5% of Adjusted Reading
            const fivePercent = adjustedReading * 0.05;

            // Calculate Actual Cash: Adjusted Reading - Total Expenses - Total Advances - Total Samer Expenses
            const actualCash = adjustedReading - totalExpenses - totalAdvances - totalSamerExpenses;

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

        // Actual submission to Flask API
        this.submitDailyClose();
    },

    // Collect form data
    collectFormData() {
        const inputs = [
            'mainReading', 'drSmashed', 'dailyExpenses',
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
        const totalDeductions = this.calculateSectionTotal('.deduction-amount');
        const actualCash = adjustedReading - data.inputs.dailyExpenses - data.inputs.dailyAdvances;

        data.calculations = {
            adjustedReading,
            fivePercent,
            actualCash,
            totalDeductions
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
        const submitBtn = document.getElementById('submitCloseBtn');
        try {
            const closeDate = document.getElementById('closeDate')?.value;

            // Collect basic inputs
            const basicInputs = {
                close_date: closeDate,
                main_reading: parseFloat(document.getElementById('mainReading')?.value) || 0
            };

            // Collect expense data with proper types for automatic creation
            const expenses = this.collectSectionData('.expense-item', '.expense-description', '.expense-amount', 'expense');
            const advances = this.collectSectionData('.advance-item', '.advance-description', '.advance-amount', 'advance');
            const credits = this.collectSectionData('.credit-item', '.credit-description', '.credit-amount', 'credit');
            const cashbacks = this.collectSectionData('.cashback-item', '.cashback-description', '.cashback-amount', 'cashback');
            const samer_expenses = this.collectSectionData('.samer-expense-item', '.samer-expense-description', '.samer-expense-amount', 'samer-expense');

            // Calculate totals and calculated fields
            const calculations = {
                adjusted_reading: parseFloat(document.getElementById('adjustedReading')?.textContent.replace('$', '').replace(',', '')) || 0,
                five_percent: parseFloat(document.getElementById('fivePercent')?.textContent.replace('$', '').replace(',', '')) || 0,
                actual_cash: parseFloat(document.getElementById('actualCash')?.textContent.replace('$', '').replace(',', '')) || 0
            };

            // Calculate totals from individual sections
            const totalGenExpenses = this.calculateSectionTotal('.expense-amount');
            const totalAdvance = this.calculateSectionTotal('.advance-amount');
            const totalDeductions = this.calculateSectionTotal('.deduction-amount');
            const totalCredit = this.calculateSectionTotal('.credit-amount');
            const totalCashback = this.calculateSectionTotal('.cashback-amount');
            const totalSamerExpenses = this.calculateSectionTotal('.samer-expense-amount');

            const totalTotalExpenses = totalGenExpenses + totalSamerExpenses;

            // Collect deductions data
            const deductions = this.collectSectionData('.deduction-item', '.deduction-description', '.deduction-amount', 'deduction');

            const formData = {
                date: closeDate,
                main_reading: basicInputs.main_reading,
                dr_smashed: 0,
                adjusted_reading: calculations.adjusted_reading,
                total_expenses: totalTotalExpenses,
                total_advance: totalAdvance,
                total_deductions: totalDeductions,
                total_credit: totalCredit,
                total_cashback: totalCashback,
                five_percent: calculations.five_percent,
                total_cashout: totalTotalExpenses + totalAdvance + totalDeductions,
                actual_cash: calculations.actual_cash,
                expenses: expenses,
                advances: advances,
                deductions: deductions,
                credits: credits,
                cashbacks: cashbacks,
                samer_expenses: samer_expenses
            };

            // Validation: Ensure main reading is provided
            if (!(formData.main_reading > 0)) {
                this.showStatusMessage('Main Reading is mandatory. Please enter the current counter value.', 'warning');
                return;
            }

            // Validation: Ensure there's at least some data
            const hasData = formData.main_reading > 0 ||
                formData.expenses.length > 0 ||
                formData.advances.length > 0 ||
                formData.deductions.length > 0 ||
                formData.credits.length > 0 ||
                formData.cashbacks.length > 0 ||
                formData.samer_expenses.length > 0;

            if (!hasData) {
                this.showStatusMessage('Cannot submit an empty daily close. Please enter at least one value.', 'warning');
                return;
            }

            // Disable submit button to prevent duplicate submissions
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
            }

            this.showStatusMessage('Saving daily close data...', 'info');

            const method = this.editMode ? 'PUT' : 'POST';
            const url = this.editMode ? `/api/daily-closing/${this.currentClosingDate}` : '/api/daily-closing';

            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (response.ok && data.status === 'success') {
                const actionText = this.editMode ? 'updated' : 'saved';
                this.showStatusMessage(`Daily close ${actionText} successfully! Redirecting to print view...`, 'success');
                this.clearDailyCloseForm();

                // Keep toast visible shortly before redirecting
                const redirectId = data.id || data.data?.id;
                setTimeout(() => {
                    window.location.href = `/control-panel/daily-close/${redirectId}/print`;
                }, 1000);
            } else {
                this.showStatusMessage('Error saving daily close: ' + (data.message || data.error || 'Unknown error'), 'danger');
            }
        } catch (error) {
            console.error('Error submitting daily close:', error);
            this.showStatusMessage('Error saving daily close: ' + error.message, 'danger');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                const originalText = this.editMode ? 'Update Daily Close' : 'Save Daily Close';
                submitBtn.innerHTML = `<span class="material-symbols-outlined">save</span> ${originalText}`;
            }
        }
    },

    // Collect section data for submission
    collectSectionData(itemSelector, descriptionSelector, amountSelector, type = 'expense') {
        const items = document.querySelectorAll(itemSelector);
        const data = [];

        items.forEach(item => {
            const descriptionInput = item.querySelector(descriptionSelector);
            const noteInput = item.querySelector(`.${type}-note`);
            const amountInput = item.querySelector(amountSelector);

            // For selects, value is the ID. For text inputs, value is the string.
            const descValue = descriptionInput ? descriptionInput.value.trim() : '';

            if (descriptionInput && amountInput && descValue && amountInput.value) {
                const baseData = {
                    amount: parseFloat(amountInput.value) || 0,
                    note: noteInput ? noteInput.value.trim() : ''
                };

                // Add type-specific data
                if (type === 'expense' || type === 'samer-expense') {
                    baseData.receiver_id = descValue;
                } else if (type === 'credit' || type === 'cashback') {
                    baseData.customer_id = descValue;
                } else if (type === 'advance' || type === 'deduction') {
                    baseData.employee_id = descValue;
                }

                data.push(baseData);
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
        this.resetExpenseSection('#deductionsSection', 'deduction');
        this.resetExpenseSection('#creditsSection', 'credit');
        this.resetExpenseSection('#cashbacksSection', 'cashback');
        this.resetExpenseSection('#samerExpensesSection', 'samer-expense');

        // Recalculate values
        this.calculateValues();

        // Reset edit mode
        this.editMode = false;
        this.currentClosingDate = null;
        const submitBtn = document.getElementById('submitCloseBtn');
        if (submitBtn) submitBtn.innerHTML = '<span class="material-symbols-outlined">save</span> Save Daily Close';

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
                // Destroy TomSelect instance to prevent memory leaks if present
                const select = item.querySelector('.employee-select');
                if (select && select.tomselect) {
                    select.tomselect.destroy();
                }
                item.remove();
            }
        });

        // Clear the first item
        const firstItem = section.querySelector('[class*="item"]');
        if (firstItem) {
            const select = firstItem.querySelector('select');
            const input = firstItem.querySelector('input[type="number"]');

            if (select) {
                if (select.tomselect) {
                    select.tomselect.clear(true);
                } else {
                    select.selectedIndex = 0;
                }
            }
            if (input) input.value = '';

            // Note: the master clearDailyCloseForm() already handles traditional input[type="text"]
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
        this.initializeSectionButtons('.add-deduction', '.remove-deduction', '#deductionsSection', 'deduction');
        this.initializeSectionButtons('.add-credit', '.remove-credit', '#creditsSection', 'credit');
        this.initializeSectionButtons('.add-cashback', '.remove-cashback', '#cashbacksSection', 'cashback');
        this.initializeSectionButtons('.add-samer-expense', '.remove-samer-expense', '#samerExpensesSection', 'samer-expense');

        // Initialize remove buttons for existing items
        this.updateRemoveButtons('#expensesSection');
        this.updateRemoveButtons('#advancesSection');
        this.updateRemoveButtons('#deductionsSection');
        this.updateRemoveButtons('#creditsSection');
        this.updateRemoveButtons('#cashbacksSection');
        this.updateRemoveButtons('#samerExpensesSection');

        // Initialize all select elements
        document.querySelectorAll('.employee-select').forEach(select => {
            this.initializeGenericSelect(select, this.employees, 'Select Employee...');
        });
        document.querySelectorAll('.receiver-select').forEach(select => {
            this.initializeGenericSelect(select, this.receivers, 'Select Receiver...');
        });
        document.querySelectorAll('.samer-receiver-select').forEach(select => {
            this.initializeGenericSelect(select, this.samerReceivers, 'Select Samer Receiver...');
        });
        document.querySelectorAll('.customer-select').forEach(select => {
            this.initializeGenericSelect(select, this.customers, 'Select Customer...');
        });

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
            this.updateRemoveButtons(sectionSelector);

            // Initialize TomSelect if it's a dropdown
            const newItem = section.lastElementChild;
            if (newItem.querySelector('.employee-select')) {
                this.initializeGenericSelect(newItem.querySelector('.employee-select'), this.employees, 'Select Employee...');
            } else if (newItem.querySelector('.receiver-select')) {
                this.initializeGenericSelect(newItem.querySelector('.receiver-select'), this.receivers, 'Select Receiver...');
            } else if (newItem.querySelector('.samer-receiver-select')) {
                this.initializeGenericSelect(newItem.querySelector('.samer-receiver-select'), this.samerReceivers, 'Select Samer Receiver...');
            } else if (newItem.querySelector('.customer-select')) {
                this.initializeGenericSelect(newItem.querySelector('.customer-select'), this.customers, 'Select Customer...');
            }
        }, 10);
    },

    // Remove section item
    removeSectionItem(button, sectionSelector) {
        // Find the item that contains the remove button
        const item = button.closest('[class*="-item"]');
        if (item) {
            item.remove();
            this.updateRemoveButtons(sectionSelector);
            this.calculateValues(); // Recalculate totals
        } else {
            console.error('Could not find item to remove');
        }
    },

    // Update remove buttons visibility
    updateRemoveButtons(sectionSelector) {
        const section = document.querySelector(sectionSelector);
        if (!section) return;

        const items = section.querySelectorAll('[class*="item"]');
        items.forEach((item, index) => {
            const removeBtn = Array.from(item.querySelectorAll('button')).find(btn => btn.className.match(/remove-/));
            if (removeBtn) {
                // Always show remove button, even for first item
                removeBtn.style.display = 'block';
            }
        });
    },

    // Get section template
    getSectionTemplate(type) {
        const templates = {
            'expense': `
                <div class="expense-item flex flex-wrap md:flex-nowrap gap-4 items-center p-3 bg-slate-50 dark:bg-slate-800/30 rounded-lg">
                    <div class="flex-1 min-w-[200px] flex gap-2">
                        <select class="w-full receiver-select expense-description" data-placeholder="Select Receiver..."></select>
                        <button type="button" class="px-2 py-1 bg-primary text-white rounded-md hover:bg-blue-600 transition-colors tooltip" title="Add New Receiver" onclick="DailyCloseApp.openNewReceiverModal(this, 'general')">
                            <span class="material-symbols-outlined text-sm">person_add</span>
                        </button>
                    </div>
                    <input type="text"
                        class="flex-[1.5] min-w-[200px] rounded-lg border-slate-200 dark:border-slate-700 dark:bg-slate-800 text-sm focus:border-primary focus:ring-primary expense-note"
                        placeholder="Note/Details" />
                    <div class="relative w-32 shrink-0">
                        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-medium">$</span>
                        <input type="number"
                            class="w-full pl-7 rounded-lg border-slate-200 dark:border-slate-700 dark:bg-slate-800 text-sm focus:border-primary focus:ring-primary text-right expense-amount"
                            placeholder="0.00" />
                    </div>
                    <div class="flex gap-2">
                        <button type="button" class="text-emerald-500 hover:text-emerald-600 add-expense" title="Add Item">
                            <span class="material-symbols-outlined">add_circle</span>
                        </button>
                        <button type="button" class="text-slate-300 hover:text-red-500 remove-expense" title="Remove Item">
                            <span class="material-symbols-outlined">delete</span>
                        </button>
                    </div>
                </div>`,
            'advance': `
                <div class="advance-item flex flex-wrap md:flex-nowrap gap-4 items-center p-3 bg-slate-50 dark:bg-slate-800/30 rounded-lg">
                    <div class="flex-1 min-w-[200px] flex gap-2">
                        <select class="w-full employee-select advance-description" data-placeholder="Select Employee..."></select>
                        <button type="button" class="px-2 py-1 bg-primary text-white rounded-md hover:bg-blue-600 transition-colors tooltip" title="Add New Employee" onclick="DailyCloseApp.openNewEmployeeModal(this)">
                            <span class="material-symbols-outlined text-sm">person_add</span>
                        </button>
                    </div>
                    <input type="text"
                        class="flex-[1.5] min-w-[200px] rounded-lg border-slate-200 dark:border-slate-700 dark:bg-slate-800 text-sm focus:border-primary focus:ring-primary advance-note"
                        placeholder="Note/Reason" />
                    <div class="relative w-32 shrink-0">
                        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-medium">$</span>
                        <input type="number" step="any"
                            class="w-full pl-7 rounded-lg border-slate-200 dark:border-slate-700 dark:bg-slate-800 text-sm focus:border-primary focus:ring-primary text-right advance-amount"
                            placeholder="0.00" />
                    </div>
                    <div class="flex gap-2">
                        <button type="button" class="text-emerald-500 hover:text-emerald-600 add-advance" title="Add Item">
                            <span class="material-symbols-outlined">add_circle</span>
                        </button>
                        <button type="button" class="text-slate-300 hover:text-red-500 remove-advance" title="Remove Item">
                            <span class="material-symbols-outlined">delete</span>
                        </button>
                    </div>
                </div>`,
            'deduction': `
                <div class="deduction-item flex flex-wrap md:flex-nowrap gap-4 items-center p-3 bg-slate-50 dark:bg-slate-800/30 rounded-lg">
                    <div class="flex-1 min-w-[200px] flex gap-2">
                        <select class="w-full employee-select deduction-description" data-placeholder="Select Employee..."></select>
                        <button type="button" class="px-2 py-1 bg-primary text-white rounded-md hover:bg-blue-600 transition-colors tooltip" title="Add New Employee" onclick="DailyCloseApp.openNewEmployeeModal(this)">
                            <span class="material-symbols-outlined text-sm">person_add</span>
                        </button>
                    </div>
                    <input type="text"
                        class="flex-[1.5] min-w-[200px] rounded-lg border-slate-200 dark:border-slate-700 dark:bg-slate-800 text-sm focus:border-primary focus:ring-primary deduction-note"
                        placeholder="Note/Reason" />
                    <div class="relative w-32 shrink-0">
                        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-medium">$</span>
                        <input type="number" step="any"
                            class="w-full pl-7 rounded-lg border-slate-200 dark:border-slate-700 dark:bg-slate-800 text-sm focus:border-primary focus:ring-primary text-right deduction-amount"
                            placeholder="0.00" />
                    </div>
                    <div class="flex gap-2">
                        <button type="button" class="text-emerald-500 hover:text-emerald-600 add-deduction" title="Add Item">
                            <span class="material-symbols-outlined">add_circle</span>
                        </button>
                        <button type="button" class="text-slate-300 hover:text-red-500 remove-deduction" title="Remove Item">
                            <span class="material-symbols-outlined">delete</span>
                        </button>
                    </div>
                </div>`,
            'credit': `
                <div class="credit-item flex flex-wrap md:flex-nowrap gap-4 items-center p-3 bg-slate-50 dark:bg-slate-800/30 rounded-lg">
                    <div class="flex-1 min-w-[200px] flex gap-2">
                        <select class="w-full customer-select credit-description" data-placeholder="Select Customer..."></select>
                        <button type="button" class="px-2 py-1 bg-primary text-white rounded-md hover:bg-blue-600 transition-colors tooltip" title="Add New Customer" onclick="DailyCloseApp.openNewCustomerModal(this)">
                            <span class="material-symbols-outlined text-sm">person_add</span>
                        </button>
                    </div>
                    <input type="text"
                        class="flex-[1.5] min-w-[200px] rounded-lg border-slate-200 dark:border-slate-700 dark:bg-slate-800 text-sm focus:border-primary focus:ring-primary credit-note"
                        placeholder="Note/Reference" />
                    <div class="relative w-32 shrink-0">
                        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-medium">$</span>
                        <input type="number" step="any"
                            class="w-full pl-7 rounded-lg border-slate-200 dark:border-slate-700 dark:bg-slate-800 text-sm focus:border-primary focus:ring-primary text-right credit-amount"
                            placeholder="0.00" />
                    </div>
                    <div class="flex gap-2">
                        <button type="button" class="text-emerald-500 hover:text-emerald-600 add-credit" title="Add Item">
                            <span class="material-symbols-outlined">add_circle</span>
                        </button>
                        <button type="button" class="text-slate-300 hover:text-red-500 remove-credit" title="Remove Item">
                            <span class="material-symbols-outlined">delete</span>
                        </button>
                    </div>
                </div>`,
            'cashback': `
                <div class="cashback-item flex flex-wrap md:flex-nowrap gap-4 items-center p-3 bg-slate-50 dark:bg-slate-800/30 rounded-lg">
                    <div class="flex-1 min-w-[200px] flex gap-2">
                        <select class="w-full customer-select cashback-description" data-placeholder="Select Customer..."></select>
                        <button type="button" class="px-2 py-1 bg-primary text-white rounded-md hover:bg-blue-600 transition-colors tooltip" title="Add New Customer" onclick="DailyCloseApp.openNewCustomerModal(this)">
                            <span class="material-symbols-outlined text-sm">person_add</span>
                        </button>
                    </div>
                    <input type="text"
                        class="flex-[1.5] min-w-[200px] rounded-lg border-slate-200 dark:border-slate-700 dark:bg-slate-800 text-sm focus:border-primary focus:ring-primary cashback-note"
                        placeholder="Note/Reference" />
                    <div class="relative w-32 shrink-0">
                        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-medium">$</span>
                        <input type="number" step="any"
                            class="w-full pl-7 rounded-lg border-slate-200 dark:border-slate-700 dark:bg-slate-800 text-sm focus:border-primary focus:ring-primary text-right cashback-amount"
                            placeholder="0.00" />
                    </div>
                    <div class="flex gap-2">
                        <button type="button" class="text-emerald-500 hover:text-emerald-600 add-cashback" title="Add Item">
                            <span class="material-symbols-outlined">add_circle</span>
                        </button>
                        <button type="button" class="text-slate-300 hover:text-red-500 remove-cashback" title="Remove Item">
                            <span class="material-symbols-outlined">delete</span>
                        </button>
                    </div>
                </div>`,
            'samer-expense': `
                <div class="samer-expense-item flex flex-wrap md:flex-nowrap gap-4 items-center p-3 bg-slate-50 dark:bg-slate-800/30 rounded-lg">
                    <div class="flex-1 min-w-[200px] flex gap-2">
                        <select class="w-full samer-receiver-select samer-expense-description" data-placeholder="Select Samer Receiver..."></select>
                        <button type="button" class="px-2 py-1 bg-primary text-white rounded-md hover:bg-blue-600 transition-colors tooltip" title="Add New Samer Receiver" onclick="DailyCloseApp.openNewReceiverModal(this, 'samer')">
                            <span class="material-symbols-outlined text-sm">person_add</span>
                        </button>
                    </div>
                    <input type="text"
                        class="flex-[1.5] min-w-[200px] rounded-lg border-slate-200 dark:border-slate-700 dark:bg-slate-800 text-sm focus:border-primary focus:ring-primary samer-expense-note"
                        placeholder="Note/Details" />
                    <div class="relative w-32 shrink-0">
                        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-medium">$</span>
                        <input type="number" step="any"
                            class="w-full pl-7 rounded-lg border-slate-200 dark:border-slate-700 dark:bg-slate-800 text-sm focus:border-primary focus:ring-primary text-right samer-expense-amount"
                            placeholder="0.00" />
                    </div>
                    <div class="flex gap-2">
                        <button type="button" class="text-emerald-500 hover:text-emerald-600 add-samer-expense" title="Add Item">
                            <span class="material-symbols-outlined">add_circle</span>
                        </button>
                        <button type="button" class="text-slate-300 hover:text-red-500 remove-samer-expense" title="Remove Item">
                            <span class="material-symbols-outlined">delete</span>
                        </button>
                    </div>
                </div>`
        };

        return templates[type] || '';
    },

    // Initialize simplified calculation handlers
    initializeSimpleCalculationHandlers() {
        // Handle input events for real-time calculation
        document.addEventListener('input', (e) => {
            if (e.target.matches('.expense-amount, .advance-amount, .deduction-amount, .credit-amount, .cashback-amount, .samer-expense-amount')) {
                this.calculateValues();
            }
        });
    },

    // Fetch daily closing data by date
    async fetchDailyClosingData(dateStr) {
        if (!dateStr) return;

        this.showStatusMessage(`Checking for existing record on ${dateStr}...`, 'info');

        try {
            const response = await fetch(`/api/daily-closing/${dateStr}`);
            const result = await response.json();

            if (response.ok && result.status === 'success') {
                this.populateForm(result.data);
                this.editMode = true;
                this.currentClosingDate = dateStr;

                const submitBtn = document.getElementById('submitCloseBtn');
                if (submitBtn) {
                    submitBtn.classList.remove('bg-emerald-500', 'hover:bg-emerald-600');
                    submitBtn.classList.add('bg-blue-500', 'hover:bg-blue-600');
                    submitBtn.innerHTML = '<span class="material-symbols-outlined">update</span> Update Daily Close';
                }

                this.showStatusMessage(`Record found for ${dateStr}. You are now in EDIT mode.`, 'success');
            } else {
                // No record found, reset to add mode
                this.editMode = false;
                this.currentClosingDate = null;

                const submitBtn = document.getElementById('submitCloseBtn');
                if (submitBtn) {
                    submitBtn.classList.add('bg-emerald-500', 'hover:bg-emerald-600');
                    submitBtn.classList.remove('bg-blue-500', 'hover:bg-blue-600');
                    submitBtn.innerHTML = '<span class="material-symbols-outlined">save</span> Save Daily Close';
                }

                // Keep the date but clear other fields if they were populated
                this.clearFormKeepDate(dateStr);
                this.showStatusMessage(`No record found for ${dateStr}. Ready for new entry.`, 'info');
            }
        } catch (error) {
            console.error('Error fetching daily closing data:', error);
            this.showStatusMessage('Error fetching data for this date.', 'danger');
        }
    },

    // Clear form but keep the selected date
    clearFormKeepDate(dateStr) {
        // Reset number inputs
        const inputs = document.querySelectorAll('#dailyCloseForm input[type="number"]');
        inputs.forEach(input => input.value = '');

        // Clear sections
        this.resetExpenseSection('#expensesSection', 'expense');
        this.resetExpenseSection('#advancesSection', 'advance');
        this.resetExpenseSection('#deductionsSection', 'deduction');
        this.resetExpenseSection('#creditsSection', 'credit');
        this.resetExpenseSection('#cashbacksSection', 'cashback');
        this.resetExpenseSection('#samerExpensesSection', 'samer-expense');

        this.calculateValues();
    },

    // Populate form with fetched data
    populateForm(data) {
        if (!data) return;

        // Set basic readings
        const mainReadingEl = document.getElementById('mainReading');
        if (mainReadingEl) {
            mainReadingEl.value = data.main_reading || '';
        }

        // Populate sections
        this.fillSection('#expensesSection', 'expense', data.expenses, 'receiver_id');
        this.fillSection('#advancesSection', 'advance', data.advances, 'employee_id');
        this.fillSection('#deductionsSection', 'deduction', data.deductions, 'employee_id');
        this.fillSection('#creditsSection', 'credit', data.credits, 'customer_id');
        this.fillSection('#cashbacksSection', 'cashback', data.cashbacks, 'customer_id');
        this.fillSection('#samerExpensesSection', 'samer-expense', data.samer_expenses, 'receiver_id');

        // Give time for TomSelect and DOM updates
        setTimeout(() => this.calculateValues(), 500);
    },

    // Helper to fill sections with items
    fillSection(sectionSelector, type, items, idField) {
        const section = document.querySelector(sectionSelector);
        if (!section || !items) return;

        // Clear current items first
        const existingItems = section.querySelectorAll('[class*="item"]');
        existingItems.forEach((item, index) => {
            // Destroy TomSelect instance to prevent memory leaks
            const selects = item.querySelectorAll('select');
            selects.forEach(select => {
                if (select.tomselect) select.tomselect.destroy();
            });
            item.remove();
        });

        if (items.length === 0) {
            // If no items, add one empty item
            this.addSectionItem(sectionSelector, type);
            return;
        }

        items.forEach((itemData, index) => {
            // Append the item template
            const template = this.getSectionTemplate(type);
            section.insertAdjacentHTML('beforeend', template);
            const newItem = section.lastElementChild;

            // Populate fields
            const noteInput = newItem.querySelector(`.${type}-note`);
            const amountInput = newItem.querySelector(`.${type}-amount`);
            if (noteInput) noteInput.value = itemData.note || '';
            if (amountInput) amountInput.value = itemData.amount || '';

            // Initialize TomSelect with the saved value
            const select = newItem.querySelector('select');
            if (select) {
                let options = [];
                let placeholder = '';

                if (type === 'expense') { options = this.receivers; placeholder = 'Select Receiver...'; }
                else if (type === 'advance' || type === 'deduction') { options = this.employees; placeholder = 'Select Employee...'; }
                else if (type === 'credit' || type === 'cashback') { options = this.customers; placeholder = 'Select Customer...'; }
                else if (type === 'samer-expense') { options = this.samerReceivers; placeholder = 'Select Samer Receiver...'; }

                // Small delay to ensure initialization order
                setTimeout(() => {
                    this.initializeGenericSelect(select, options, placeholder, String(itemData[idField]));
                }, 0);
            }
        });

        this.updateRemoveButtons(sectionSelector);
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

    // Check if admin is validated (this will be called after form submission)
    checkAdminValidation() {
        // This will be called after the page reloads from form submission
        const dateInput = document.getElementById('closeDate');
        const editBtn = document.getElementById('editDateBtn');

        if (dateInput && editBtn) {
            // Check if we have admin validation in the URL or session
            const urlParams = new URLSearchParams(window.location.search);
            const adminValidated = urlParams.get('admin_validated') === 'true';

            if (adminValidated) {
                // Admin was validated - unlock date field
                dateInput.removeAttribute('readonly');
                editBtn.innerHTML = '<i class="fas fa-lock"></i> Lock';
                editBtn.onclick = () => this.lockDateField();

                // Show success message
                this.showStatusMessage('Date field unlocked for editing', 'success');
            }
        }
    },

    // Verify admin password
    async verifyAdminPassword() {
        const password = document.getElementById('adminPassword').value;

        try {
            // Fetch admin password hash from server
            const response = await fetch('/api/admin-password');
            const data = await response.json();

            if (response.ok && data.status === 'success') {
                // Hash the entered password and compare with stored hash
                const hashedPassword = await this.hashPassword(password);

                if (hashedPassword === data.password) {
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
            } else {
                this.showStatusMessage('Error fetching admin password', 'danger');
            }
        } catch (error) {
            console.error('Error verifying admin password:', error);
            this.showStatusMessage('Error verifying password', 'danger');
        }
    },

    // Hash password using SHA-256 (same as server)
    async hashPassword(password) {
        const encoder = new TextEncoder();
        const data = encoder.encode(password);
        const hashBuffer = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        return hashHex;
    },

    // Lock date field
    lockDateField() {
        const dateInput = document.getElementById('closeDate');
        const editBtn = document.getElementById('editDateBtn');

        dateInput.setAttribute('readonly', 'readonly');
        editBtn.innerHTML = '<i class="fas fa-edit"></i> Edit';
        editBtn.onclick = () => this.showAdminPasswordModal();

        this.showStatusMessage('Date field locked', 'info');
    },

    // Fetch and populate autocomplete suggestions
    async fetchAutocompleteSuggestions() {
        try {
            const [receivers, employees, customers, samerReceivers] = await Promise.all([
                fetch('/api/suggestions/receivers').then(res => res.json()),
                fetch('/api/suggestions/employees').then(res => res.json()),
                fetch('/api/suggestions/customers').then(res => res.json()),
                fetch('/api/suggestions/samer-receivers').then(res => res.json())
            ]);

            this.populateDatalist('receiversList', receivers);
            this.populateDatalist('employeesList', employees);
            this.populateDatalist('customersList', customers);
            this.populateDatalist('samerReceiversList', samerReceivers);
        } catch (error) {
            console.error('Error fetching autocomplete suggestions:', error);
        }
    },

    // Populate a datalist with options
    populateDatalist(id, suggestions) {
        const datalist = document.getElementById(id);
        if (!datalist) return;

        datalist.innerHTML = '';
        suggestions.forEach(suggestion => {
            const option = document.createElement('option');
            option.value = suggestion;
            datalist.appendChild(option);
        });
    },

    // Handle new employee modal opening
    openNewEmployeeModal(btnElement) {
        // Store the select element that opened the modal so we can auto-select the new employee
        this.currentEmployeeSelect = btnElement.parentElement.querySelector('.employee-select');

        document.getElementById('newEmployeeForm').reset();
        document.getElementById('newEmployeeError').classList.add('hidden');

        const modalEl = document.getElementById('newEmployeeModal');
        const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
        modal.show();
    },

    // Handle new employee submission
    async submitNewEmployee() {
        const name = document.getElementById('newEmpName').value.trim();
        const phone = document.getElementById('newEmpPhone').value.trim();
        const position = document.getElementById('newEmpPosition').value.trim();
        const salary = parseFloat(document.getElementById('newEmpSalary').value) || 0;

        if (!name) return;

        const submitBtn = document.getElementById('btnSubmitNewEmployee');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';

        try {
            const response = await fetch('/api/employees', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    phone_number: phone,
                    position,
                    base_salary: salary,
                    is_active: true
                })
            });

            const data = await response.json();

            if (response.ok && data.status === 'success') {
                const newEmpId = data.employee_id || data.id;
                const newEmpName = data.employee_name || data.name;

                // Add to employees list cache
                this.employees.push({ id: newEmpId, name: newEmpName });

                // Update all existing TomSelect instances
                document.querySelectorAll('.employee-select').forEach(select => {
                    if (select.tomselect) {
                        select.tomselect.addOption({ id: String(newEmpId), name: newEmpName });
                        select.tomselect.refreshOptions(false);
                    }
                });

                // Auto-select in the dropdown that opened the modal
                if (this.currentEmployeeSelect && this.currentEmployeeSelect.tomselect) {
                    this.currentEmployeeSelect.tomselect.setValue(String(newEmpId));
                }

                // Close modal
                const modalEl = document.getElementById('newEmployeeModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();

                this.showStatusMessage('Employee added successfully', 'success');
            } else {
                const errorDiv = document.getElementById('newEmployeeError');
                errorDiv.querySelector('.error-text').textContent = data.error || 'Failed to create employee';
                errorDiv.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Error creating employee:', error);
            const errorDiv = document.getElementById('newEmployeeError');
            errorDiv.querySelector('.error-text').textContent = error.message;
            errorDiv.classList.remove('hidden');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    },

    // Handle new customer modal opening
    openNewCustomerModal(btnElement) {
        this.currentCustomerSelect = btnElement.parentElement.querySelector('.customer-select');

        document.getElementById('newCustomerForm').reset();
        document.getElementById('newCustomerError').classList.add('hidden');

        const modalEl = document.getElementById('newCustomerModal');
        const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
        modal.show();
    },

    // Handle new customer submission
    async submitNewCustomer() {
        const username = document.getElementById('newCustomerUsername').value.trim();
        const phone = document.getElementById('newCustomerPhone').value.trim();

        if (!username) return;

        const submitBtn = document.getElementById('btnSubmitNewCustomer');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';

        try {
            const response = await fetch('/api/customers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: username,
                    phone_number: phone
                })
            });

            const data = await response.json();

            if (response.ok && data.status === 'success') {
                const newId = data.id;
                const newName = data.name;

                // Add to list cache
                this.customers.push({ id: newId, name: newName });

                // Update all existing TomSelect instances for customers
                document.querySelectorAll('.customer-select').forEach(select => {
                    if (select.tomselect) {
                        select.tomselect.addOption({ id: String(newId), name: newName });
                        select.tomselect.refreshOptions(false);
                    }
                });

                // Auto-select in the dropdown that opened the modal
                if (this.currentCustomerSelect && this.currentCustomerSelect.tomselect) {
                    this.currentCustomerSelect.tomselect.setValue(String(newId));
                }

                // Close modal
                const modalEl = document.getElementById('newCustomerModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();

                this.showStatusMessage('Customer added successfully', 'success');
            } else {
                const errorDiv = document.getElementById('newCustomerError');
                errorDiv.querySelector('.error-text').textContent = data.error || 'Failed to create customer';
                errorDiv.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Error creating customer:', error);
            const errorDiv = document.getElementById('newCustomerError');
            errorDiv.querySelector('.error-text').textContent = error.message;
            errorDiv.classList.remove('hidden');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    },

    // Handle new receiver modal opening
    openNewReceiverModal(btnElement, type = 'general') {
        const selectClass = type === 'general' ? '.receiver-select' : `.${type}-receiver-select`;
        this.currentReceiverSelect = btnElement.parentElement.querySelector(selectClass);
        this.currentReceiverType = type;

        document.getElementById('newReceiverForm').reset();
        document.getElementById('newReceiverType').value = type;
        document.getElementById('newReceiverError').classList.add('hidden');

        // Update modal title
        const typeMap = { 'general': 'General Expense', 'samer': 'Samer Expense' };
        document.getElementById('newReceiverModalLabel').innerHTML = `
            <span class="material-symbols-outlined text-primary">person_add</span>
            Add New Receiver (${typeMap[type]})
        `;

        const modalEl = document.getElementById('newReceiverModal');
        const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
        modal.show();
    },

    // Handle new receiver submission
    async submitNewReceiver() {
        const name = document.getElementById('newReceiverName').value.trim();
        const type = document.getElementById('newReceiverType').value;

        if (!name) return;

        const submitBtn = document.getElementById('btnSubmitNewReceiver');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';

        let endpoint = '/api/receivers';
        if (type === 'samer') endpoint = '/api/samer-receivers';
        if (type === 'ahmad') endpoint = '/api/ahmad-receivers';

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name
                })
            });

            const data = await response.json();

            if (response.ok && data.status === 'success') {
                const newId = data.id;
                const newName = data.name;

                // Add to list cache based on type
                let cacheArray = this.receivers;
                let selectSelector = '.receiver-select';

                if (type === 'samer') {
                    cacheArray = this.samerReceivers;
                    selectSelector = '.samer-receiver-select';
                } else if (type === 'ahmad') {
                    cacheArray = this.ahmadReceivers;
                    selectSelector = '.ahmad-receiver-select';
                }

                cacheArray.push({ id: newId, name: newName });

                // Update all existing TomSelect instances for this type
                document.querySelectorAll(selectSelector).forEach(select => {
                    if (select.tomselect) {
                        select.tomselect.addOption({ id: String(newId), name: newName });
                        select.tomselect.refreshOptions(false);
                    }
                });

                // Auto-select in the dropdown that opened the modal
                if (this.currentReceiverSelect && this.currentReceiverSelect.tomselect) {
                    this.currentReceiverSelect.tomselect.setValue(String(newId));
                }

                // Close modal
                const modalEl = document.getElementById('newReceiverModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();

                this.showStatusMessage('Receiver added successfully', 'success');
            } else {
                const errorDiv = document.getElementById('newReceiverError');
                errorDiv.querySelector('.error-text').textContent = data.error || 'Failed to create receiver';
                errorDiv.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Error creating receiver:', error);
            const errorDiv = document.getElementById('newReceiverError');
            errorDiv.querySelector('.error-text').textContent = error.message;
            errorDiv.classList.remove('hidden');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    }
};
document.addEventListener('DOMContentLoaded', () => {
    DailyCloseApp.init();
});

// Export for potential future use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DailyCloseApp;
}
