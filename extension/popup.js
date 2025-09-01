document.addEventListener('DOMContentLoaded', () => {
    const keywordsTextarea = document.getElementById('keywords');
    const saveButton = document.getElementById('save');

    // Load the saved text block when the popup opens
    chrome.storage.local.get(['userExperiences'], (result) => {
        if (result.userExperiences) {
            keywordsTextarea.value = result.userExperiences;
        }
    });

    // Save the entire text block when the button is clicked
    saveButton.addEventListener('click', () => {
        // Get the entire text as one string, with just a simple trim
        const experiences = keywordsTextarea.value.trim();
        
        // Save the single block of text
        chrome.storage.local.set({ userExperiences: experiences }, () => {
            console.log('User experiences saved!');
            window.close(); // Close the popup after saving
        });
    });
});