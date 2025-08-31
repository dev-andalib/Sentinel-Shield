// !!! IMPORTANT !!!
// Paste your Ngrok public URL here
const BACKEND_URL = 'https://8cc74488deaf.ngrok-free.app';

// Function to check content and apply mask if necessary
const processTweet = async (tweetElement) => {
    // Avoid processing already masked tweets
    if (tweetElement.dataset.sentinelChecked) return;
    tweetElement.dataset.sentinelChecked = 'true';

    const textContent = tweetElement.innerText;
    if (!textContent) return;

    let isHarmful = false;
    let reason = '';

    // 1. Check against user's custom keywords [cite: 43]
    const { blockedKeywords } = await chrome.storage.local.get(['blockedKeywords']);
    if (blockedKeywords && blockedKeywords.length > 0) {
        for (const keyword of blockedKeywords) {
            if (textContent.toLowerCase().includes(keyword.toLowerCase())) {
                isHarmful = true;
                reason = `This content was hidden because it contains the keyword: "${keyword}"`;
                break;
            }
        }
    }

    // 2. If not harmful yet, check with the AI backend [cite: 44]
    if (!isHarmful) {
        try {
            // Use fetch() to send text to your backend [cite: 24]
            const response = await fetch(BACKEND_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: textContent })
            });
            const data = await response.json(); // It will respond with JSON [cite: 25]
            if (data.label === 'toxic') {
                isHarmful = true;
                reason = 'This content was flagged as potentially toxic by Sentinel Shield.';
            }
        } catch (error) {
            console.error('Sentinel Shield: Error contacting backend.', error);
        }
    }

    // 3. If harmful, apply the mask
    if (isHarmful) {
        maskContent(tweetElement, reason);
    }
};

// Function to create and apply the visual mask [cite: 52]
const maskContent = (tweetElement, reason) => {
    // The tweet's main div needs relative positioning for the absolute mask
    tweetElement.style.position = 'relative';

    const mask = document.createElement('div');
    mask.className = 'sentinel-mask';
    mask.innerHTML = `
        <div class="sentinel-mask-text">${reason}</div>
        <button class="sentinel-mask-button">Show Content</button>
    `;

    // Add event listener to the "Show" button [cite: 56]
    mask.querySelector('.sentinel-mask-button').addEventListener('click', (e) => {
        e.stopPropagation(); // Prevents click from going to the tweet itself
        mask.remove(); // Deletes the mask, revealing the original content [cite: 57]
    });

    // Append the mask as a child of the tweet element [cite: 58]
    tweetElement.appendChild(mask);
};

// Use MutationObserver to detect new tweets as the user scrolls [cite: 22]
const observer = new MutationObserver((mutationsList) => {
    for (const mutation of mutationsList) {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
            mutation.addedNodes.forEach(node => {
                if (node.nodeType === 1 && node.matches('[data-testid="tweet"]')) {
                    processTweet(node);
                }
                // Also check for tweets inside the newly added nodes
                node.querySelectorAll('[data-testid="tweet"]').forEach(processTweet);
            });
        }
    }
});

// Start observing the main timeline area of the page
observer.observe(document.body, { childList: true, subtree: true });