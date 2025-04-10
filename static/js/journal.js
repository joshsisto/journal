/**
 * Journal App JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Automatically expand textareas as content grows
    const autoExpandTextareas = document.querySelectorAll('textarea');
    autoExpandTextareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    });
    
    // Handle conditional questions in guided journal
    const exerciseRadios = document.querySelectorAll('input[name="question_exercise"]');
    const exerciseTypeCard = document.getElementById('exerciseTypeCard');
    
    if (exerciseRadios.length > 0 && exerciseTypeCard) {
        exerciseRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                if (this.value === 'Yes' && this.checked) {
                    exerciseTypeCard.style.display = 'block';
                } else {
                    exerciseTypeCard.style.display = 'none';
                }
            });
        });
    }
    
    // Auto-save functionality (optional)
    const journalForms = document.querySelectorAll('form[id^="journal"]');
    journalForms.forEach(form => {
        const formInputs = form.querySelectorAll('input, textarea');
        formInputs.forEach(input => {
            input.addEventListener('change', function() {
                const formData = new FormData(form);
                const formId = form.id;
                
                // Save form data to localStorage
                const formDataObj = {};
                formData.forEach((value, key) => {
                    formDataObj[key] = value;
                });
                
                localStorage.setItem(`journal_autosave_${formId}`, JSON.stringify(formDataObj));
            });
        });
        
        // Check for saved data on page load
        const savedData = localStorage.getItem(`journal_autosave_${form.id}`);
        if (savedData) {
            try {
                const formDataObj = JSON.parse(savedData);
                
                // Populate form fields
                Object.keys(formDataObj).forEach(key => {
                    const field = form.querySelector(`[name="${key}"]`);
                    if (field) {
                        if (field.type === 'radio') {
                            form.querySelector(`[name="${key}"][value="${formDataObj[key]}"]`).checked = true;
                        } else {
                            field.value = formDataObj[key];
                        }
                    }
                });
                
                // Show restore notification
                const restoreNotice = document.createElement('div');
                restoreNotice.className = 'alert alert-info alert-dismissible fade show mt-3';
                restoreNotice.innerHTML = `
                    Unsaved entry restored from your last session.
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
                form.prepend(restoreNotice);
            } catch (e) {
                console.error('Error restoring saved form data', e);
            }
        }
        
        // Clear saved data on successful submission
        form.addEventListener('submit', function() {
            localStorage.removeItem(`journal_autosave_${form.id}`);
        });
    });
});
