// !!! IMPORTANT !!!
// Paste your Ngrok public URL here
// !!! IMPORTANT !!!
// Paste your Ngrok public URL here (no leading/trailing spaces)
const BACKEND_URL = 'https://21b4f3dad6cd.ngrok-free.app';

/**
 * Processes a single tweet element to check if its content should be masked.
 * It sends the tweet's text and the user's custom keywords to the backend for analysis.
 * @param {HTMLElement} tweetElement The HTML element representing the tweet.
 */
const processTweet = async (tweetElement) => {
    // Only process if not currently being checked
    if (tweetElement.dataset.sentinelChecked === 'checking') return;
    
    // Mark as being checked to prevent concurrent checks
    tweetElement.dataset.sentinelChecked = 'checking';

    const textContent = tweetElement.innerText;
    if (!textContent) return;

    try {
        // 1. Get the user's custom input from storage
        const { userExperiences } = await new Promise((resolve) =>
          chrome.storage.local.get(['userExperiences'], resolve)
        );

        // 2. Prepare the data payload, including both the tweet text and keywords
        const payload = {
            text: textContent,
            keywords:  userExperiences || "" // Send keywords or an empty array
        };

        // 3. Send the combined payload to the backend for a decision
        const response = await fetch(`${BACKEND_URL}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // 4. If the backend flags content, apply the mask with details
        if (data.status === "flagged") {
            const details = data.details || [];
            const reason = data.reason || 
                          `Content flagged (${details.length} trigger${details.length !== 1 ? 's' : ''} found)`;
            const explanation = data.explanation || 
                              'This content may be challenging based on your personal experiences.';
            maskContent(tweetElement, reason, explanation);
        }

    } catch (error) {
        console.error('Sentinel Shield: Error contacting backend.', error);
        // Clear the checking state in case of error
        tweetElement.removeAttribute('data-sentinel-checked');
    }
};

/**
 * Creates and applies a visual mask over a given element.
 * The mask displays a reason for hiding the content and a button to reveal it.
 * @param {HTMLElement} tweetElement The element to apply the mask to.
 * @param {string} reason The reason the content is being masked.
 */
const maskContent = (tweetElement, reason, explanation) => {
    // Relative positioning is needed for the absolutely positioned mask to work correctly
    tweetElement.style.position = 'relative';

    const mask = document.createElement('div');
    mask.className = 'sentinel-mask';
    
    // Create initial mask content with both the reason and show content button
    mask.innerHTML = `
        <div class="sentinel-mask-text">${reason}</div>
        <button class="sentinel-show-explanation-button">Why is this masked?</button>
        <button class="sentinel-mask-button">Show Content</button>
    `;

    // Create the explanation panel (initially hidden)
    const explanationPanel = document.createElement('div');
    explanationPanel.className = 'sentinel-explanation-panel';
    explanationPanel.style.display = 'none';
    explanationPanel.innerHTML = `
        <div class="sentinel-explanation-text">${explanation || 'This content may be challenging based on your preferences.'}</div>
        <button class="sentinel-back-button">Go back</button>
    `;
    mask.appendChild(explanationPanel);

    // Show explanation panel when "Why is this masked?" is clicked
    mask.querySelector('.sentinel-show-explanation-button').addEventListener('click', (e) => {
        e.stopPropagation();
        mask.querySelector('.sentinel-mask-text').style.display = 'none';
        mask.querySelector('.sentinel-show-explanation-button').style.display = 'none';
        explanationPanel.style.display = 'block';
    });

    // Handle show content button click
    mask.querySelector('.sentinel-mask-button').addEventListener('click', (e) => {
        e.stopPropagation();
        // Remove the sentinel checked flag so content can be rechecked
        tweetElement.removeAttribute('data-sentinel-checked');
        mask.remove();
    });

    // Handle back button in explanation panel
    mask.querySelector('.sentinel-back-button').addEventListener('click', (e) => {
        e.stopPropagation();
        explanationPanel.style.display = 'none';
        mask.querySelector('.sentinel-mask-text').style.display = 'block';
        mask.querySelector('.sentinel-show-explanation-button').style.display = 'block';
        mask.querySelector('.sentinel-mask-button').style.display = 'block';
    });

    // Add the mask as a child to the tweet element
    tweetElement.appendChild(mask);
};

/**
 * Uses a MutationObserver to detect when new nodes are added to the page,
 * allowing the script to process new tweets as they are loaded dynamically.
 */
const observer = new MutationObserver((mutationsList) => {
    for (const mutation of mutationsList) {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
            mutation.addedNodes.forEach(node => {
                // Check if the added node is a tweet itself
                if (node.nodeType === 1 && node.matches('[data-testid="tweet"]')) {
                    processTweet(node);
                }
                // Check for any tweets nested within the added node
                if (node.querySelectorAll) {
                    node.querySelectorAll('[data-testid="tweet"]').forEach(processTweet);
                }
            });
        }
    }
});

// Start observing the entire document body for changes to the DOM
observer.observe(document.body, { childList: true, subtree: true });