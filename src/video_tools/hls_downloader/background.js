chrome.webRequest.onSendHeaders.addListener(
  (details) => {
    if (details.url.includes('.m3u8')) {
      let cookieHeader = '';
      let refererHeader = '';
      let originHeader = '';
      let userAgentHeader = '';
      
      if (details.requestHeaders) {
        for (let header of details.requestHeaders) {
          const headerName = header.name.toLowerCase();
          if (headerName === 'cookie') {
            cookieHeader = header.value;
          } else if (headerName === 'referer') {
            refererHeader = header.value;
          } else if (headerName === 'origin') {
            originHeader = header.value;
          } else if (headerName === 'user-agent') {
            userAgentHeader = header.value;
          }
        }
      }

      chrome.storage.local.get({ capturedStreams: [] }, (result) => {
        let streams = result.capturedStreams;
        // Kiểm tra xem url này đã được lưu gần đây chưa để tránh trùng lặp
        if (!streams.find(s => s.url === details.url)) {
          streams.push({
            url: details.url,
            cookie: cookieHeader,
            referer: refererHeader,
            origin: originHeader,
            userAgent: userAgentHeader,
            tabId: details.tabId,
            timestamp: Date.now()
          });
          
          // Chỉ giữ lại 20 luồng gần nhất
          if (streams.length > 20) streams.shift();
          
          chrome.storage.local.set({ capturedStreams: streams });
          chrome.action.setBadgeText({ text: streams.length.toString() });
          chrome.action.setBadgeBackgroundColor({ color: '#4CAF50' });
        }
      });
    }
  },
  { urls: ["<all_urls>"] },
  ["requestHeaders", "extraHeaders"]
);
