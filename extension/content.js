// !!! IMPORTANT !!!
// Paste your Ngrok public URL here
const BACKEND_URL = ' https://8b8056554119.ngrok-free.app';

/**
 * Processes a single tweet element to check if its content should be masked.
 * It sends the tweet's text and the user's custom keywords to the backend for analysis.
 * @param {HTMLElement} tweetElement The HTML element representing the tweet.
 */
const processTweet = async (tweetElement) => {
    // Avoid processing tweets that have already been checked
    if (tweetElement.dataset.sentinelChecked) return;
    tweetElement.dataset.sentinelChecked = 'true';

    const textContent = tweetElement.innerText;
    if (!textContent) return;

    try {
        // 1. Get the user's custom input from storage
        const { userExperiences } = await chrome.storage.local.get(['userExperiences']);

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

        const data = await response.json();

        // 4. If the backend decides to mask, apply the mask with the reason it provides
        //    (Example backend response: { "action": "mask", "reason": "..." })
        if (data.action === 'mask') {
            const reason = data.reason || 'This content was hidden by Sentinel Shield.';
            maskContent(tweetElement, reason);
        }

    } catch (error) {
        console.error('Sentinel Shield: Error contacting backend.', error);
    }
};

/**
 * Creates and applies a visual mask over a given element.
 * The mask displays a reason for hiding the content and a button to reveal it.
 * @param {HTMLElement} tweetElement The element to apply the mask to.
 * @param {string} reason The reason the content is being masked.
 */
const maskContent = (tweetElement, reason) => {
    // Relative positioning is needed for the absolutely positioned mask to work correctly
    tweetElement.style.position = 'relative';

    const mask = document.createElement('div');
    mask.className = 'sentinel-mask';
    mask.innerHTML = `
        <div class="sentinel-mask-text">${reason}</div>
        <button class="sentinel-mask-button">Show Content</button>
    `;

    // Add a click event listener to the "Show Content" button to remove the mask
    mask.querySelector('.sentinel-mask-button').addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent the click from affecting underlying elements
        mask.remove(); // Remove the mask to reveal the original content
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