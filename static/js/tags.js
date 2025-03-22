/**
 * Tags management functionality for journal entries.
 * 
 * This script handles the dynamic creation of new tags during journal entry creation.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const newTagNameInput = document.getElementById('new-tag-name');
    const newTagColorInput = document.getElementById('new-tag-color');
    const addTagButton = document.getElementById('add-tag-btn');
    const tagFeedback = document.getElementById('tag-feedback');
    const newTagsData = document.getElementById('new-tags-data');
    
    // Check if tag elements exist on the page
    if (!newTagNameInput || !newTagColorInput || !addTagButton || !tagFeedback || !newTagsData) {
        return; // Exit if not on a page with tag functionality
    }
    
    // Initialize newTags array
    let newTags = [];
    
    // If there's already value in the hidden field, parse it
    try {
        if (newTagsData.value && newTagsData.value !== '[]') {
            newTags = JSON.parse(newTagsData.value);
        }
    } catch (e) {
        console.error('Error parsing new tags data:', e);
        newTags = [];
    }
    
    // Update hidden field with newTags data
    function updateNewTagsData() {
        newTagsData.value = JSON.stringify(newTags);
    }
    
    // Handle adding a new tag
    addTagButton.addEventListener('click', function() {
        const tagName = newTagNameInput.value.trim();
        const tagColor = newTagColorInput.value;
        
        // Validate tag name
        if (!tagName) {
            tagFeedback.textContent = 'Please enter a tag name';
            tagFeedback.className = 'form-text text-danger';
            return;
        }
        
        // Check if this tag name already exists in existing tags
        const existingTags = document.querySelectorAll('.form-check-label');
        for (const tag of existingTags) {
            if (tag.textContent.trim().toLowerCase() === tagName.toLowerCase()) {
                tagFeedback.textContent = 'This tag already exists';
                tagFeedback.className = 'form-text text-danger';
                return;
            }
        }
        
        // Check if this tag name already exists in new tags
        for (const tag of newTags) {
            if (tag.name.toLowerCase() === tagName.toLowerCase()) {
                tagFeedback.textContent = 'This tag already exists';
                tagFeedback.className = 'form-text text-danger';
                return;
            }
        }
        
        // Add new tag to the list
        const newTag = {
            name: tagName,
            color: tagColor
        };
        
        newTags.push(newTag);
        updateNewTagsData();
        
        // Create a visual representation of the tag
        const tagContainer = document.querySelector('.d-flex.flex-wrap.gap-2');
        
        // Create elements
        const newTagIndex = newTags.length - 1;
        const formCheck = document.createElement('div');
        formCheck.className = 'form-check form-check-inline';
        
        const checkbox = document.createElement('input');
        checkbox.className = 'form-check-input new-tag-checkbox';
        checkbox.type = 'checkbox';
        checkbox.name = 'new_tag_checkbox';
        checkbox.id = 'new-tag-' + newTagIndex;
        checkbox.setAttribute('data-index', newTagIndex);
        checkbox.checked = true; // Check by default since it's a new tag
        
        const label = document.createElement('label');
        label.className = 'form-check-label';
        label.htmlFor = 'new-tag-' + newTagIndex;
        
        const badge = document.createElement('span');
        badge.className = 'badge';
        badge.style.backgroundColor = tagColor;
        badge.textContent = tagName;
        
        // Assemble elements
        label.appendChild(badge);
        formCheck.appendChild(checkbox);
        formCheck.appendChild(label);
        
        // Add to container
        tagContainer.appendChild(formCheck);
        
        // Clear form and show success message
        newTagNameInput.value = '';
        tagFeedback.textContent = 'Tag added! It will be created when you save the entry.';
        tagFeedback.className = 'form-text text-success';
        
        // Hide "no tags" message if present
        const noTagsMsg = tagContainer.querySelector('.text-muted');
        if (noTagsMsg) {
            noTagsMsg.style.display = 'none';
        }
    });
    
    // Clear feedback when tag name is changed
    newTagNameInput.addEventListener('input', function() {
        tagFeedback.textContent = '';
    });
});