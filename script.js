// ========== 图片单击放大 ==========
document.querySelectorAll('.thumb').forEach(img => {
    img.addEventListener('click', () => {
        const overlay = document.getElementById('overlay');
        const overlayImg = document.getElementById('overlay-img');
        overlayImg.src = img.src;
        overlay.style.display = 'flex';
    });
});

document.getElementById('overlay').addEventListener('click', () => {
    document.getElementById('overlay').style.display = 'none';
});

// ========== 视频单击放大 ==========
document.querySelectorAll('.video-wrapper').forEach(wrapper => {
    const video = wrapper.querySelector('.video-box');
    const clickLayer = wrapper.querySelector('.video-click-layer');
    const overlay = document.getElementById('video-overlay');
    const overlayVideo = document.getElementById('overlay-video');

    clickLayer.addEventListener('click', () => {
        overlayVideo.src = video.currentSrc || video.src;
        overlay.style.display = 'flex';
        overlayVideo.play();
    });
});

document.getElementById('video-overlay').addEventListener('click', () => {
    const overlayVideo = document.getElementById('overlay-video');
    overlayVideo.pause();
    overlayVideo.src = '';
    document.getElementById('video-overlay').style.display = 'none';
});

const searchInput = document.getElementById('searchInput');
const items = document.querySelectorAll('.link-list a, .link-list li');

searchInput.addEventListener('input', () => {
  const keyword = searchInput.value.toLowerCase().trim();
  let firstMatch = null;

  items.forEach(el => {
    const text = el.textContent.toLowerCase();

    if (text.includes(keyword)) {
      el.style.display = '';
      if (!firstMatch && keyword !== '') {
        firstMatch = el;
      }
    } else {
      el.style.display = 'none';
    }
  });

  // ⭐ 自动滚动到第一个结果
  if (firstMatch) {
    firstMatch.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    });
  }
});

// ===== PPT 折叠控制 =====
const pptToggle = document.getElementById("pptToggle");
const pptContent = document.getElementById("pptContent");

if (pptToggle && pptContent) {
  pptToggle.addEventListener("click", () => {
    const isOpen = pptContent.style.display === "block";
    pptContent.style.display = isOpen ? "none" : "block";
    pptToggle.textContent = isOpen ? "展开" : "收起";
  });
}

// ===== Q&A 折叠互斥（一次只展开一个）=====
const qaDetails = document.querySelectorAll('.qa details');

qaDetails.forEach(detail => {
  detail.addEventListener('toggle', () => {
    if (detail.open) {
      qaDetails.forEach(other => {
        if (other !== detail) {
          other.removeAttribute('open');
        }
      });
    }
  });
});
