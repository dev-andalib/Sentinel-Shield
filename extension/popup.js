document.addEventListener('DOMContentLoaded', () => {
  const keywordsTextarea = document.getElementById('keywords');
  const saveButton = document.getElementById('save');

  // Load and display saved keywords when the popup opens
  chrome.storage.local.get(['blockedKeywords'], (result) => {
    if (result.blockedKeywords) {
      keywordsTextarea.value = result.blockedKeywords.join(', ');
    }
  });

  // Save keywords when the button is clicked
  saveButton.addEventListener('click', () => {
    const keywords = keywordsTextarea.value.split(',').map(k => k.trim()).filter(Boolean);
    // Use chrome.storage.local.set() to save the list [cite: 41]
    chrome.storage.local.set({ blockedKeywords: keywords }, () => {
      console.log('Keywords saved!');
      window.close(); // Close the popup after saving
    });
  });
});