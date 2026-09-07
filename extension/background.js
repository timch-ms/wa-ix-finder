const openedDetails = new Set();
const COLLECTOR_PARAMETER = "waixcollector";

function collectorUrl(value) {
  const url = new URL(value);
  url.searchParams.set(COLLECTOR_PARAMETER, "1");
  return url.toString();
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "inventory") return;

  fetch("http://127.0.0.1:4173/api/collect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(message.payload)
  })
    .then((response) => response.json())
    .then((result) => {
      sendResponse(result);
      if (result.ok && sender.tab?.id && message.payload.collectorManaged
        && (message.payload.isDetail || message.payload.collectionComplete)) {
        chrome.tabs.remove(sender.tab.id);
      }
    })
    .catch((error) => sendResponse({ error: error.message }));

  if (!message.payload.isDetail) {
    for (const url of message.payload.detailUrls.slice(0, 30)) {
      if (openedDetails.has(url)) continue;
      openedDetails.add(url);
      chrome.tabs.create({ url: collectorUrl(url), active: false });
    }
  }
  return true;
});
