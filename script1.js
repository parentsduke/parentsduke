/* ========== 图片单击放大 ========== */
document.querySelectorAll('.thumb').forEach(img => {
  img.addEventListener('click', () => {
    document.getElementById('overlay-img').src = img.src;
    document.getElementById('overlay').style.display = 'flex';
  });
});

document.getElementById('overlay').addEventListener('click', () => {
  document.getElementById('overlay').style.display = 'none';
});


/* ========== 视频单击放大（关键修正） ========== */

document.querySelectorAll('.video-wrapper').forEach(wrapper => {
  const video = wrapper.querySelector('.video-box');
  const clickLayer = wrapper.querySelector('.video-click-layer');

  clickLayer.addEventListener('click', () => {
    const overlay = document.getElementById('video-overlay');
    const overlayVideo = document.getElementById('overlay-video');

    overlayVideo.src = video.currentSrc || video.src;
    overlay.style.display = 'flex';
    overlayVideo.play();
  });
});

// 点击遮罩关闭
document.getElementById('video-overlay').addEventListener('click', () => {
  const overlayVideo = document.getElementById('overlay-video');
  overlayVideo.pause();
  overlayVideo.src = '';
  document.getElementById('video-overlay').style.display = 'none';
});
