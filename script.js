
const thumbs = document.querySelectorAll('.thumb');
const overlay = document.getElementById('overlay');
const overlayImg = document.getElementById('overlay-img');

thumbs.forEach(img => {
  img.addEventListener('click', () => {
    overlayImg.src = img.src;
    overlay.style.display = 'flex';
  });
});

overlay.addEventListener('click', () => {
  overlay.style.display = 'none';
});

const videos = document.querySelectorAll('.enlarge-video');
const overlay = document.getElementById('video-overlay');
const overlayVideo = document.getElementById('overlay-video');

// 点击视频 → 放大
videos.forEach(video => {
  video.addEventListener('click', () => {
    overlayVideo.src = video.currentSrc;
    overlay.style.display = 'flex';
    overlayVideo.play();
  });
});

// 点击黑色区域 → 关闭
overlay.addEventListener('click', () => {
  overlayVideo.pause();
  overlayVideo.src = '';
  overlay.style.display = 'none';
});

document.querySelectorAll('.video-wrapper').forEach(wrapper => {
  const video = wrapper.querySelector('video');

  wrapper.addEventListener('click', () => {
    overlayVideo.src = video.currentSrc;
    overlay.style.display = 'flex';
    overlayVideo.play();
  });
});
