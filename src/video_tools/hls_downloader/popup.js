document.addEventListener('DOMContentLoaded', async () => {
  const streamList = document.getElementById('streamList');
  const clearBtn = document.getElementById('clearBtn');

  // Xóa số lượng thông báo (badge) khi mở popup
  await chrome.action.setBadgeText({ text: '' });

  const renderStreams = (streams) => {
    streamList.innerHTML = '';
    if (!streams || streams.length === 0) {
      streamList.innerHTML = '<div class="empty-msg">Chưa bắt được link m3u8 nào.<br/>Hãy mở video trên trang web để extension tự động bắt ngầm.</div>';
      return;
    }

    // Đảo ngược để link mới nhất lên đầu
    const reversed = [...streams].reverse();
    
    reversed.forEach((stream) => {
      const div = document.createElement('div');
      div.className = 'stream-item';
      
      const urlEl = document.createElement('div');
      urlEl.className = 'stream-url';
      urlEl.textContent = stream.url;
      div.appendChild(urlEl);
      
      // Nút Copy lệnh FFmpeg
      const ffmpegBtn = document.createElement('button');
      ffmpegBtn.textContent = 'Copy FFmpeg Command';
      ffmpegBtn.onclick = () => {
        let cmd = `ffmpeg `;
        
        // Gộp các header thành một string cách nhau bởi \r\n
        let headerStr = '';
        if (stream.cookie) headerStr += `Cookie: ${stream.cookie.replace(/"/g, '\\"')}\\r\\n`;
        if (stream.referer) headerStr += `Referer: ${stream.referer}\\r\\n`;
        if (stream.origin) headerStr += `Origin: ${stream.origin}\\r\\n`;
        if (stream.userAgent) headerStr += `User-Agent: ${stream.userAgent.replace(/"/g, '\\"')}\\r\\n`;

        if (headerStr) {
          cmd += `-headers "${headerStr}" `;
        }
        
        cmd += `-i "${stream.url}" -c copy video_${Date.now()}.mp4`;
        
        navigator.clipboard.writeText(cmd).then(() => {
          const originalText = ffmpegBtn.textContent;
          ffmpegBtn.textContent = 'Đã Copy!';
          setTimeout(() => ffmpegBtn.textContent = originalText, 2000);
        });
      };
      div.appendChild(ffmpegBtn);
      
      // Nút Copy lệnh yt-dlp
      const ytdlpBtn = document.createElement('button');
      ytdlpBtn.textContent = 'Copy yt-dlp Command';
      ytdlpBtn.onclick = () => {
        let cmd = `yt-dlp `;
        if (stream.referer) cmd += `--add-header "Referer:${stream.referer}" `;
        if (stream.cookie) cmd += `--add-header "Cookie:${stream.cookie.replace(/"/g, '\\"')}" `;
        if (stream.origin) cmd += `--add-header "Origin:${stream.origin}" `;
        if (stream.userAgent) cmd += `--user-agent "${stream.userAgent.replace(/"/g, '\\"')}" `;
        cmd += `"${stream.url}" -o "video_${Date.now()}.mp4"`;
        
        navigator.clipboard.writeText(cmd).then(() => {
          const originalText = ytdlpBtn.textContent;
          ytdlpBtn.textContent = 'Đã Copy!';
          setTimeout(() => ytdlpBtn.textContent = originalText, 2000);
        });
      };
      div.appendChild(ytdlpBtn);

      streamList.appendChild(div);
    });
  };

  const { capturedStreams } = await chrome.storage.local.get('capturedStreams');
  renderStreams(capturedStreams);

  clearBtn.onclick = async () => {
    await chrome.storage.local.set({ capturedStreams: [] });
    renderStreams([]);
    await chrome.action.setBadgeText({ text: '' });
  };
});
