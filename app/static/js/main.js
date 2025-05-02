/**
 * ChurchOps - Main JavaScript
 * High-performance JavaScript with minimal dependencies
 */

// Utility functions
const ChurchOps = {
    // Debounce function to improve performance of frequent events
    debounce: (func, wait = 300) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Format date to locale string
    formatDate: (dateString) => {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString();
    },
    
    // Format time to locale string
    formatTime: (timeString) => {
        if (!timeString) return '';
        // Handle SQL time format (HH:MM:SS)
        if (timeString.includes(':')) {
            const [hours, minutes] = timeString.split(':');
            const date = new Date();
            date.setHours(hours);
            date.setMinutes(minutes);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
        return timeString;
    },
    
    // Toggle element visibility
    toggleElement: (element, show = null) => {
        if (!element) return;
        
        if (show === null) {
            element.classList.toggle('hidden');
        } else if (show) {
            element.classList.remove('hidden');
        } else {
            element.classList.add('hidden');
        }
    },
    
    // Animate element
    animateElement: (element, animation, duration = 300) => {
        if (!element) return Promise.reject('No element provided');
        
        return new Promise(resolve => {
            element.classList.add(animation);
            
            const animationEndHandler = () => {
                element.classList.remove(animation);
                element.removeEventListener('animationend', animationEndHandler);
                resolve();
            };
            
            element.addEventListener('animationend', animationEndHandler);
            
            // Fallback if animation doesn't trigger
            setTimeout(() => {
                if (element.classList.contains(animation)) {
                    element.classList.remove(animation);
                    resolve();
                }
            }, duration + 50);
        });
    },
    
    // API request helper
    apiRequest: async (url, options = {}) => {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    },
    
    // Initialize components
    initComponents: () => {
        ChurchOps.initMobileMenu();
        ChurchOps.initAttendanceForm();
        ChurchOps.initSearchPeople();
        ChurchOps.initHierarchyToggle();
        ChurchOps.initFilterForm();
        ChurchOps.initReportCharts();
        ChurchOps.initResponsiveSliders();
    },
    
    // Initialize mobile menu
    initMobileMenu: () => {
        const hamburger = document.getElementById('sidebar-toggle');
        const sidebar = document.getElementById('sidebar');
        const appContainer = document.querySelector('.app-container');
        
        if (!hamburger || !sidebar || !appContainer) {
            console.error('Mobile menu elements not found:', { 
                hamburger: !!hamburger, 
                sidebar: !!sidebar, 
                appContainer: !!appContainer 
            });
            return;
        }
        
        // Hamburger click handler
        hamburger.addEventListener('click', function(event) {
            console.log('Hamburger clicked');
            // Toggle sidebar visibility
            if (window.innerWidth < 992) {
                appContainer.classList.toggle('sidebar-open');
                // Force reflow to ensure the class change takes effect
                void sidebar.offsetWidth;
            } else {
                appContainer.classList.toggle('sidebar-collapsed');
                // Force reflow to ensure the class change takes effect
                void sidebar.offsetWidth;
            }
            
            // Store state in localStorage
            if (appContainer.classList.contains('sidebar-open')) {
                localStorage.setItem('sidebar-state', 'open');
            } else if (appContainer.classList.contains('sidebar-collapsed')) {
                localStorage.setItem('sidebar-state', 'collapsed');
            } else {
                localStorage.setItem('sidebar-state', 'default');
            }
            
            // Prevent default behavior just in case
            event.preventDefault();
            event.stopPropagation();
        });
        
        // Auto-close sidebar when clicking on navigation links on mobile
        const navLinks = document.querySelectorAll('.sidebar .nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth < 992 && appContainer.classList.contains('sidebar-open')) {
                    appContainer.classList.remove('sidebar-open');
                    localStorage.setItem('sidebar-state', 'default');
                }
            });
        });
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function(event) {
            if (window.innerWidth < 992 && 
                appContainer.classList.contains('sidebar-open') && 
                !sidebar.contains(event.target) && 
                !hamburger.contains(event.target)) {
                appContainer.classList.remove('sidebar-open');
                localStorage.setItem('sidebar-state', 'default');
            }
        });
        
        // Reset sidebar state on page load to prevent auto-opening
        if (window.innerWidth < 992) {
            // On mobile, always start with sidebar closed
            appContainer.classList.remove('sidebar-open');
            // Only set localStorage if it was previously open
            if (localStorage.getItem('sidebar-state') === 'open') {
                localStorage.setItem('sidebar-state', 'default');
            }
        } else {
            // On desktop, respect the collapsed state
            const sidebarState = localStorage.getItem('sidebar-state');
            if (sidebarState === 'collapsed') {
                appContainer.classList.add('sidebar-collapsed');
            } else {
                appContainer.classList.remove('sidebar-collapsed');
            }
        }
        
        // Handle resize events
        window.addEventListener('resize', ChurchOps.debounce(() => {
            if (window.innerWidth >= 992) {
                // Switch to desktop view
                appContainer.classList.remove('sidebar-open');
                if (localStorage.getItem('sidebar-state') === 'collapsed') {
                    appContainer.classList.add('sidebar-collapsed');
                }
            } else {
                // Switch to mobile view
                appContainer.classList.remove('sidebar-collapsed');
            }
        }, 100));
    },
    
    // Initialize attendance form
    initAttendanceForm: () => {
        const form = document.getElementById('attendance-form');
        if (!form) return;
        
        // Handle form submission with optimistic UI
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Show loading state
            const submitButton = form.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner"></span> Saving...';
            
            try {
                // Get form data
                const formData = new FormData(form);
                
                // Submit form
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                if (!response.ok) {
                    throw new Error('Form submission failed');
                }
                
                // Handle success
                const successMessage = document.createElement('div');
                successMessage.className = 'alert alert-success fade-in';
                successMessage.innerHTML = `
                    <div class="alert-content">Attendance saved successfully!</div>
                    <button class="alert-close" aria-label="Close">&times;</button>
                `;
                
                const flashContainer = document.querySelector('.flash-messages');
                if (flashContainer) {
                    flashContainer.appendChild(successMessage);
                    
                    // Scroll to message
                    successMessage.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    
                    // Set up close button
                    const closeButton = successMessage.querySelector('.alert-close');
                    closeButton.addEventListener('click', () => {
                        successMessage.classList.add('fade-out');
                        setTimeout(() => successMessage.remove(), 300);
                    });
                    
                    // Auto-hide after 5 seconds
                    setTimeout(() => {
                        successMessage.classList.add('fade-out');
                        setTimeout(() => successMessage.remove(), 300);
                    }, 5000);
                }
                
                // Update UI to show marked attendees
                const personIds = formData.getAll('person_ids');
                personIds.forEach(id => {
                    const checkbox = document.querySelector(`input[name="person_ids"][value="${id}"]`);
                    if (checkbox) {
                        const row = checkbox.closest('tr, .person-item');
                        if (row) {
                            row.classList.add('marked');
                        }
                    }
                });
                
            } catch (error) {
                console.error('Form submission error:', error);
                
                // Show error message
                const errorMessage = document.createElement('div');
                errorMessage.className = 'alert alert-danger fade-in';
                errorMessage.innerHTML = `
                    <div class="alert-content">Failed to save attendance. Please try again.</div>
                    <button class="alert-close" aria-label="Close">&times;</button>
                `;
                
                const flashContainer = document.querySelector('.flash-messages');
                if (flashContainer) {
                    flashContainer.appendChild(errorMessage);
                    
                    // Set up close button
                    const closeButton = errorMessage.querySelector('.alert-close');
                    closeButton.addEventListener('click', () => {
                        errorMessage.classList.add('fade-out');
                        setTimeout(() => errorMessage.remove(), 300);
                    });
                }
            } finally {
                // Reset button state
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
        
        // Handle select all checkboxes
        const selectAllCheckboxes = document.querySelectorAll('.select-all');
        selectAllCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                const container = checkbox.closest('.cell-content, .team-content, .department-content');
                if (container) {
                    const childCheckboxes = container.querySelectorAll('input[name="person_ids"]');
                    childCheckboxes.forEach(childCheckbox => {
                        childCheckbox.checked = checkbox.checked;
                    });
                }
            });
        });
    },
    
    // Initialize people search
    initSearchPeople: () => {
        const searchInput = document.getElementById('search-people');
        if (!searchInput) return;
        
        const resultsContainer = document.getElementById('search-results');
        const serviceId = searchInput.dataset.serviceId;
        
        // Debounced search function
        const performSearch = ChurchOps.debounce(async (query) => {
            if (!query || query.length < 2) {
                resultsContainer.innerHTML = '';
                return;
            }
            
            try {
                const url = `/api/people/search?query=${encodeURIComponent(query)}&service_id=${serviceId}`;
                const results = await ChurchOps.apiRequest(url);
                
                if (results.length === 0) {
                    resultsContainer.innerHTML = '<div class="search-empty">No results found</div>';
                    return;
                }
                
                // Build results HTML
                let html = '<ul class="search-results-list">';
                results.forEach(person => {
                    const markedClass = person.marked ? 'marked' : '';
                    html += `
                        <li class="search-result-item ${markedClass}">
                            <div class="search-result-info">
                                <div class="search-result-name">${person.name}</div>
                                <div class="search-result-path">
                                    ${person.region} &raquo; ${person.direction} &raquo; 
                                    ${person.department} &raquo; ${person.team} &raquo; ${person.cell}
                                </div>
                            </div>
                            <div class="search-result-action">
                                <label class="form-check">
                                    <input type="checkbox" name="person_ids" value="${person.id}" class="form-check-input" ${person.marked ? 'checked' : ''}>
                                    <span class="form-check-label">Mark</span>
                                </label>
                            </div>
                        </li>
                    `;
                });
                html += '</ul>';
                
                resultsContainer.innerHTML = html;
                
                // Add event listeners to checkboxes
                const checkboxes = resultsContainer.querySelectorAll('input[name="person_ids"]');
                checkboxes.forEach(checkbox => {
                    checkbox.addEventListener('change', function() {
                        const item = this.closest('.search-result-item');
                        if (this.checked) {
                            item.classList.add('marked');
                        } else {
                            item.classList.remove('marked');
                        }
                    });
                });
                
            } catch (error) {
                console.error('Search error:', error);
                resultsContainer.innerHTML = '<div class="search-error">Error searching for people</div>';
            }
        }, 300);
        
        // Set up search input
        searchInput.addEventListener('input', () => {
            performSearch(searchInput.value.trim());
        });
        
        // Clear results when clicking outside
        document.addEventListener('click', (event) => {
            if (!searchInput.contains(event.target) && !resultsContainer.contains(event.target)) {
                resultsContainer.innerHTML = '';
            }
        });
    },
    
    // Initialize hierarchy toggles
    initHierarchyToggle: () => {
        // Add click handlers to toggleable sections
        document.querySelectorAll('.hierarchy-toggle').forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.preventDefault();
                
                const target = toggle.dataset.target;
                const content = document.getElementById(target);
                
                if (content) {
                    content.classList.toggle('collapsed');
                    toggle.classList.toggle('collapsed');
                    
                    // Update aria attributes for accessibility
                    const expanded = !content.classList.contains('collapsed');
                    toggle.setAttribute('aria-expanded', expanded);
                    content.setAttribute('aria-hidden', !expanded);
                    
                    // Change icon
                    const icon = toggle.querySelector('.toggle-icon');
                    if (icon) {
                        icon.textContent = expanded ? '−' : '+';
                    }
                }
            });
        });
    },
    
    // Initialize filter form
    initFilterForm: () => {
        const filterForm = document.getElementById('filter-form');
        if (!filterForm || filterForm.classList.contains('no-ajax')) return;
        
        // Dependent dropdowns for hierarchy
        const regionSelect = document.getElementById('region_id');
        const directionSelect = document.getElementById('direction_id');
        const departmentSelect = document.getElementById('department_id');
        const teamSelect = document.getElementById('team_id');
        const cellSelect = document.getElementById('cell_id');
        const nameSearch = document.getElementById('name_search');
        const statusSelect = document.getElementById('is_active');
        
        // Prevent the default form submission and handle filter changes via AJAX
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            loadFilteredData();
        });
        
        // Initialize the asynchronous loading
        const loadFilteredData = async function() {
            // Show loading state
            const tableBody = document.querySelector('table tbody');
            if (tableBody) {
                tableBody.innerHTML = '<tr><td colspan="7" class="text-center">Loading...</td></tr>';
            }
            
            // Collect all form data
            const formData = new FormData(filterForm);
            const queryParams = new URLSearchParams(formData).toString();
            
            try {
                // Fetch the filtered data
                const response = await fetch(filterForm.action + '?' + queryParams + '&ajax=true', {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                
                // Get the JSON data
                const data = await response.json();
                
                // Update the table
                if (tableBody && data.people) {
                    if (data.people.length === 0) {
                        tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No saints found matching the current filters.</td></tr>';
                    } else {
                        tableBody.innerHTML = '';
                        data.people.forEach(person => {
                            tableBody.innerHTML += `
                                <tr>
                                    <td>${person.first_name} ${person.last_name}</td>
                                    <td>${person.cell}</td>
                                    <td>${person.team}</td>
                                    <td>${person.department}</td>
                                    <td>${person.direction}</td>
                                    <td>${person.region}</td>
                                    <td>
                                        <span class="badge ${person.is_active ? 'badge-success' : 'badge-danger'}">
                                            ${person.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                </tr>
                            `;
                        });
                    }
                }
                
                // Update pagination if present
                const paginationContainer = document.querySelector('.pagination');
                if (paginationContainer && data.pagination) {
                    paginationContainer.querySelector('.pagination-info').textContent = 
                        `Showing ${data.pagination.page} of ${data.pagination.pages} pages`;
                        
                    const prevButton = paginationContainer.querySelector('.pagination-controls a:first-child');
                    const nextButton = paginationContainer.querySelector('.pagination-controls a:last-child');
                    
                    if (prevButton && nextButton) {
                        if (data.pagination.has_prev) {
                            prevButton.href = filterForm.action + '?' + queryParams + '&page=' + data.pagination.prev_num;
                            prevButton.classList.remove('disabled');
                        } else {
                            prevButton.classList.add('disabled');
                        }
                        
                        if (data.pagination.has_next) {
                            nextButton.href = filterForm.action + '?' + queryParams + '&page=' + data.pagination.next_num;
                            nextButton.classList.remove('disabled');
                        } else {
                            nextButton.classList.add('disabled');
                        }
                    }
                }
                
                // Update URL without refreshing
                const newUrl = filterForm.action + '?' + queryParams;
                window.history.replaceState({ path: newUrl }, '', newUrl);
                
            } catch (error) {
                console.error('Error loading filtered data:', error);
                if (tableBody) {
                    tableBody.innerHTML = '<tr><td colspan="7" class="text-center">An error occurred while loading data.</td></tr>';
                }
            }
        };
        
        // Add change event listeners to form inputs
        const formInputs = [regionSelect, directionSelect, departmentSelect, teamSelect, cellSelect, statusSelect];
        formInputs.forEach(input => {
            if (input) {
                input.addEventListener('change', ChurchOps.debounce(() => {
                    loadFilteredData();
                }, 300));
            }
        });
        
        // Handle name search with debounce
        if (nameSearch) {
            nameSearch.addEventListener('input', ChurchOps.debounce(() => {
                loadFilteredData();
            }, 500));
        }
    },
    
    // Initialize charts for reports
    initReportCharts: () => {
        const reportCharts = document.querySelectorAll('.report-chart');
        if (reportCharts.length === 0) return;
        
        // Check if Chart.js is loaded, if not, dynamically load it
        if (typeof Chart === 'undefined') {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js';
            script.integrity = 'sha384-+jVt2eFCLJz+XTET+TzbRlJtUF7jgW0s0ll1Wo9xWl8xD7B5JZ+XrtJ4xF6RlTuA';
            script.crossOrigin = 'anonymous';
            
            script.onload = () => {
                // Initialize charts once Chart.js is loaded
                reportCharts.forEach(chartContainer => {
                    const chartData = JSON.parse(chartContainer.dataset.chart);
                    const chartType = chartContainer.dataset.type || 'line';
                    const canvas = chartContainer.querySelector('canvas');
                    
                    if (!canvas || !chartData) return;
                    
                    new Chart(canvas, {
                        type: chartType,
                        data: chartData,
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            animation: {
                                duration: 400,
                                easing: 'easeOutQuad'
                            },
                            plugins: {
                                legend: {
                                    position: 'top',
                                    labels: {
                                        usePointStyle: true,
                                        boxWidth: 6
                                    }
                                },
                                tooltip: {
                                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                                    titleFont: {
                                        size: 14
                                    },
                                    bodyFont: {
                                        size: 13
                                    }
                                }
                            }
                        }
                    });
                });
            };
            
            document.head.appendChild(script);
        } else {
            // Chart.js already loaded, initialize charts
            reportCharts.forEach(chartContainer => {
                // Similar chart initialization...
            });
        }
    },
    
    // Initialize responsive sliders
    initResponsiveSliders: () => {
        // Find all slider elements - typically elements with class "slider" or similar
        const sliders = document.querySelectorAll('.slider, [data-slider]');
        
        if (!sliders || sliders.length === 0) return;
        
        sliders.forEach(slider => {
            // Handle slider touch events for mobile devices
            let startX, currentX, initialPosition;
            const handleTouchStart = (e) => {
                startX = e.touches[0].clientX;
                initialPosition = slider.scrollLeft;
                slider.style.scrollBehavior = 'auto'; // Disable smooth scrolling during touch
            };
            
            const handleTouchMove = (e) => {
                if (!startX) return;
                currentX = e.touches[0].clientX;
                const diff = startX - currentX;
                slider.scrollLeft = initialPosition + diff;
                // Prevent page scrolling when sliding horizontally
                if (Math.abs(diff) > 5) {
                    e.preventDefault();
                }
            };
            
            const handleTouchEnd = () => {
                startX = null;
                slider.style.scrollBehavior = 'smooth'; // Re-enable smooth scrolling
            };
            
            // Add event listeners for touch devices
            slider.addEventListener('touchstart', handleTouchStart, { passive: false });
            slider.addEventListener('touchmove', handleTouchMove, { passive: false });
            slider.addEventListener('touchend', handleTouchEnd);
            
            // For mouse events (desktop/laptop)
            let isMouseDown = false;
            
            slider.addEventListener('mousedown', (e) => {
                isMouseDown = true;
                startX = e.clientX;
                initialPosition = slider.scrollLeft;
                slider.style.scrollBehavior = 'auto';
                slider.style.cursor = 'grabbing';
                e.preventDefault();
            });
            
            slider.addEventListener('mousemove', (e) => {
                if (!isMouseDown) return;
                const diff = startX - e.clientX;
                slider.scrollLeft = initialPosition + diff;
            });
            
            slider.addEventListener('mouseup', () => {
                isMouseDown = false;
                slider.style.scrollBehavior = 'smooth';
                slider.style.cursor = 'grab';
            });
            
            slider.addEventListener('mouseleave', () => {
                if (isMouseDown) {
                    isMouseDown = false;
                    slider.style.cursor = 'grab';
                }
            });
            
            // Make sure sliders are properly sized for different devices
            const resizeSlider = () => {
                // Apply specific styles for different screen sizes
                if (window.innerWidth < 768) {
                    // Mobile styling
                    slider.style.overflowX = 'auto';
                    slider.style.scrollSnapType = 'x mandatory';
                    
                    // Make child items snap points
                    const items = slider.children;
                    for (let item of items) {
                        item.style.scrollSnapAlign = 'start';
                        item.style.flexShrink = '0';
                    }
                } else {
                    // Desktop/tablet styling
                    // Keep some scroll functionality but with different UX
                    slider.style.overflowX = 'auto';
                }
            };
            
            // Initial setup
            resizeSlider();
            
            // Re-evaluate on window resize
            window.addEventListener('resize', ChurchOps.debounce(resizeSlider, 200));
        });
    }
};

// Initialize on DOM content loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize all components
    ChurchOps.initComponents();
    
    // Close alert messages
    document.querySelectorAll('.alert-close').forEach(button => {
        button.addEventListener('click', function() {
            const alert = this.closest('.alert');
            alert.classList.add('fade-out');
            setTimeout(() => alert.remove(), 300);
        });
    });
});
