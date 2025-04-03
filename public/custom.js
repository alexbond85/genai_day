// Wait for DOM to be fully loaded
document.addEventListener("DOMContentLoaded", function () {
  // Function to hide elements - will run initially and through observer
  function hideElements() {
    // Remove message icons
    document
      .querySelectorAll(
        '.cl-message-icon, [class*="MessageIcon"], .cl-avatar, .cl-avatar-container'
      )
      .forEach((el) => {
        el.style.display = "none";
        el.style.visibility = "hidden";
        if (el.parentNode) {
          el.parentNode.style.paddingLeft = "0";
          el.parentNode.style.marginLeft = "0";
        }
      });

    // Remove all svg icons in messages
    document
      .querySelectorAll(".cl-message svg, .cl-message-container svg")
      .forEach((el) => {
        el.style.display = "none";
      });

    // Remove Chainlit footer
    document
      .querySelectorAll(
        '.cl-footer, [class*="footer"], [class*="Footer"], a.watermark[href*="chainlit.io"]'
      )
      .forEach((el) => {
        el.style.display = "none";
        el.style.visibility = "hidden";
      });

    // Check for text nodes containing "Built with" and remove parent elements
    document.querySelectorAll("*").forEach((el) => {
      if (el.textContent && el.textContent.includes("Built with")) {
        if (el.parentNode) {
          el.parentNode.style.display = "none";
        }
        el.style.display = "none";
      }
    });
  }

  // Run initially
  hideElements();

  // Create observer to watch for DOM changes and re-run our function
  const observer = new MutationObserver(function (mutations) {
    hideElements();
  });

  // Observe the entire document for changes
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    characterData: true,
  });
});
