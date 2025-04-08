/**
 * Guided Journal functionality - simplified version
 * 
 * This file handles the interactive elements of the guided journal entry form
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log("Guided journal script loaded");
    
    // Directly target the additional questions dropdown using different selectors to be sure
    const dropdown = document.querySelector('select[name="question_additional_questions"]');
    console.log("Dropdown selector 1:", dropdown);
    
    if (!dropdown) {
        const alternativeDropdown = document.getElementById('additional_questions_select');
        console.log("Dropdown selector 2:", alternativeDropdown);
        
        if (alternativeDropdown) {
            setupDropdown(alternativeDropdown);
        } else {
            // Last try - find any dropdown on the page
            const anyDropdown = document.querySelector('select.form-select');
            console.log("Dropdown selector 3:", anyDropdown);
            
            if (anyDropdown) {
                setupDropdown(anyDropdown);
            } else {
                console.error("Could not find the additional questions dropdown");
            }
        }
    } else {
        setupDropdown(dropdown);
    }
    
    function setupDropdown(dropdownElement) {
        // Find the additional questions section
        const additionalQuestionsSection = document.getElementById('additional-questions-section');
        console.log("Additional questions section:", additionalQuestionsSection);
        
        if (!additionalQuestionsSection) {
            console.error("Could not find the additional questions section");
            return;
        }
        
        // Hide the section initially
        additionalQuestionsSection.style.display = 'none';
        
        // Basic dropdown change handler - just show/hide the section
        dropdownElement.addEventListener('change', function() {
            const selectedValue = this.value;
            console.log("Dropdown changed to:", selectedValue);
            
            if (selectedValue && selectedValue !== 'None') {
                // Show the section
                additionalQuestionsSection.style.display = 'block';
                
                // Try to find and activate the tab for this category
                activateTab(selectedValue);
            } else {
                // Hide the section
                additionalQuestionsSection.style.display = 'none';
            }
        });
        
        // If there's already a value selected, trigger the change event
        if (dropdownElement.value && dropdownElement.value !== 'None') {
            console.log("Initial dropdown value:", dropdownElement.value);
            dropdownElement.dispatchEvent(new Event('change'));
        }
    }
    
    function activateTab(category) {
        console.log("Activating tab for category:", category);
        
        // Format the category to match tab ID format (lowercase, hyphens instead of spaces)
        const formattedCategory = category.toLowerCase().replace(/\s+/g, '-');
        console.log("Formatted category:", formattedCategory);
        
        // Try to find the tab element
        const tabSelector = `#${formattedCategory}-tab`;
        const tabElement = document.querySelector(tabSelector);
        console.log("Tab selector:", tabSelector);
        console.log("Tab element:", tabElement);
        
        if (tabElement) {
            // Remove active class from all tabs
            document.querySelectorAll('.nav-tab .nav-link').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Add active class to this tab
            tabElement.classList.add('active');
            
            // Try to activate the corresponding content
            const contentId = tabElement.getAttribute('data-bs-target');
            if (contentId) {
                const contentElement = document.querySelector(contentId);
                console.log("Content id:", contentId);
                console.log("Content element:", contentElement);
                
                if (contentElement) {
                    // Hide all other content
                    document.querySelectorAll('.tab-pane').forEach(pane => {
                        pane.classList.remove('show', 'active');
                    });
                    
                    // Show this content
                    contentElement.classList.add('show', 'active');
                }
            }
        }
    }
});